"""Üretilen sitenin uçtan uca duman testi.

Geçici bir veritabanıyla uygulamayı ayağa kaldırır; public sayfaları, iletişim formunu,
admin panelini (giriş, CRUD) ve REST API'yi dener.
Kullanım:  python tests/smoke_test.py [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

tmp = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = str(Path(tmp) / "test.db")
os.environ["ADMIN_USER"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-pass-123"
os.environ["API_TOKEN"] = "test-token"

checks: list[str] = []
errors: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (checks if cond else errors).append(name if cond else f"{name} {detail}".strip())


def csrf_of(html: str) -> str:
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    return m.group(1) if m else ""


def sample_value(f: dict, client) -> str:
    t = f["type"]
    return {
        "int": "3", "float": "2.5", "price": "199.90", "bool": "1", "date": "2026-01-15",
        "email": "test@example.com", "url": "https://example.com", "phone": "+90 555 000 00 00",
        "image": "https://picsum.photos/seed/test/400/300",
    }.get(t) or (f["options"][0] if t == "select" and f["options"] else None) or (
        "" if t == "relation" else f"Test {f['label']}"
    )


def main() -> None:
    try:
        from fastapi.testclient import TestClient
        import app as site
    except Exception as e:  # uygulama import edilemiyorsa tüm test başarısız
        errors.append(f"Uygulama yüklenemedi: {type(e).__name__}: {e}")
        return

    spec = site.SPEC
    c = TestClient(site.app)

    # ---------------------------------------------------------- public
    for path in ["/", "/health", "/contact", "/search?q=a", "/api/schema", "/olmayan-sayfa-xyz"]:
        r = c.get(path)
        expected = 404 if "olmayan" in path else 200
        check(f"GET {path} -> {expected}", r.status_code == expected, f"(aldı {r.status_code})")
    for p in spec["pages"]:
        r = c.get(f"/p/{p['slug']}")
        check(f"sayfa /p/{p['slug']}", r.status_code == 200, f"({r.status_code})")
    for e in spec["entities"]:
        r = c.get(f"/{e['name']}")
        check(f"liste /{e['name']}", r.status_code == (200 if e["public"] else 404), f"({r.status_code})")
        rows = c.get(f"/api/{e['name']}", headers={"Authorization": "Bearer test-token"}).json().get("items", [])
        if e["public"] and rows:
            r = c.get(f"/{e['name']}/{rows[0]['id']}")
            check(f"detay /{e['name']}/{rows[0]['id']}", r.status_code == 200, f"({r.status_code})")

    # ---------------------------------------------------------- iletişim formu
    html = c.get("/contact").text
    r = c.post("/contact", data={"csrf": csrf_of(html), "name": "Deneme", "email": "a@b.com",
                                 "subject": "Test", "body": "Merhaba, bu bir test."}, follow_redirects=False)
    check("iletişim formu gönderimi", r.status_code == 303, f"({r.status_code})")
    r = c.post("/contact", data={"name": "x", "email": "a@b.com", "body": "csrf yok"}, follow_redirects=False)
    check("CSRF koruması", r.status_code == 400, f"({r.status_code})")

    # ---------------------------------------------------------- API yetki
    if spec["entities"]:
        e0 = spec["entities"][0]["name"]
        r = c.post(f"/api/{e0}", json={})
        check("API yazma yetkisiz -> 401", r.status_code == 401, f"({r.status_code})")

    # ---------------------------------------------------------- admin
    r = c.get("/admin", follow_redirects=False)
    check("admin girişsiz -> yönlendirme", r.status_code == 303, f"({r.status_code})")
    html = c.get("/admin/login").text
    r = c.post("/admin/login", data={"csrf": csrf_of(html), "username": "admin", "password": "yanlis", "next": "/admin"})
    check("yanlış şifre reddedilir", r.status_code == 401, f"({r.status_code})")
    r = c.post("/admin/login", data={"csrf": csrf_of(html), "username": "admin", "password": "test-pass-123", "next": "/admin"},
               follow_redirects=False)
    check("admin girişi", r.status_code == 303, f"({r.status_code})")
    for path in ["/admin", "/admin/messages", "/admin/subscribers"]:
        r = c.get(path)
        check(f"GET {path}", r.status_code == 200, f"({r.status_code})")

    for e in spec["entities"]:
        name = e["name"]
        r = c.get(f"/admin/e/{name}")
        check(f"admin liste {name}", r.status_code == 200, f"({r.status_code})")
        form_html = c.get(f"/admin/e/{name}/new").text
        data = {"csrf": csrf_of(form_html)}
        for f in e["fields"]:
            v = sample_value(f, c)
            if f["type"] == "relation":
                opts = c.get(f"/api/{f['relation']}", headers={"Authorization": "Bearer test-token"}).json().get("items", [])
                v = str(opts[0]["id"]) if opts else ""
                if not v and f["required"]:
                    continue
            if v != "":
                data[f["name"]] = v
        r = c.post(f"/admin/e/{name}/new", data=data, follow_redirects=False)
        check(f"admin kayıt ekle {name}", r.status_code == 303, f"({r.status_code}) {r.text[:200] if r.status_code != 303 else ''}")
        items = c.get(f"/api/{name}").json().get("items", [])
        if items:
            rid = items[0]["id"]
            r = c.get(f"/admin/e/{name}/{rid}")
            check(f"admin düzenle formu {name}", r.status_code == 200, f"({r.status_code})")
            r = c.put(f"/api/{name}/{rid}", json={e["title_field"]: "API ile güncellendi"},
                      headers={"Authorization": "Bearer test-token"})
            check(f"API güncelle {name}", r.status_code == 200, f"({r.status_code}) {r.text[:200]}")
            r = c.post(f"/admin/e/{name}/{rid}/delete", data={"csrf": data["csrf"]}, follow_redirects=False)
            check(f"admin sil {name}", r.status_code == 303, f"({r.status_code})")


if __name__ == "__main__":
    main()
    result = {"passed": not errors, "checks": checks, "errors": errors}
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for x in checks:
            print("  OK  ", x)
        for x in errors:
            print("  FAIL", x)
        print(f"\n{len(checks)} başarılı, {len(errors)} hatalı")
    sys.exit(0 if not errors else 1)
