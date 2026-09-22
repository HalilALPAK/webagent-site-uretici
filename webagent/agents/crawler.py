"""Tarayıcı Ajanı: rakip siteleri gezip yapısal sinyalleri çıkarır (LLM kullanmaz)."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import CRAWL_MAX_PAGES_PER_SITE, CRAWL_TIMEOUT, CRAWL_USER_AGENT
from .base import Agent

# Sayfa metni/HTML'inde aranan hızlı özellik sinyalleri
FEATURE_PATTERNS = {
    "shopping_cart": r"sepet|cart|basket|add[- ]to[- ]cart|sepete ekle",
    "checkout_payment": r"checkout|ödeme|odeme|payment|iyzico|stripe|paytr",
    "booking_appointment": r"randevu|appointment|rezervasyon|reservation|booking|book now",
    "blog_news": r"/blog|haberler|/news|makaleler|articles",
    "search": r'type="search"|name="q"|name="s"|arama|search',
    "user_accounts": r"giriş yap|üye ol|login|sign in|register|hesabım|my account",
    "newsletter": r"bülten|newsletter|abone ol|subscribe",
    "live_chat": r"tawk\.to|intercom|crisp\.chat|livechat|zendesk|jivosite|whatsapp",
    "locations_map": r"maps\.google|google\.com/maps|şubeler|subeler|locations|harita",
    "faq": r"sıkça sorulan|sss|faq|frequently asked",
    "jobs_careers": r"kariyer|career|jobs|iş ilanları|insan kaynakları",
    "multi_language": r'hreflang=|/en/|lang-switch|language',
    "testimonials_reviews": r"yorumlar|testimonial|reviews|müşteri görüşleri|referanslar",
    "pricing_plans": r"fiyatlar|pricing|paketler|plans|₺|tl/ay",
    "quote_request": r"teklif al|get a quote|fiyat teklifi|request a quote",
}

TECH_PATTERNS = {
    "WordPress": r"wp-content|wp-includes",
    "WooCommerce": r"woocommerce",
    "Shopify": r"cdn\.shopify\.com",
    "Ticimax": r"ticimax",
    "IdeaSoft": r"ideasoft",
    "Wix": r"wix\.com|wixstatic",
    "Next.js": r"__next|_next/static",
    "React": r"data-reactroot|react",
    "Google Analytics": r"googletagmanager|google-analytics",
}

_LINK_HINTS = re.compile(
    r"hizmet|service|urun|ürün|product|hakkimizda|about|iletisim|contact|blog|fiyat|pricing|"
    r"randevu|booking|kategori|category|shop|magaza|kurumsal|sss|faq", re.I
)


@dataclass
class PageData:
    url: str
    title: str = ""
    headings: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    text: str = ""
    images: list[dict] = field(default_factory=list)  # {"url", "alt"} — eski siteden devralmada kullanılır


@dataclass
class CrawlResult:
    url: str
    ok: bool = False
    error: str = ""
    meta_description: str = ""
    nav: list[str] = field(default_factory=list)
    footer_links: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    tech: list[str] = field(default_factory=list)
    pages: list[PageData] = field(default_factory=list)

    def digest(self, max_chars: int = 9000) -> str:
        """LLM'e gönderilecek özet metin."""
        parts = [
            f"URL: {self.url}",
            f"Meta açıklama: {self.meta_description}",
            f"Ana menü: {' | '.join(self.nav[:40])}",
            f"Footer linkleri: {' | '.join(self.footer_links[:40])}",
            f"Otomatik algılanan sinyaller: {', '.join(self.signals) or '-'}",
            f"Teknoloji: {', '.join(self.tech) or '-'}",
        ]
        for p in self.pages:
            parts.append(
                f"\n--- Sayfa: {p.url}\nBaşlık: {p.title}\nBaşlıklar: {' | '.join(p.headings[:25])}\n"
                f"Formlar: {' ; '.join(p.forms[:6]) or '-'}\n"
                f"Görseller: {', '.join(i['alt'] or i['url'].rsplit('/', 1)[-1] for i in p.images[:8]) or '-'}\n"
                f"Metin: {p.text[:1200]}"
            )
        return "\n".join(parts)[:max_chars]


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


