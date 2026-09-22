"""API anahtarı gerektirmeyen uçtan uca test.

Sahte bir LLM ile tüm ajan hattını çalıştırır; 'rakip' olarak yerelde ayağa kaldırılan
örnek site taranır. Tarayıcı, strateji matrisi, mimari/tasarım düzeltmeleri, Laravel inşası ve QA gerçek kodla çalışır.
(Laravel inşası görseller için Openverse'e bağlanır; PHP ve tools/laravel-base gerekir.)
Kullanım:  python tests/test_pipeline_offline.py
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from webagent.jobs import JobRequest, new_job  # noqa: E402
from webagent.llm import SearchHit  # noqa: E402
from webagent.orchestrator import Orchestrator  # noqa: E402
from webagent.schemas import (  # noqa: E402
    CompetitorList, EntitySeed, LegacyInfo, ModuleNormalization, PlanReport, SiteAnalysis, SiteSpec,
    Strategy, ThemeSpec,
)

EXAMPLE = json.loads((ROOT / "site_engine" / "example_site.json").read_text(encoding="utf-8"))


class FakeLLM:
    """Şemaya uygun sabit yanıtlar döndürür; hangi ajanın ne istediğini kaydeder."""

    def __init__(self):
        self.calls: list[str] = []

    def web_search(self, prompt: str, max_uses: int = 6):
        self.calls.append("web_search")
        return "araştırma notu", [SearchHit(url="https://ornek.com", title="Örnek")]

    def structured(self, system, prompt, output, effort="medium", max_tokens=16000):
        self.calls.append(output.__name__)
        if output is CompetitorList:
            return CompetitorList(competitors=[])
        if output is SiteAnalysis:
            return SiteAnalysis(
                url="", name="Yerel Klinik", summary="Test sitesi",
                modules=[{"key": "services", "title": "Tedaviler", "evidence": "menü"},
                         {"key": "team", "title": "Hekimler", "evidence": "menü"},
                         {"key": "contact_form", "title": "İletişim", "evidence": "form"}],
                content_types=["tedavi", "hekim"], strengths=["net menü"], weaknesses=["fiyat yok"],
            )
        if output is LegacyInfo:
            return LegacyInfo(
                business_name="Gülüş Diş Kliniği", about="2010'dan beri Alsancak'ta hizmet veriyoruz.",
                phone="+90 232 111 22 33", email="info@eskisite.test", address="Alsancak, İzmir",
                working_hours="Hafta içi 09:00-18:00", social_links=["https://instagram.com/test"],
                items=[{"name": "İmplant", "description": "Eski siteden gelen açıklama", "price": "15000", "category": "Cerrahi"}],
                highlights=["Uzman kadro"], missing=["Güncel fiyat listesi"],
            )
        if output is PlanReport:
            return PlanReport(
                summary="Özet.", included=[{"title": "Tedaviler", "detail": "Hizmet listesi"}],
                from_old_site=["İletişim bilgileri", "1 hizmet kaydı"],
                needed_from_user=[{"title": "Gerçek fotoğraflar", "detail": "Klinik fotoğrafları gerekiyor"}],
                risks=[{"title": "Örnek yorumlar", "detail": "Yayından önce kaldırılmalı"}],
                next_steps=["Görselleri seçin", "Siteyi kurun"],
            )
        if output is ModuleNormalization:
            return ModuleNormalization(mappings=[
                {"key": "services", "canonical": "services", "title": "Tedaviler"},
                {"key": "team", "canonical": "team", "title": "Hekimler"},
                {"key": "contact_form", "canonical": "contact_form", "title": "İletişim"},
            ])
        if output is Strategy:
            return Strategy(positioning="Şeffaf fiyatlı klinik", target_audience="25-45 yaş",
                            recommended_modules=EXAMPLE["modules"])
        if output is SiteSpec:
            spec = dict(EXAMPLE)
            # mimarın düzeltmesi gereken hatalı değerler
            spec["slug"] = "Test Klinik!"
            spec["hero"] = {**spec["hero"], "cta_link": "javascript:alert(1)"}
            spec["entities"] = [dict(e) for e in spec["entities"]]
            spec["entities"][0] = {**spec["entities"][0], "name": "Admin"}  # rezerve ad
            spec["entities"][1] = {**spec["entities"][1], "fields": [
                {**f, "relation": "admin"} if f["type"] == "relation" else f for f in spec["entities"][1]["fields"]]}
            return SiteSpec(**spec)
        if output is ThemeSpec:
            return ThemeSpec(
                preset="wellness", mode="light",  # kullanıcı "dark" seçtiği için ajan bunu düzeltmeli
                primary="#134e4a", accent="#f59e0b", surface="#f7faf9", ink="#1c1917",
                font_heading="Fraunces", font_body="Fraunces",  # aynı font: ajan düzeltmeli
                radius="round", hero_variant="split", hero_eyebrow="İzmir", hero_image_keywords="dental clinic",
                trust_items=["2010'dan beri", "Uzman kadro"], nav_entities=["services", "doctors", "faqs", "yok"],
                nav_labels=[{"entity": "services", "label": "Tedavilerimizin Tamamı ve Fiyatları"}],
                primary_cta_text="Hemen şimdi randevu alın", primary_cta_link="javascript:x",
                home_sections=[{"entity": "services", "display": "cards", "eyebrow": "Tedaviler", "title": "T", "subtitle": "S"},
                               {"entity": "doctors", "display": "cards", "eyebrow": "Ekip", "title": "T", "subtitle": "S"},
                               {"entity": "faqs", "display": "faq", "eyebrow": "SSS", "title": "T", "subtitle": "S"}],
                entity_displays=[], cta_band_title="Randevu", cta_band_text="Hemen arayın",
            )
        if output is EntitySeed:
            ent = next(e for e in EXAMPLE["entities"] if f"({e['name']})" in prompt or e["name"] in prompt)
            return EntitySeed(entity=ent["name"], records=[
                {"values": [{"field": f["name"], "value": _val(f, i)} for f in ent["fields"]]} for i in range(1, 4)
            ])
        raise AssertionError(output)


def _val(f: dict, i: int) -> str:
    return {"price": "1.250,50", "bool": "true", "date": "2026-05-01", "relation": "1",
            "phone": "+90 555", "image": "", "email": "a@b.com", "url": "https://x.com"}.get(
        f["type"], f["options"][0] if f["options"] else f"{f['label']} {i}")


OLD_SITE_HTML = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>Gülüş Diş Kliniği</title><meta name="description" content="Alsancak'ta diş kliniği">
<meta property="og:image" content="/klinik.jpg"></head><body>
<nav><a href="/">Ana sayfa</a> <a href="/hizmetler.html">Hizmetlerimiz</a></nav>
<h1>Gülüş Diş Kliniği</h1>
<p>2010'dan beri Alsancak'ta hizmet veriyoruz. Telefon: +90 232 111 22 33 · info@eskisite.test</p>
<p>Adres: Alsancak Mah. 1 Sk. No:2, İzmir · Hafta içi 09:00-18:00</p>
<h2>Hizmetlerimiz</h2><ul><li>İmplant — 15.000 TL</li><li>Diş beyazlatma</li></ul>
<img src="/klinik.jpg" width="900" height="600" alt="Klinik içi">
<img src="/ekip.jpg" width="900" height="600" alt="Hekim kadromuz">
</body></html>"""


