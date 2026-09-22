"""Keşif Ajanı: sektördeki rakip siteleri web aramasıyla bulur."""
from __future__ import annotations

from urllib.parse import urlparse

from ..schemas import Competitor, CompetitorList
from .base import Agent

# Rakip olarak sayılmaması gereken genel platformlar
_SKIP_DOMAINS = (
    "wikipedia.org", "youtube.com", "facebook.com", "instagram.com", "linkedin.com",
    "twitter.com", "x.com", "tiktok.com", "google.", "sikayetvar.com", "eksisozluk.com",
    "reddit.com", "medium.com", "pinterest.",
)


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


class ScoutAgent(Agent):
    name = "Keşif Ajanı"
    role = "Sektördeki en güçlü rakip web sitelerini bulmak."

    def run(self) -> list[Competitor]:
        req = self.job.request
        given = [normalize_url(u) for u in req.competitor_urls if u.strip()]
        competitors = [Competitor(name=urlparse(u).netloc, url=u, why="Kullanıcı tarafından verildi") for u in given]
        need = max(0, req.max_competitors - len(competitors))
        if need == 0:
            self.log(f"{len(competitors)} rakip kullanıcıdan alındı, arama atlandı.", "ok")
            return competitors

        self.log(f"'{req.sector}' sektörü için {need} rakip aranıyor ({req.location})…")
        research, hits = self.llm.web_search(
            f"'{req.sector}' sektöründe {req.location} pazarında faaliyet gösteren, web sitesi "
            f"güçlü olan önde gelen {need + 3} şirketi/markayı bul. Dizin, haber, sosyal medya "
            "ve pazaryeri sitelerini değil, şirketlerin kendi resmi sitelerini hedefle. "
            "Her biri için resmi site adresini ve kısa gerekçeyi yaz."
        )
        self.log(f"Web aramasında {len(hits)} sonuç bulundu, rakipler seçiliyor…")

        hit_lines = "\n".join(f"- {h.title} — {h.url}" for h in hits[:60])
        chosen = self.llm.structured(
            self.system_prompt(),
            f"Araştırma notları:\n{research}\n\nArama sonuçları:\n{hit_lines}\n\n"
            f"Bu bilgilerden sektörün en temsilî {need} rakibini seç. Yalnızca şirketin kendi "
            "resmi web sitesinin ana sayfa URL'sini ver. Şu zaten listede, tekrar etme: "
            f"{', '.join(given) or '-'}",
            CompetitorList,
            effort="low",
        )
        seen = {urlparse(c.url).netloc for c in competitors}
        for c in chosen.competitors:
            c.url = normalize_url(c.url)
            host = urlparse(c.url).netloc
            if host in seen or any(s in host for s in _SKIP_DOMAINS):
                continue
            seen.add(host)
            competitors.append(c)
            if len(competitors) >= req.max_competitors:
                break

        for c in competitors:
            self.log(f"Rakip: {c.name} ({c.url})", "ok")
        return competitors
