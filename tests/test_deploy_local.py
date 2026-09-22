"""Yayın (sunucuya yükleme) testi — gerçek hosting benzetimiyle, API anahtarı gerekmez.

Yerelde bir FTP sunucusu (hosting hesabı) ve bir web sunucusu (alan adı) ayağa kaldırılır;
üretilmiş bir site bunlara yüklenir, kurulum betiği çalıştırılır ve site gerçekten açılıyor mu diye bakılır.

Kullanım:  python tests/test_deploy_local.py [site_klasörü]
"""
from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import httpx  # noqa: E402

from webagent.config import OUTPUT_DIR, php_bin  # noqa: E402
from webagent.deploy import DeployAgent, Target  # noqa: E402
from webagent.jobs import JobRequest, new_job  # noqa: E402

ROUTER = """<?php
// PHP yerleşik sunucusu için basit yönlendirici (Apache .htaccess'in yerine)
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$file = __DIR__ . $path;
if ($path !== '/' && is_file($file)) { return false; }
require __DIR__ . '/index.php';
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_ftp(root: Path, port: int, user: str, password: str) -> threading.Thread:
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer

    auth = DummyAuthorizer()
    auth.add_user(user, password, str(root), perm="elradfmwMT")
    handler = FTPHandler
    handler.authorizer = auth
    server = FTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def main() -> int:
    site_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else max(
        (p for p in OUTPUT_DIR.glob("*") if (p / "artisan").exists()), key=lambda p: p.stat().st_mtime, default=None)
    if not site_dir or not site_dir.exists():
        print("Test için üretilmiş bir Laravel sitesi gerekli (önce tests/test_ui_flow.py çalıştırın).")
        return 1
    print(f"Site: {site_dir}")

    hosting = Path(tempfile.mkdtemp(prefix="hosting-"))     # sunucu hesabı
    webroot = hosting / "public_html"                       # web kökü
    webroot.mkdir()
    ftp_port, web_port = free_port(), free_port()
    ftp = start_ftp(webroot, ftp_port, "user", "pass")
    (webroot / "router.php").write_text(ROUTER, encoding="utf-8")
    web = subprocess.Popen([php_bin(), "-S", f"127.0.0.1:{web_port}", "-t", str(webroot), str(webroot / "router.php")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                socket.create_connection(("127.0.0.1", web_port), timeout=0.25).close()
                break
            except OSError:
                time.sleep(0.25)

        job = new_job(JobRequest(sector="test", brand_name="Yayın Testi"))
        job.log = lambda a, m, level="info": print(f"[{level:5}] {a}: {m}", flush=True)
        target = Target(method="ftp", host="127.0.0.1", port=ftp_port, username="user", password="pass",
                        remote_dir="/", site_url=f"http://127.0.0.1:{web_port}", db={"type": "sqlite"})
        result = DeployAgent(job, site_dir).run(target)
        print("Sonuç:", result)

        # sunucuda beklenen düzen: kod web kökünün dışında, public dosyaları kökte
        app_dirs = [p for p in hosting.glob("webagent-app-*") if p.is_dir()]
        assert app_dirs, "uygulama klasörü web kökünün dışına açılmalıydı"
        assert (webroot / "index.php").exists() and (webroot / "css" / "site.css").exists(), "public dosyaları kökte olmalı"
        assert not list(webroot.glob("webagent-install-*.php")), "kurulum betiği silinmeliydi"
        assert not list(webroot.glob("webagent-*.zip")), "yükleme paketi silinmeliydi"
        assert not (webroot / ".env").exists() and not (webroot / "app").exists(), "kod web kökünde olmamalı"

        with httpx.Client(timeout=30) as c:
            r = c.get(f"http://127.0.0.1:{web_port}/")
            assert r.status_code == 200 and "<title>" in r.text, r.status_code
            print("✓ site açılıyor:", r.text.split("<title>")[1].split("<")[0][:60])
            assert c.get(f"http://127.0.0.1:{web_port}/admin", follow_redirects=False).status_code == 302
            print("✓ yönetim paneli giriş istiyor")
            r = c.get(f"http://127.0.0.1:{web_port}/.env")
            assert r.status_code == 404, f".env web kökünden okunabiliyor! ({r.status_code})"
            print("✓ .env web kökünden erişilemiyor")
        # arayüz üzerinden de dene (yalnızca site bu ortamın output klasöründeyse)
        if OUTPUT_DIR.resolve() in site_dir.resolve().parents:
            from fastapi.testclient import TestClient

            from webagent.jobs import load_job
            from webagent.web.app import app

            ui_job = new_job(JobRequest(sector="test", brand_name="Yayın Testi (arayüz)"))
            ui_job.status, ui_job.output_dir = "done", str(site_dir)
            ui_job.save()
            r = TestClient(app).post(f"/jobs/{ui_job.id}/deploy", data={
                "method": "ftp", "host": "127.0.0.1", "port": ftp_port, "username": "user", "password": "pass",
                "remote_dir": "/", "site_url": f"http://127.0.0.1:{web_port}", "db_type": "sqlite",
            }, follow_redirects=False)
            assert r.status_code == 303, r.text
            for _ in range(300):
                j = load_job(ui_job.id)
                if j.status == "done" and (j.artifacts.get("deploy") or j.error):
                    break
                time.sleep(1)
            assert j.artifacts.get("deploy"), j.error
            assert "password" not in j.artifacts["deploy_settings"], "şifre diske yazılmamalı"
            print("✓ arayüzden yayın da çalışıyor:", j.artifacts["deploy"]["url"])

        print("\nTAMAM — yayın akışı çalışıyor.")
        return 0
    finally:
        web.terminate()
        ftp.close_all()
        shutil.rmtree(hosting, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