class CrawlerAgent(Agent):
    name = "Tarayıcı Ajanı"
    role = "Rakip siteleri gezip menü, form, sayfa ve teknoloji sinyallerini toplamak."

    def run(self, url: str) -> CrawlResult:
        result = CrawlResult(url=url)
        headers = {"User-Agent": CRAWL_USER_AGENT, "Accept-Language": "tr,en;q=0.8"}
        try:
            with httpx.Client(headers=headers, timeout=CRAWL_TIMEOUT, follow_redirects=True) as client:
                robots = self._robots(client, url)
                resp = client.get(url)
                resp.raise_for_status()
                html = resp.text
                base = str(resp.url)
                soup = BeautifulSoup(html, "html.parser")

                desc = soup.find("meta", attrs={"name": "description"})
                result.meta_description = _clean(desc.get("content", "")) if desc else ""
                result.nav = self._link_texts(soup.select("header a, nav a"))
                result.footer_links = self._link_texts(soup.select("footer a"))
                result.tech = [k for k, pat in TECH_PATTERNS.items() if re.search(pat, html, re.I)]

                all_html = [html]
                result.pages.append(self._page(base, soup))

                for link in self._candidate_links(soup, base)[: CRAWL_MAX_PAGES_PER_SITE - 1]:
                    if robots and not robots.can_fetch(CRAWL_USER_AGENT, link):
                        continue
                    try:
                        r = client.get(link)
                        if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                            all_html.append(r.text)
                            result.pages.append(self._page(str(r.url), BeautifulSoup(r.text, "html.parser")))
                    except httpx.HTTPError:
                        continue

                joined = "\n".join(all_html)
                result.signals = [k for k, pat in FEATURE_PATTERNS.items() if re.search(pat, joined, re.I)]
                result.ok = True
                self.log(f"{urlparse(url).netloc}: {len(result.pages)} sayfa, sinyaller: {', '.join(result.signals) or '-'}", "ok")
        except Exception as e:  # ağ, SSL, parse… hiçbiri tüm hattı durdurmamalı
            result.error = f"{type(e).__name__}: {e}"
            self.log(f"{url} taranamadı: {result.error}", "warn")
        return result

    # ------------------------------------------------------------ yardımcılar
    @staticmethod
    def _robots(client: httpx.Client, url: str) -> robotparser.RobotFileParser | None:
        try:
            r = client.get(urljoin(url, "/robots.txt"))
            if r.status_code != 200:
                return None
            rp = robotparser.RobotFileParser()
            rp.parse(r.text.splitlines())
            return rp
        except httpx.HTTPError:
            return None

    @staticmethod
    def _link_texts(links) -> list[str]:
        out: list[str] = []
        for a in links:
            t = _clean(a.get_text(" "))
            if t and len(t) < 50 and t not in out:
                out.append(t)
        return out

    @staticmethod
    def _candidate_links(soup: BeautifulSoup, base: str) -> list[str]:
        host = urlparse(base).netloc
        scored: dict[str, int] = {}
        for a in soup.find_all("a", href=True):
            href = urljoin(base, a["href"]).split("#")[0]
            p = urlparse(href)
            if p.netloc != host or p.scheme not in ("http", "https") or href.rstrip("/") == base.rstrip("/"):
                continue
            if re.search(r"\.(jpg|jpeg|png|gif|pdf|zip|svg|webp)$", p.path, re.I):
                continue
            score = 2 if _LINK_HINTS.search(href + " " + a.get_text(" ")) else 0
            score += 1 if p.path.count("/") <= 2 else 0
            scored[href] = max(scored.get(href, 0), score)
        return [u for u, _ in sorted(scored.items(), key=lambda kv: -kv[1])]

    @staticmethod
    def _images(soup: BeautifulSoup, base: str) -> list[dict]:
        """Sayfadaki içerik görselleri: ikon/logo/izleme pikseli gibi küçük dosyalar elenir."""
        found: dict[str, dict] = {}
        og = soup.find("meta", attrs={"property": "og:image"})
        if og and og.get("content"):
            found[urljoin(base, og["content"])] = {"url": urljoin(base, og["content"]), "alt": "og:image"}
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
            if not src or src.startswith("data:"):
                continue
            url = urljoin(base, src.split("?")[0])
            if not re.search(r"\.(jpe?g|png|webp)$", urlparse(url).path, re.I):
                continue
            if re.search(r"logo|icon|sprite|placeholder|avatar|pixel|blank|spacer|whatsapp|favicon", url, re.I):
                continue
            try:  # HTML'de boyut belirtilmişse küçükleri ele
                if int(img.get("width") or 999) < 300 or int(img.get("height") or 999) < 200:
                    continue
            except ValueError:
                pass
            found.setdefault(url, {"url": url, "alt": _clean(img.get("alt") or "")})
        return list(found.values())[:20]

    @staticmethod
    def _page(url: str, soup: BeautifulSoup) -> PageData:
        forms = []
        for f in soup.find_all("form"):
            fields = [i.get("name") or i.get("placeholder") or i.get("type") for i in f.find_all(["input", "select", "textarea"])]
            fields = [x for x in fields if x and x not in ("hidden", "submit")]
            if fields:
                forms.append(", ".join(fields[:10]))
        images = CrawlerAgent._images(soup, url)
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        return PageData(
            url=url,
            images=images,
            title=_clean(soup.title.get_text()) if soup.title else "",
            headings=[_clean(h.get_text(" ")) for h in soup.find_all(["h1", "h2", "h3"]) if _clean(h.get_text(" "))][:30],
            forms=forms,
            text=_clean(soup.get_text(" "))[:3000],
        )


def crawl_to_dict(c: CrawlResult, keep_images: bool = False) -> dict:
    d = asdict(c)
    for p in d["pages"]:
        p["text"] = p["text"][:400]
        if not keep_images:
            p["images"] = []
    return d
