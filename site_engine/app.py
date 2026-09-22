"""Web Agent tarafından üretilen site: public site + REST API + admin paneli.

Tüm yapı site.json'dan okunur; veritabanı SQLite'tır (site.db).
Çalıştırma:  python -m uvicorn app:app --reload
"""
from __future__ import annotations

import json
import math
import os
import secrets
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from db import DB, ValidationError
from render import excerpt, fmt, markdown

BASE = Path(__file__).resolve().parent


def load_env() -> None:
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
SPEC_FILE = BASE / "site.json" if (BASE / "site.json").exists() else BASE / "example_site.json"
SPEC: dict = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
ENTITIES: dict[str, dict] = {e["name"]: e for e in SPEC["entities"]}
PUBLIC_ENTITIES = [e for e in SPEC["entities"] if e["public"]]
CURRENCY = SPEC.get("currency") or ("₺" if SPEC.get("language", "tr").startswith("tr") else "$")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
API_TOKEN = os.environ.get("API_TOKEN", "")

db = DB(Path(os.environ.get("DATABASE_PATH", BASE / "site.db")), SPEC)
db.init_schema()
SEED_FILE = BASE / ("seed.json" if SPEC_FILE.name == "site.json" else "example_seed.json")
if db.is_empty() and SEED_FILE.exists():
    db.seed(json.loads(SEED_FILE.read_text(encoding="utf-8")))

