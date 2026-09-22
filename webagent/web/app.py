"""Web Agent arayüzü (masaüstü penceresinde ya da tarayıcıda çalışır).

Akış: İlk kurulum (PHP + Laravel) → Sihirbaz (işletme, sektör, bağlantılar) → Analiz (canlı akış)
      → Görsel seçimi (grup grup: hazır / yükle / boş) → İnşa + test → Siteyi aç.
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import time
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..agents.laravel_builder import NO_WINDOW, SERVER_SCRIPT
from ..config import JOBS_DIR, MODEL, OUTPUT_DIR, php_bin, save_env_value, tools_ready
from ..jobs import SECRETS, JobRequest, list_jobs, load_job, load_job_dict, new_job
from ..llm import find_claude_cli
from ..deploy import DeployAgent, Target
from ..orchestrator import start_in_background
from ..setup_tools import SetupError, setup_all

HERE = Path(__file__).resolve().parent
app = FastAPI(title="Web Agent")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.filters["ts"] = lambda t: time.strftime("%d.%m %H:%M", time.localtime(t))

AGENTS = [
    ("Miras Ajanı", "Varsa mevcut sitenizden bilgileri ve görselleri devralır"),
    ("Keşif Ajanı", "Web aramasıyla sektördeki rakipleri bulur"),
    ("Tarayıcı Ajanı", "Rakip siteleri gezer; menü, form, teknoloji sinyallerini toplar"),
    ("Analist Ajanı", "Her sitenin modüllerini kanıtlarıyla çıkarır"),
    ("Stratejist Ajanı", "Özellik matrisinden modül setini ve konumlandırmayı seçer"),
    ("Mimar Ajanı", "Veri modeli ve sayfaları tasarlar"),
    ("Tasarım Ajanı", "DESIGN.md'ye göre tema, tipografi, menü ve ana sayfa kurgusunu seçer"),
    ("İçerik Ajanı", "Veritabanı için özgün örnek içerik yazar"),
    ("Görsel Ajanı", "Görsel gruplarını çıkarır, hazır görsel önerir, seçimlerinizi uygular"),
    ("Rapor Ajanı", "Üretimden önce ne yapılacağını ve sizden ne isteneceğini raporlar"),
    ("İnşa Ajanı", "Laravel + Filament projesini ve veritabanını kurar"),
    ("Revizyon Ajanı", "Hazır sitede istediğiniz değişiklikleri veri kaybetmeden uygular"),
    ("QA Ajanı", "Üretilen siteyi uçtan uca test eder"),
]
STATUS_TR = {"queued": "sırada", "running": "çalışıyor", "awaiting_review": "plan onayı bekliyor",
             "awaiting_images": "görsel bekliyor",
             "building": "oluşturuluyor", "deploying": "sunucuya yükleniyor", "done": "hazır", "failed": "hata"}
templates.env.globals.update(STATUS_TR=STATUS_TR)

RUNNING: dict[str, tuple[subprocess.Popen, int]] = {}  # job_id -> (PHP sunucusu, port)
JOB_ID = re.compile(r"^[0-9a-f]{10}$")
SLOT_ID = re.compile(r"^[a-z0-9_]+$")
SETUP = {"running": False, "done": False, "error": "", "log": []}
MAX_UPLOAD = 15 * 1024 * 1024


@app.on_event("startup")
def _mark_stale_jobs() -> None:
    """Yarıda kalan analiz/inşa görevlerini başarısız işaretle (görsel bekleyenler kalır, devam edilebilir)."""
    for d in list_jobs():
        if d["status"] in ("queued", "running", "building", "deploying"):
            job = load_job(d["id"])
            job.status, job.error = "failed", "Uygulama kapandığı için görev yarıda kaldı."
            job.save()


@app.on_event("shutdown")
def _stop_all() -> None:
    for proc, _ in RUNNING.values():
        proc.terminate()


# ============================================================ yardımcılar

def _job_dict(job_id: str) -> dict:
    if not JOB_ID.match(job_id) or not (d := load_job_dict(job_id)):
        raise HTTPException(404, "Görev bulunamadı")
    return d


def _job_for_images(job_id: str):
    job = load_job(_job_dict(job_id)["id"])
    if job.status != "awaiting_images":
        raise HTTPException(409, "Bu görev görsel seçimi aşamasında değil.")
    return job


def _group(images: dict, gid: str) -> dict:
    g = next((g for g in images["groups"] if g["id"] == gid), None)
    if not g:
        raise HTTPException(404, "Görsel grubu bulunamadı")
    return g


def _slot_group(images: dict, slot: str) -> dict:
    g = next((g for g in images["groups"] if any(s["id"] == slot for s in g["slots"])), None)
    if not g or not SLOT_ID.match(slot):
        raise HTTPException(404, "Görsel yuvası bulunamadı")
    return g


def _back(job_id: str, gid: str = "") -> RedirectResponse:
    return RedirectResponse(f"/jobs/{job_id}" + (f"#g-{gid}" if gid else ""), status_code=303)


def _used(images: dict) -> set[str]:
    return {c["cid"] for c in images["choices"].values() if c.get("type") == "stock"}


async def _store_upload(job_id: str, slot: str, file: UploadFile) -> str:
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Dosya 15 MB'tan büyük olamaz.")
    if data[:200].lstrip().startswith(b"<svg") or (file.filename or "").lower().endswith(".svg"):
        if b"<script" in data.lower():  # SVG içinde betik olmasın
            raise HTTPException(400, "SVG dosyası betik içeriyor; PNG olarak yükleyin.")
    else:
        from PIL import Image
        try:
            Image.open(BytesIO(data)).verify()
        except Exception:
            raise HTTPException(400, f"'{file.filename}' bir görsel dosyası değil.")
    ext = (Path(file.filename or "").suffix.lower() or ".jpg")[:5]
    folder = JOBS_DIR / job_id / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{slot}.*"):
        old.unlink()
    path = folder / f"{slot}{ext}"
    path.write_bytes(data)
    return str(path)


def _ctx(request: Request, **kw) -> dict:
    return {"request": request, "agents": AGENTS, "model": MODEL, **kw}


# ============================================================ ilk kurulum

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not tools_ready():
        return templates.TemplateResponse(request, "setup.html", _ctx(request, setup=SETUP))
    return templates.TemplateResponse(request, "index.html", _ctx(
        request, jobs=list_jobs(), claude_cli=find_claude_cli(),
        has_api_key=bool(os.environ.get("ANTHROPIC_API_KEY")),
    ))


@app.post("/setup/start")
def setup_start():
    if not SETUP["running"] and not tools_ready():
        SETUP.update(running=True, done=False, error="", log=[])

        def work():
            try:
                setup_all(lambda m: SETUP["log"].append(m))
                SETUP["done"] = True
            except (SetupError, Exception) as e:  # ağ, disk vb. — ekranda gösterilir
                SETUP["error"] = str(e)
            finally:
                SETUP["running"] = False

        threading.Thread(target=work, daemon=True).start()
    return RedirectResponse("/", status_code=303)


@app.get("/setup/status")
def setup_status():
    return {**SETUP, "log": SETUP["log"][-40:], "ready": tools_ready()}


# ============================================================ sihirbaz → görev

@app.post("/api/db-test")
def db_test(host: str = Form(""), port: int = Form(3306), database: str = Form(""),
            username: str = Form(""), password: str = Form("")):
    """Uzak MySQL bağlantısını PHP PDO ile dener (sitenin kullanacağı sürücüyle aynı)."""
    code = ("try { new PDO('mysql:host='.getenv('H').';port='.getenv('P').';dbname='.getenv('D'), getenv('U'), getenv('W'),"
            " [PDO::ATTR_TIMEOUT => 5]); echo 'OK'; } catch (Throwable $e) { echo $e->getMessage(); }")
    env = {**os.environ, "H": host, "P": str(port), "D": database, "U": username, "W": password}
    try:
        out = subprocess.run([php_bin(), "-r", code], env=env, capture_output=True, text=True, timeout=15,
                             creationflags=NO_WINDOW).stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        out = str(e)
    return JSONResponse({"ok": out == "OK", "message": "Bağlantı başarılı." if out == "OK" else out[:300]})


@app.post("/jobs")
async def create_job(
    brand_name: str = Form(...), sector: str = Form(...), location: str = Form("Türkiye"), language: str = Form("tr"),
    competitor_urls: str = Form(""), max_competitors: int = Form(4), notes: str = Form(""), style: str = Form("auto"),
    own_site: str = Form(""),
    contact_phone: str = Form(""), contact_email: str = Form(""), address: str = Form(""),
    logo: UploadFile | None = File(None),
    ai_backend: str = Form("claude-code"), api_key: str = Form(""), remember_key: str = Form(""),
    db_type: str = Form("sqlite"), db_host: str = Form(""), db_port: int = Form(3306), db_database: str = Form(""),
    db_username: str = Form(""), db_password: str = Form(""),
):
    if ai_backend == "api":
        if api_key.strip():
            os.environ["ANTHROPIC_API_KEY"] = api_key.strip()
            if remember_key:
                save_env_value("ANTHROPIC_API_KEY", api_key.strip())
        elif not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(400, "API seçildi ama anahtar girilmedi.")
    db = {"type": "sqlite"}
    if db_type == "mysql":
        if not (db_host and db_database and db_username):
            raise HTTPException(400, "MySQL için sunucu, veritabanı adı ve kullanıcı adı gerekli.")
        db = {"type": "mysql", "host": db_host.strip(), "port": db_port, "database": db_database.strip(),
              "username": db_username.strip()}

    urls = [u.strip() for u in re.split(r"[\s,]+", competitor_urls) if u.strip()]
    job = new_job(JobRequest(
        sector=sector.strip()[:200], language=language, location=location.strip()[:100] or "Türkiye",
        competitor_urls=urls[:10], max_competitors=max(1, min(max_competitors, 8)),
        brand_name=brand_name.strip()[:80], notes=notes.strip()[:2000], ai_backend=ai_backend, db=db,
        style=style if style in ("auto", "light", "dark", "colorful", "minimal") else "auto",
        contact_phone=contact_phone.strip()[:40], contact_email=contact_email.strip()[:120], address=address.strip()[:200],
        own_site=own_site.strip()[:200],
    ))
    if db["type"] == "mysql":
        SECRETS[job.id] = {"password": db_password}
    if logo and logo.filename:  # isteğe bağlı logo
        try:
            job.put("logo", await _store_upload(job.id, "logo", logo))
        except HTTPException as e:
            job.log("Sihirbaz", f"Logo alınamadı: {e.detail}", "warn")
    start_in_background(job, "analysis")
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_page(request: Request, job_id: str):
    job = _job_dict(job_id)
    need_db_password = job["request"]["db"].get("type") == "mysql" and job_id not in SECRETS
    return templates.TemplateResponse(request, "job.html", _ctx(
        request, job=job, site_url=_running_url(job_id), need_db_password=need_db_password))


@app.get("/jobs/{job_id}/partial", response_class=HTMLResponse)
def job_partial(request: Request, job_id: str):
    return templates.TemplateResponse(request, "_job_body.html", _ctx(
        request, job=_job_dict(job_id), site_url=_running_url(job_id)))


@app.get("/api/jobs/{job_id}")
def job_json(job_id: str):
    return JSONResponse(_job_dict(job_id))


@app.post("/jobs/{job_id}/delete")
def delete_job(job_id: str):
    _job_dict(job_id)
    (JOBS_DIR / f"{job_id}.json").unlink(missing_ok=True)
    return RedirectResponse("/", status_code=303)


# ============================================================ görsel seçimi

@app.post("/jobs/{job_id}/approve")
def approve_plan(job_id: str):
    """Plan raporu onaylandı → görsel seçimine geç."""
    job = load_job(_job_dict(job_id)["id"])
    if job.status != "awaiting_review":
        raise HTTPException(409, "Bu görev plan onayı aşamasında değil.")
    job.status = "awaiting_images"
    job.set_stage("Görsel seçimi")
    job.log("Rapor Ajanı", "Plan onaylandı, görsel seçimine geçildi.", "ok")
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.get("/jobs/{job_id}/report.md")
def report_markdown_file(job_id: str):
    """Planı metin dosyası olarak indir."""
    from ..agents.reporter import report_markdown
    from ..schemas import PlanReport

    job = _job_dict(job_id)
    stored = job["artifacts"].get("report")
    if not stored:
        raise HTTPException(404, "Bu görev için rapor yok.")
    md = report_markdown(PlanReport(**stored["report"]), stored["facts"])
    name = re.sub(r"[^a-z0-9-]+", "-", stored["facts"]["site_name"].lower())[:40] or "site"
    return Response(md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}-plan.md"'})


@app.get("/jobs/{job_id}/uploads/{slot}")
def upload_preview(job_id: str, slot: str):
    _job_dict(job_id)
    if not SLOT_ID.match(slot):
        raise HTTPException(404)
    match = next((JOBS_DIR / job_id / "uploads").glob(f"{slot}.*"), None)
    if not match:
        raise HTTPException(404)
    return FileResponse(match)


@app.post("/jobs/{job_id}/img/{slot}/next")
def slot_next(job_id: str, slot: str):
    """Aynı gruptan, kullanılmayan bir sonraki hazır görsel."""
    job = _job_for_images(job_id)
    images = job.artifacts["images"]
    g = _slot_group(images, slot)
    used = _used(images)
    current = images["choices"].get(slot, {}).get("cid")
    ids = [c["id"] for c in g["pool"]]
    start = ids.index(current) + 1 if current in ids else 0
    for cid in ids[start:] + ids[:start]:
        if cid not in used:
            images["choices"][slot] = {"type": "stock", "cid": cid}
            break
    job.put("images", images)
    return _back(job_id, g["id"])


@app.post("/jobs/{job_id}/img/{slot}/upload")
async def slot_upload(job_id: str, slot: str, file: UploadFile = File(...)):
    job = _job_for_images(job_id)
    images = job.artifacts["images"]
    g = _slot_group(images, slot)
    images["choices"][slot] = {"type": "upload", "file": await _store_upload(job_id, slot, file), "ts": int(time.time())}
    job.put("images", images)
    return _back(job_id, g["id"])


@app.post("/jobs/{job_id}/img/{slot}/clear")
def slot_clear(job_id: str, slot: str):
    job = _job_for_images(job_id)
    images = job.artifacts["images"]
    g = _slot_group(images, slot)
    images["choices"][slot] = {"type": "none"}
    job.put("images", images)
    return _back(job_id, g["id"])


@app.post("/jobs/{job_id}/group/{gid}/stock")
def group_stock(job_id: str, gid: str):
    """Gruptaki tüm yuvalara hazır görsel ata (yüklenen görseller korunur)."""
    job = _job_for_images(job_id)
    images = job.artifacts["images"]
    g = _group(images, gid)
    keep = {s["id"] for s in g["slots"] if images["choices"].get(s["id"], {}).get("type") == "upload"}
    others = {c["cid"] for sid, c in images["choices"].items()
              if c.get("type") == "stock" and not any(s["id"] == sid for s in g["slots"])}
    pool = iter([c["id"] for c in g["pool"] if c["id"] not in others])
    for s in g["slots"]:
        if s["id"] not in keep:
            cid = next(pool, None)
            images["choices"][s["id"]] = {"type": "stock", "cid": cid} if cid else {"type": "none"}
    job.put("images", images)
    return _back(job_id, gid)


@app.post("/jobs/{job_id}/group/{gid}/clear")
def group_clear(job_id: str, gid: str):
    job = _job_for_images(job_id)
    images = job.artifacts["images"]
    for s in _group(images, gid)["slots"]:
        images["choices"][s["id"]] = {"type": "none"}
    job.put("images", images)
    return _back(job_id, gid)


@app.post("/jobs/{job_id}/group/{gid}/upload")
async def group_upload(job_id: str, gid: str, files: list[UploadFile] = File(...)):
    """Toplu yükleme: seçilen dosyalar gruptaki yuvalara sırayla yerleşir."""
    job = _job_for_images(job_id)
    images = job.artifacts["images"]
    g = _group(images, gid)
    for slot, f in zip(g["slots"], [f for f in files if f.filename]):
        images["choices"][slot["id"]] = {"type": "upload", "file": await _store_upload(job_id, slot["id"], f),
                                         "ts": int(time.time())}
    job.put("images", images)
    return _back(job_id, gid)


@app.post("/jobs/{job_id}/build")
def build(job_id: str, db_password: str = Form("")):
    job = _job_for_images(job_id)
    if job.request.db.get("type") == "mysql" and job_id not in SECRETS:
        SECRETS[job_id] = {"password": db_password}
    job.status = "building"
    job.save()
    start_in_background(job, "build")
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


# ============================================================ üretilen siteyi çalıştırma

def _running_url(job_id: str) -> str | None:
    entry = RUNNING.get(job_id)
    if entry and entry[0].poll() is None:
        return f"http://127.0.0.1:{entry[1]}"
    RUNNING.pop(job_id, None)
    return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _output_dir(job: dict) -> Path:
    out = Path(job.get("output_dir") or "")
    if job["status"] != "done" or not out.is_dir() or OUTPUT_DIR.resolve() not in out.resolve().parents:
        raise HTTPException(400, "Bu görevin çalıştırılabilir bir çıktısı yok.")
    return out


@app.post("/jobs/{job_id}/launch")
def launch(job_id: str):
    out = _output_dir(_job_dict(job_id))
    if not _running_url(job_id):
        port = _free_port()
        if (out / "artisan").exists():  # Laravel: PHP yerleşik sunucusu, public/ içinden
            cmd, cwd = [php_bin(), "-S", f"127.0.0.1:{port}", f"../{SERVER_SCRIPT}"], out / "public"
        else:
            cmd, cwd = [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)], out
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=NO_WINDOW)
        RUNNING[job_id] = (proc, port)
        for _ in range(40):  # sunucu ayağa kalkana kadar kısa bekleme
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                    break
            except OSError:
                time.sleep(0.25)
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/revise")
def revise(job_id: str, instruction: str = Form(...)):
    """Hazır siteyi kullanıcının cümlesiyle güncelle (veri korunur)."""
    job = load_job(_job_dict(job_id)["id"])
    _output_dir(job.to_dict())  # çıktının gerçekten var olduğunu doğrula
    if not instruction.strip():
        raise HTTPException(400, "Ne değiştirmek istediğinizi yazın.")
    start_in_background(job, "revision", instruction.strip()[:2000])
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/deploy")
def deploy(job_id: str, method: str = Form("ftp"), host: str = Form(...), port: int = Form(0),
           username: str = Form(...), password: str = Form(""), remote_dir: str = Form("/public_html"),
           site_url: str = Form(...), db_type: str = Form("sqlite"), db_host: str = Form("localhost"),
           db_port: int = Form(3306), db_database: str = Form(""), db_username: str = Form(""),
           db_password: str = Form("")):
    """Üretilen siteyi kullanıcının kendi sunucusuna yükler (arka planda)."""
    job = load_job(_job_dict(job_id)["id"])
    site_dir = _output_dir(job.to_dict())
    if not site_url.startswith(("http://", "https://")):
        site_url = "https://" + site_url.strip()
    db = {"type": "sqlite"}
    if db_type == "mysql":
        if not (db_host and db_database and db_username):
            raise HTTPException(400, "MySQL için sunucu, veritabanı adı ve kullanıcı adı gerekli.")
        db = {"type": "mysql", "host": db_host.strip(), "port": db_port, "database": db_database.strip(),
              "username": db_username.strip(), "password": db_password}
    target = Target(method=method, host=host.strip(), port=port, username=username.strip(), password=password,
                    remote_dir=remote_dir.strip() or "/", site_url=site_url.rstrip("/"), db=db)
    # şifreler diske yazılmaz; yalnızca formun hatırlanması için güvenli alanlar saklanır
    job.put("deploy_settings", {"method": method, "host": target.host, "port": port, "username": target.username,
                                "remote_dir": target.remote_dir, "site_url": target.site_url, "db_type": db_type,
                                "db_host": db_host, "db_port": db_port, "db_database": db_database,
                                "db_username": db_username})
    job.status = "deploying"
    job.save()

    def work():
        try:
            result = DeployAgent(job, site_dir).run(target)
            job.put("deploy", result)
            job.error = ""
        except Exception as e:
            job.error = f"Yayın başarısız: {e}"
            job.log(DeployAgent.name, job.error, "error")
        finally:
            job.status = "done"
            job.save()

    threading.Thread(target=work, daemon=True, name=f"deploy-{job_id}").start()
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/stop")
def stop(job_id: str):
    if entry := RUNNING.pop(job_id, None):
        entry[0].terminate()
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/open")
def open_target(job_id: str, what: str = Form("folder")):
    """Site klasörünü Gezgin'de ya da çalışan siteyi varsayılan tarayıcıda açar."""
    job = _job_dict(job_id)
    if what == "folder":
        target = str(_output_dir(job))
    else:
        base = _running_url(job_id) or ""
        if not base:
            raise HTTPException(400, "Önce siteyi başlatın.")
        target = base + ("/admin" if what == "admin" else "")
    if os.name == "nt":
        os.startfile(target)  # noqa: S606 — yalnızca kendi ürettiğimiz klasör/yerel URL
    else:
        import webbrowser
        webbrowser.open(target)
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)
