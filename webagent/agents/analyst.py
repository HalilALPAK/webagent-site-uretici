"""Analist Ajanı: taranan bir sitenin modüllerini ve içerik türlerini çıkarır."""
from __future__ import annotations

from ..schemas import MODULE_KEYS, SiteAnalysis
from .base import Agent
from .crawler import CrawlResult


class AnalystAgent(Agent):
    name = "Analist Ajanı"
    role = "Bir rakip sitenin hangi modüllere/özelliklere sahip olduğunu kanıtlarıyla tespit etmek."

    def run(self, crawl: CrawlResult, competitor_name: str) -> SiteAnalysis:
        system = self.system_prompt(
            "Modül anahtarı olarak mümkünse şu kanonik listeden seç: "
            + ", ".join(MODULE_KEYS)
            + ". Listede karşılığı olmayan belirgin bir modül varsa kısa snake_case yeni anahtar üret. "
            "Sadece verilen tarama verisinde kanıtı olan modülleri yaz; tahmin yürütme."
        )
        analysis = self.llm.structured(
            system,
            f"Rakip: {competitor_name}\n\nTarama verisi:\n{crawl.digest()}",
            SiteAnalysis,
            effort="low",
        )
        analysis.url = crawl.url
        self.log(f"{analysis.name}: {len(analysis.modules)} modül — {', '.join(m.key for m in analysis.modules)}", "ok")
        return analysis
