"""İş durumu: ajanların ortak 'kara tahtası' (blackboard).

Her ajan buraya olay (log) yazar ve ürettiği çıktıyı artifacts altına koyar.
Durum her değişiklikte diske JSON olarak kaydedilir; arayüz bunu okur.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from .config import JOBS_DIR

_SAVE_LOCK = threading.Lock()


@dataclass
class JobEvent:
    ts: float
    agent: str
    level: str  # info | ok | warn | error
    message: str


@dataclass
class JobRequest:
    sector: str
    language: str = "tr"
    location: str = "Türkiye"
    competitor_urls: list[str] = field(default_factory=list)
    max_competitors: int = 5
    brand_name: str = ""
    notes: str = ""
    own_site: str = ""        # kullanıcının mevcut sitesi (bilgi ve görseller oradan devralınır)
    contact_phone: str = ""   # boş bırakılırsa ajan örnek bilgi yazar
    contact_email: str = ""
    address: str = ""
    style: str = "auto"       # auto | light | dark | colorful | minimal (kullanıcının seçtiği görünüm)
    ai_backend: str = "auto"  # auto | claude-code | api
    db: dict = field(default_factory=lambda: {"type": "sqlite"})  # şifre diske yazılmaz (bkz. SECRETS)


@dataclass
class Job:
    id: str
    request: JobRequest
    status: str = "queued"  # queued | running | awaiting_review | awaiting_images | building | done | failed
    stage: str = ""
    created_at: float = field(default_factory=time.time)
    events: list[JobEvent] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    output_dir: str = ""
    error: str = ""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    # ------------------------------------------------------------ yazma
    def log(self, agent: str, message: str, level: str = "info") -> None:
        with self._lock:
            self.events.append(JobEvent(time.time(), agent, level, message))
        self.save()

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self.artifacts[key] = value
        self.save()

    def set_stage(self, stage: str) -> None:
        self.stage = stage
        self.save()

    # ------------------------------------------------------------ kalıcılık
    def to_dict(self) -> dict:
        with self._lock:
            return {
                "id": self.id,
                "request": asdict(self.request),
                "status": self.status,
                "stage": self.stage,
                "created_at": self.created_at,
                "events": [asdict(e) for e in self.events],
                "artifacts": json.loads(json.dumps(self.artifacts, default=str)),
                "output_dir": self.output_dir,
                "error": self.error,
            }

    def save(self) -> None:
        path = JOBS_DIR / f"{self.id}.json"
        data = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        # Geçici dosya adı sürece/iş parçacığına özeldir: aynı görevi iki süreç (ör. arayüz + test)
        # yazarken Windows'ta "erişim engellendi" hatası almayalım.
        tmp = path.with_suffix(f".{os.getpid()}-{threading.get_ident()}.tmp")
        with _SAVE_LOCK:
            tmp.write_text(data, encoding="utf-8")
            for attempt in range(6):
                try:
                    tmp.replace(path)
                    return
                except PermissionError:  # dosya o an başka bir süreçte açık
                    time.sleep(0.05 * (attempt + 1))
            tmp.unlink(missing_ok=True)


# Diske yazılmayan gizli bilgiler (ör. uzak veritabanı şifresi): job_id -> {anahtar: değer}
SECRETS: dict[str, dict] = {}


def load_job(job_id: str) -> Job | None:
    """Diskteki görevi yeniden Job nesnesine çevirir (uygulama kapanıp açılınca kaldığı yerden devam için)."""
    d = load_job_dict(job_id)
    if not d:
        return None
    job = Job(id=d["id"], request=JobRequest(**d["request"]), status=d["status"], stage=d["stage"],
              created_at=d["created_at"], artifacts=d["artifacts"], output_dir=d["output_dir"], error=d["error"])
    job.events = [JobEvent(**e) for e in d["events"]]
    return job


def new_job(request: JobRequest) -> Job:
    job = Job(id=uuid.uuid4().hex[:10], request=request)
    job.save()
    return job


def load_job_dict(job_id: str) -> dict | None:
    path = JOBS_DIR / f"{job_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_jobs() -> list[dict]:
    jobs = []
    for p in JOBS_DIR.glob("*.json"):
        try:
            jobs.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return sorted(jobs, key=lambda j: j["created_at"], reverse=True)