app = FastAPI(title=SPEC["site_name"], docs_url="/api/docs", redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax", max_age=60 * 60 * 8)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

templates = Jinja2Templates(directory=BASE / "templates")
templates.env.filters["md"] = markdown
templates.env.filters["excerpt"] = excerpt
templates.env.globals.update(
    site=SPEC,
    public_entities=PUBLIC_ENTITIES,
    all_entities=SPEC["entities"],
    nav_pages=[p for p in SPEC["pages"] if p["in_nav"]],
    fmt=lambda v, f, rel=None: fmt(v, f, CURRENCY, rel),
    year=time.strftime("%Y"),
)


# ================================================================ yardımcılar

def csrf_token(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(24)
    return request.session["csrf"]


templates.env.globals["csrf_token"] = csrf_token


async def form_data(request: Request) -> dict:
    form = await request.form()
    if not secrets.compare_digest(str(form.get("csrf", "")), request.session.get("csrf", "")):
        raise HTTPException(400, "Geçersiz form anahtarı (CSRF). Sayfayı yenileyip tekrar deneyin.")
    return {k: v for k, v in form.items() if k != "csrf"}


def render(request: Request, name: str, status: int = 200, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(request, name, ctx, status_code=status)


def get_entity(name: str, public_only: bool = False) -> dict:
    ent = ENTITIES.get(name)
    if not ent or (public_only and not ent["public"]):
        raise HTTPException(404, "Sayfa bulunamadı")
    return ent


def relations_for(ent: dict) -> dict[str, dict[int, str]]:
    return {f["name"]: db.titles(f["relation"]) for f in ent["fields"] if f["type"] == "relation"}


def is_admin(request: Request) -> bool:
    return request.session.get("admin") is True


class AdminRequired(Exception):
    pass


@app.exception_handler(AdminRequired)
async def _admin_redirect(request: Request, exc: AdminRequired):
    return RedirectResponse(f"/admin/login?next={request.url.path}", status_code=303)


@app.exception_handler(404)
async def _not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Bulunamadı"}, status_code=404)
    return render(request, "404.html", status=404)


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise AdminRequired()


def require_api_write(request: Request) -> None:
    auth = request.headers.get("authorization", "")
    token_ok = API_TOKEN and auth.startswith("Bearer ") and secrets.compare_digest(auth[7:], API_TOKEN)
    if not (token_ok or is_admin(request)):
        raise HTTPException(401, "Yetkisiz. 'Authorization: Bearer <API_TOKEN>' gerekli.")


# ================================================================ public site

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    sections = []
    for ent in SPEC["entities"]:
        if ent["public"] and ent["show_on_home"]:
            rows, _ = db.list(ent["name"], per_page=6)
            sections.append({"entity": ent, "rows": rows, "relations": relations_for(ent)})
    return render(request, "home.html", sections=sections)


@app.get("/health")
def health():
    return {"status": "ok", "site": SPEC["site_name"]}


@app.get("/p/{slug}", response_class=HTMLResponse)
def page(request: Request, slug: str):
    pg = next((p for p in SPEC["pages"] if p["slug"] == slug), None)
    if not pg:
        raise HTTPException(404)
    return render(request, "page.html", page=pg)


@app.get("/contact", response_class=HTMLResponse)
def contact_form(request: Request, sent: int = 0):
    return render(request, "contact.html", sent=sent, errors={}, values={})


@app.post("/contact", response_class=HTMLResponse)
async def contact_submit(request: Request):
    data = await form_data(request)
    errors = {}
    if not str(data.get("name", "")).strip():
        errors["name"] = "Adınızı yazın"
    if "@" not in str(data.get("email", "")):
        errors["email"] = "Geçerli bir e-posta girin"
    if len(str(data.get("body", "")).strip()) < 5:
        errors["body"] = "Mesajınızı yazın"
    if data.get("website"):  # bal küpü (spam botları doldurur)
        return RedirectResponse("/contact?sent=1", status_code=303)
    if errors:
        return render(request, "contact.html", status=422, sent=0, errors=errors, values=data)
    db.add_message(**{k: str(data.get(k, ""))[:5000] for k in ("name", "email", "phone", "subject", "body")})
    return RedirectResponse("/contact?sent=1", status_code=303)


@app.post("/newsletter")
async def newsletter(request: Request):
    data = await form_data(request)
    email = str(data.get("email", "")).strip()
    if "@" in email and len(email) < 200:
        db.subscribe(email)
    return RedirectResponse("/?subscribed=1#newsletter", status_code=303)


@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = ""):
    results = []
    if q.strip():
        for ent in PUBLIC_ENTITIES:
            rows, total = db.list(ent["name"], search=q.strip(), per_page=10)
            if rows:
                results.append({"entity": ent, "rows": rows, "total": total})
    return render(request, "search.html", q=q, results=results)


# ================================================================ REST API

@app.get("/api/schema")
def api_schema():
    return {"site": SPEC["site_name"], "entities": [
        {"name": e["name"], "public": e["public"], "fields": e["fields"]} for e in SPEC["entities"]]}


@app.get("/api/{entity}")
def api_list(request: Request, entity: str, q: str = "", page: int = 1, per_page: int = 20):
    ent = get_entity(entity)
    if not ent["public"]:
        require_api_write(request)
    rows, total = db.list(entity, search=q, page=page, per_page=min(max(per_page, 1), 100))
    return {"items": rows, "total": total, "page": page}


@app.get("/api/{entity}/{row_id}")
def api_get(request: Request, entity: str, row_id: int):
    ent = get_entity(entity)
    if not ent["public"]:
        require_api_write(request)
    row = db.get(entity, row_id)
    if not row:
        raise HTTPException(404)
    return row


@app.post("/api/{entity}", status_code=201)
async def api_create(request: Request, entity: str):
    get_entity(entity)
    require_api_write(request)
    try:
        new_id = db.create(entity, await request.json())
    except ValidationError as e:
        raise HTTPException(422, e.errors)
    return db.get(entity, new_id)


@app.put("/api/{entity}/{row_id}")
async def api_update(request: Request, entity: str, row_id: int):
    get_entity(entity)
    require_api_write(request)
    if not db.get(entity, row_id):
        raise HTTPException(404)
    try:
        db.update(entity, row_id, await request.json(), partial=True)
    except ValidationError as e:
        raise HTTPException(422, e.errors)
    return db.get(entity, row_id)


@app.delete("/api/{entity}/{row_id}", status_code=204)
def api_delete(request: Request, entity: str, row_id: int):
    get_entity(entity)
    require_api_write(request)
    db.delete(entity, row_id)


# ================================================================ admin paneli

_login_attempts: dict[str, list[float]] = defaultdict(list)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form(request: Request, next: str = "/admin"):
    return render(request, "admin/login.html", error="", next=next)


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    data = await form_data(request)
    ip = request.client.host if request.client else "?"
    recent = [t for t in _login_attempts[ip] if time.time() - t < 300]
    _login_attempts[ip] = recent
    nxt = str(data.get("next", "/admin"))
    if not nxt.startswith("/admin"):
        nxt = "/admin"
    if len(recent) >= 10:
        return render(request, "admin/login.html", status=429, error="Çok fazla deneme. 5 dakika sonra tekrar deneyin.", next=nxt)
    ok = (
        ADMIN_PASSWORD
        and secrets.compare_digest(str(data.get("username", "")), ADMIN_USER)
        and secrets.compare_digest(str(data.get("password", "")), ADMIN_PASSWORD)
    )
    if not ok:
        _login_attempts[ip].append(time.time())
        return render(request, "admin/login.html", status=401, error="Kullanıcı adı veya şifre hatalı.", next=nxt)
    request.session.clear()
    request.session["admin"] = True
    return RedirectResponse(nxt, status_code=303)


@app.post("/admin/logout")
async def admin_logout(request: Request):
    await form_data(request)
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    require_admin(request)
    stats = [{"entity": e, "count": db.count(e["name"])} for e in SPEC["entities"]]
    return render(
        request, "admin/dashboard.html", stats=stats, messages=db.messages()[:5],
        unread=db.unread_count(), subscribers=len(db.subscribers()),
    )


@app.get("/admin/messages", response_class=HTMLResponse)
def admin_messages(request: Request):
    require_admin(request)
    return render(request, "admin/messages.html", messages=db.messages(), unread=db.unread_count())


@app.post("/admin/messages/{msg_id}/{action}")
async def admin_message_action(request: Request, msg_id: int, action: str):
    require_admin(request)
    await form_data(request)
    if action == "read":
        db.mark_read(msg_id)
    elif action == "delete":
        db.delete_message(msg_id)
    return RedirectResponse("/admin/messages", status_code=303)


@app.get("/admin/subscribers", response_class=HTMLResponse)
def admin_subscribers(request: Request):
    require_admin(request)
    return render(request, "admin/subscribers.html", subscribers=db.subscribers(), unread=db.unread_count())


@app.get("/admin/e/{entity}", response_class=HTMLResponse)
def admin_list(request: Request, entity: str, q: str = "", page: int = 1):
    require_admin(request)
    ent = get_entity(entity)
    rows, total = db.list(entity, search=q, page=page, per_page=25)
    return render(
        request, "admin/list.html", entity=ent, rows=rows, total=total, q=q, page=page,
        pages=max(1, math.ceil(total / 25)), relations=relations_for(ent), unread=db.unread_count(),
    )


@app.get("/admin/e/{entity}/new", response_class=HTMLResponse)
def admin_new(request: Request, entity: str):
    require_admin(request)
    ent = get_entity(entity)
    return render(request, "admin/form.html", entity=ent, row={}, errors={}, options=relations_for(ent), unread=db.unread_count())


@app.post("/admin/e/{entity}/new", response_class=HTMLResponse)
async def admin_create(request: Request, entity: str):
    require_admin(request)
    ent = get_entity(entity)
    data = await form_data(request)
    try:
        db.create(entity, data)
    except ValidationError as e:
        return render(request, "admin/form.html", status=422, entity=ent, row=data, errors=e.errors,
                      options=relations_for(ent), unread=db.unread_count())
    return RedirectResponse(f"/admin/e/{entity}?saved=1", status_code=303)


@app.get("/admin/e/{entity}/{row_id}", response_class=HTMLResponse)
def admin_edit(request: Request, entity: str, row_id: int):
    require_admin(request)
    ent = get_entity(entity)
    row = db.get(entity, row_id)
    if not row:
        raise HTTPException(404)
    return render(request, "admin/form.html", entity=ent, row=row, errors={}, options=relations_for(ent), unread=db.unread_count())


@app.post("/admin/e/{entity}/{row_id}", response_class=HTMLResponse)
async def admin_update(request: Request, entity: str, row_id: int):
    require_admin(request)
    ent = get_entity(entity)
    data = await form_data(request)
    try:
        db.update(entity, row_id, data)
    except ValidationError as e:
        return render(request, "admin/form.html", status=422, entity=ent, row={**data, "id": row_id},
                      errors=e.errors, options=relations_for(ent), unread=db.unread_count())
    return RedirectResponse(f"/admin/e/{entity}?saved=1", status_code=303)


@app.post("/admin/e/{entity}/{row_id}/delete")
async def admin_delete(request: Request, entity: str, row_id: int):
    require_admin(request)
    get_entity(entity)
    await form_data(request)
    db.delete(entity, row_id)
    return RedirectResponse(f"/admin/e/{entity}?deleted=1", status_code=303)


# ================================================================ varlık sayfaları (en sonda)

@app.get("/{entity}", response_class=HTMLResponse)
def entity_list(request: Request, entity: str, q: str = "", page: int = 1):
    ent = get_entity(entity, public_only=True)
    rows, total = db.list(entity, search=q, page=page, per_page=12)
    return render(request, "list.html", entity=ent, rows=rows, total=total, q=q, page=page,
                  pages=max(1, math.ceil(total / 12)), relations=relations_for(ent))


@app.get("/{entity}/{row_id}", response_class=HTMLResponse)
def entity_detail(request: Request, entity: str, row_id: int):
    ent = get_entity(entity, public_only=True)
    row = db.get(entity, row_id)
    if not row:
        raise HTTPException(404)
    others, _ = db.list(entity, per_page=4)
    return render(request, "detail.html", entity=ent, row=row, relations=relations_for(ent),
                  others=[o for o in others if o["id"] != row_id][:3])
