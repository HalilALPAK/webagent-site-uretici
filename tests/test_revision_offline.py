"""Revizyon testi (API anahtarı gerekmez): hazır siteyi güncellerken veri korunuyor mu?

Akış: sahte LLM ile site üretilir → yönetim panelinden eklenmiş gibi bir kayıt yazılır →
"alan ekle / bölüm kaldır / rengi değiştir" revizyonu uygulanır → veri, yeni sütun ve testler kontrol edilir.

Kullanım:  python tests/test_revision_offline.py
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.stdout.reconfigure(encoding="utf-8")

from test_pipeline_offline import FakeLLM, main as build_site  # noqa: E402

from webagent.jobs import JobRequest, load_job, new_job  # noqa: E402
from webagent.orchestrator import Orchestrator  # noqa: E402
from webagent.schemas import EntitySeed, Revision, Site  # noqa: E402

NEW_FIELD = {"name": "opening_hours", "label": "Açılış saatleri", "type": "string", "required": False,
             "options": [], "relation": None, "show_in_list": True}


class ReviseLLM(FakeLLM):
    """Kullanıcının isteğini uygulamış gibi güncellenmiş site tanımı döndürür."""

    def __init__(self):
        super().__init__()
        self.removed = None

    def structured(self, system, prompt, output, effort="medium", max_tokens=16000):
        if output is not Revision:
            return super().structured(system, prompt, output, effort, max_tokens)
        self.calls.append("Revision")
        body = prompt.split("Yayındaki site tanımı:\n", 1)[1].split("\n\nKullanıcının isteği:")[0]
        site = json.loads(body)
        site["entities"][0]["fields"].append(dict(NEW_FIELD))      # yeni alan
        self.removed = site["entities"].pop()["name"]              # bir bölüm kaldırılıyor
        site["theme"]["accent"] = "#c2410c"                        # tasarım değişikliği
        site["pages"].append({"slug": "calisma-saatleri", "title": "Çalışma Saatleri", "in_nav": True,
                              "body_markdown": "## Hafta içi\n\n09:00 - 18:00"})
        return Revision(summary="Açılış saatleri alanı eklendi, bir bölüm kaldırıldı, vurgu rengi değişti.",
                        site=Site(**site))


def rows(db: Path, table: str) -> list[tuple]:
    with sqlite3.connect(db) as c:
        return c.execute(f"SELECT * FROM {table}").fetchall()


def main() -> int:
    if build_site() != 0:  # sahte LLM ile taze bir site üret
        return 1
    job_id = sorted(Path(ROOT / "data" / "jobs").glob("*.json"), key=lambda p: p.stat().st_mtime)[-1].stem
    job = load_job(job_id)
    site_dir = Path(job.output_dir)
    db = site_dir / "database" / "database.sqlite"
    spec = json.loads((site_dir / "site.json").read_text(encoding="utf-8"))
    first = spec["entities"][0]
    print(f"\nSite: {site_dir.name} · ilk tablo: {first['name']}")

    # yönetim panelinden eklenmiş gibi bir kayıt
    title_col = first["title_field"]
    with sqlite3.connect(db) as c:
        c.execute(f"INSERT INTO {first['name']} ({title_col}) VALUES (?)", ("ELLE EKLENEN KAYIT",))
    before = len(rows(db, first["name"]))

    # revizyon
    job.log = lambda a, m, level="info": print(f"[{level:5}] {a}: {m}"[:160], flush=True)
    llm = ReviseLLM()
    Orchestrator(job, llm=llm).run_revision("şubelere açılış saati ekle, son bölümü kaldır, vurgu rengini değiştir")
    for _ in range(300):
        job = load_job(job_id)
        if job.status in ("done", "failed"):
            break
        time.sleep(1)
    assert job.status == "done", job.error

    # 1) kullanıcı verisi duruyor mu, çoğaltılmış mı?
    after = rows(db, first["name"])
    assert len(after) == before, f"kayıt sayısı değişti: {before} → {len(after)}"
    assert any("ELLE EKLENEN KAYIT" in str(r) for r in after), "elle eklenen kayıt kayboldu"
    print("✓ mevcut veri korundu (yeni içerik eklenmedi, eski silinmedi)")

    # 2) yeni sütun geldi mi?
    with sqlite3.connect(db) as c:
        cols = {r[1] for r in c.execute(f"PRAGMA table_info({first['name']})")}
    assert "opening_hours" in cols, cols
    print("✓ yeni alan veritabanına eklendi")

    # 3) kaldırılan bölümün tablosu duruyor ama sitede yok
    new_spec = json.loads((site_dir / "site.json").read_text(encoding="utf-8"))
    names = {e["name"] for e in new_spec["entities"]}
    assert llm.removed not in names, "kaldırılan bölüm site tanımında kalmış"
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (llm.removed,)).fetchone(), \
            "kaldırılan bölümün verisi silinmiş olmamalı"
    print(f"✓ '{llm.removed}' sitede görünmüyor ama verisi duruyor")

    # 4) tasarım ve yeni sayfa
    assert new_spec["theme"]["accent"] == "#c2410c"
    assert any(p["slug"] == "calisma-saatleri" for p in new_spec["pages"])
    assert (site_dir / ".revisions").is_dir(), "yedek alınmadı"
    print("✓ tasarım, yeni sayfa ve yedek tamam")

    # 5) site hâlâ çalışıyor mu (QA)
    assert job.artifacts["qa"]["passed"], job.artifacts["qa"]["errors"]
    print(f"✓ QA {len(job.artifacts['qa']['checks'])} kontrol geçti")
    print("\nTAMAM — revizyon akışı çalışıyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
