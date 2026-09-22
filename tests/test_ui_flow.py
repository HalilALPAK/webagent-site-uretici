"""Arayüz akışı testi (API anahtarı gerekmez): sihirbaz → analiz → görsel seçimi → inşa.

Sahte LLM ile 1. aşama çalıştırılır; ardından arayüz uç noktalarıyla görseller seçilir/yüklenir
ve "Siteyi oluştur" ile Laravel sitesi kurulup test edilir.
Kullanım:  python tests/test_ui_flow.py
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from test_pipeline_offline import FakeLLM  # noqa: E402
from webagent.jobs import JobRequest, load_job, new_job  # noqa: E402
from webagent.orchestrator import Orchestrator  # noqa: E402
from webagent.web.app import app  # noqa: E402


def png(color: tuple[int, int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (800, 600), color).save(buf, "PNG")
    return buf.getvalue()


def main() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    rival = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(port)],
                             cwd=ROOT / "site_engine", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.25).close()
                break
            except OSError:
                time.sleep(0.25)

        # 1. aşama (sahte LLM)
        job = new_job(JobRequest(sector="diş kliniği", brand_name="Test Klinik", location="İzmir",
                                 competitor_urls=[f"http://127.0.0.1:{port}"], max_competitors=1))
        assert Orchestrator(job, llm=FakeLLM()).run_analysis(), job.error
        job = load_job(job.id)
        assert job.status == "awaiting_review", job.status

        c = TestClient(app)
        r = c.get(f"/jobs/{job.id}")
        assert r.status_code == 200 and "Plan raporu" in r.text, "plan raporu ekranı açılmalı"
        assert c.get(f"/jobs/{job.id}/report.md").status_code == 200, "rapor indirilebilmeli"
        assert c.post(f"/jobs/{job.id}/approve", follow_redirects=False).status_code == 303
        job = load_job(job.id)
        assert job.status == "awaiting_images", job.status
        print("✓ plan raporu gösterildi ve onaylandı")
        groups = job.artifacts["images"]["groups"]
        print("Gruplar:", [(g["id"], len(g["slots"]), len(g["pool"])) for g in groups])

        r = c.get(f"/jobs/{job.id}")
        assert r.status_code == 200 and "Siteyi oluştur" in r.text, r.status_code
        print("✓ görsel seçim ekranı açıldı")

        multi = next(g for g in groups if len(g["slots"]) > 1)
        slot0, slot1 = multi["slots"][0]["id"], multi["slots"][1]["id"]

        # tek görsel yükle
        r = c.post(f"/jobs/{job.id}/img/{slot0}/upload", files={"file": ("benim.png", png((200, 30, 30)), "image/png")},
                   follow_redirects=False)
        assert r.status_code == 303, r.text
        assert load_job(job.id).artifacts["images"]["choices"][slot0]["type"] == "upload"
        assert c.get(f"/jobs/{job.id}/uploads/{slot0}").status_code == 200
        print("✓ tek görsel yüklendi ve önizlendi")

        # görsel olmayan dosya reddedilir
        r = c.post(f"/jobs/{job.id}/img/{slot1}/upload", files={"file": ("x.png", b"not an image", "image/png")})
        assert r.status_code == 400, r.status_code
        print("✓ görsel olmayan dosya reddedildi")

        # grup: hepsine hazır görsel (yüklenen korunur), sonra toplu yükleme, sonra tek boşaltma
        c.post(f"/jobs/{job.id}/group/{multi['id']}/stock")
        ch = load_job(job.id).artifacts["images"]["choices"]
        assert ch[slot0]["type"] == "upload", "hazır görsel ataması yüklenen görseli ezmemeli"
        c.post(f"/jobs/{job.id}/group/{multi['id']}/upload",
               files=[("files", ("a.png", png((10, 120, 60)), "image/png")), ("files", ("b.png", png((20, 40, 160)), "image/png"))])
        ch = load_job(job.id).artifacts["images"]["choices"]
        assert ch[slot0]["type"] == ch[slot1]["type"] == "upload"
        print("✓ toplu yükleme yuvalara sırayla yerleşti")
        if multi["pool"]:
            c.post(f"/jobs/{job.id}/img/{slot1}/next")
            assert load_job(job.id).artifacts["images"]["choices"][slot1]["type"] == "stock"
            print("✓ 'başka öner' hazır görsele geçti")
        c.post(f"/jobs/{job.id}/img/{slot1}/clear")
        assert load_job(job.id).artifacts["images"]["choices"][slot1]["type"] == "none"
        print("✓ tek görsel boşaltıldı")

        # 2. aşama
        r = c.post(f"/jobs/{job.id}/build", follow_redirects=False)
        assert r.status_code == 303
        for _ in range(600):
            j = load_job(job.id)
            if j.status in ("done", "failed"):
                break
            time.sleep(1)
        assert j.status == "done", j.error
        out = Path(j.output_dir)
        placed = out / "public" / "uploads" / "seed" / f"{slot0}.jpg"
        assert placed.exists(), "yüklenen görsel siteye yerleşmedi"
        assert Image.open(placed).getpixel((5, 5))[0] < 60, "toplu yüklemedeki ilk dosya (yeşil) ilk yuvaya gelmeli"
        assert not (out / "public" / "uploads" / "seed" / f"{slot1}.jpg").exists(), "boşaltılan yuvada görsel olmamalı"
        assert j.artifacts["qa"]["passed"], j.artifacts["qa"]["errors"]
        print(f"✓ site kuruldu, QA {len(j.artifacts['qa']['checks'])}/{len(j.artifacts['qa']['checks'])} geçti: {out}")
        return 0
    finally:
        rival.terminate()


if __name__ == "__main__":
    sys.exit(main())