def start_old_site(port: int) -> object:
    """Kullanıcının 'mevcut sitesi' gibi davranan küçük statik sunucu (görselleriyle birlikte)."""
    import http.server
    import tempfile
    import threading

    from PIL import Image

    root = Path(tempfile.mkdtemp(prefix="oldsite-"))
    (root / "index.html").write_text(OLD_SITE_HTML, encoding="utf-8")
    (root / "hizmetler.html").write_text(OLD_SITE_HTML, encoding="utf-8")
    for name, color in (("klinik.jpg", (210, 225, 235)), ("ekip.jpg", (235, 225, 210))):
        Image.new("RGB", (900, 600), color).save(root / name, "JPEG")

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(root), **kw)  # noqa: E731
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    # 'rakip' olarak örnek siteyi, 'kullanıcının mevcut sitesi' olarak küçük statik siteyi ayağa kaldır
    port, old_port = free_port(), free_port()
    old_site = start_old_site(old_port)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(port)],
                            cwd=ROOT / "site_engine", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.25).close()
                break
            except OSError:
                time.sleep(0.25)

        job = new_job(JobRequest(sector="diş kliniği", competitor_urls=[f"http://127.0.0.1:{port}"],
                                 max_competitors=1, style="dark",
                                 own_site=f"http://127.0.0.1:{old_port}"))  # kullanıcının mevcut sitesi
        llm = FakeLLM()
        Orchestrator(job, llm=llm).run()

        for e in job.events:
            print(f"[{e.level:5}] {e.agent}: {e.message}")
        print("\nLLM çağrıları:", llm.calls)
        assert job.status == "done", job.error
        # eski siteden gelen bilgiler kullanıldı mı?
        assert job.artifacts["legacy"]["phone"] == "+90 232 111 22 33"
        assert job.artifacts["legacy_images"], "eski siteden görsel toplanmadı"
        assert job.artifacts["spec"]["contact_phone"] == "+90 232 111 22 33", "eski sitenin telefonu kullanılmalı"
        # plan raporu üretildi mi?
        report = job.artifacts["report"]
        assert report["report"]["summary"] and report["facts"]["entities"], report
        assert report["facts"]["images"]["own_site"] > 0, "kendi görselleri öneri havuzunda olmalı"
        crawl = job.artifacts["crawls"][0]
        assert crawl["ok"] and len(crawl["pages"]) > 1, crawl
        assert "search" in crawl["signals"] and "newsletter" in crawl["signals"], crawl["signals"]
        spec = job.artifacts["spec"]
        theme = spec["theme"]
        assert theme["mode"] == "dark", "kullanıcının seçtiği koyu görünüm uygulanmalı"
        assert theme["surface"].lower() in ("#0d1516", "#0f1115") or theme["surface"] != "#f7faf9", theme["surface"]
        assert theme["font_body"] != theme["font_heading"], "başlık/gövde fontu ayrılmalıydı"
        assert theme["primary_cta_link"] == "/contact" and len(theme["primary_cta_text"].split()) <= 3
        assert "yok" not in theme["nav_entities"] and all(len(n["label"]) <= 18 for n in theme["nav_labels"])
        assert theme["home_sections"][1]["display"] != "cards", "art arda aynı düzen düzeltilmeliydi"
        assert spec["slug"] == "test-klinik", spec["slug"]
        assert spec["hero"]["cta_link"].startswith("/"), spec["hero"]["cta_link"]
        assert spec["entities"][0]["name"] == "admin_items"
        assert any(f.get("relation") == "admin_items" for f in spec["entities"][1]["fields"]), "ilişki yeniden adlandırmayı izlemeli"
        assert job.artifacts["qa"]["passed"], job.artifacts["qa"]["errors"]
        print(f"\nTAMAM — site üretildi ve QA geçti: {job.output_dir}")
        return 0
    finally:
        proc.terminate()
        old_site.shutdown()


if __name__ == "__main__":
    sys.exit(main())
