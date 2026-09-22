"""Stratejist Ajanı: rakip analizlerinden özellik matrisi ve modül önerisi üretir."""
from __future__ import annotations

from collections import defaultdict

from ..schemas import ModuleNormalization, SiteAnalysis, Strategy
from .base import Agent


def feature_matrix(analyses: list[SiteAnalysis]) -> list[dict]:
    """Hangi modül kaç rakipte var? (deterministik, LLM'siz)"""
    rows: dict[str, dict] = defaultdict(lambda: {"title": "", "sites": []})
    for a in analyses:
        for m in a.modules:
            row = rows[m.key]
            row["title"] = row["title"] or m.title
            if a.name not in row["sites"]:
                row["sites"].append(a.name)
    total = max(1, len(analyses))
    matrix = [
        {"key": k, "title": v["title"], "count": len(v["sites"]), "coverage": round(100 * len(v["sites"]) / total), "sites": v["sites"]}
        for k, v in rows.items()
    ]
    return sorted(matrix, key=lambda r: (-r["count"], r["key"]))


class StrategistAgent(Agent):
    name = "Stratejist Ajanı"
    role = "Rakiplerin ortak ve eksik yönlerinden yeni sitenin modül setini ve konumlandırmasını belirlemek."

    def normalize(self, analyses: list[SiteAnalysis]) -> None:
        """Farklı analistlerin aynı modüle verdiği farklı anahtarları birleştirir (yerinde günceller)."""
        keys = sorted({(m.key, m.title) for a in analyses for m in a.modules})
        if len(keys) < 2:
            return
        result = self.llm.structured(
            self.system_prompt(
                "Aynı işlevi gören modül anahtarlarını tek bir ortak anahtarda birleştir "
                "(ör. rooms_suites ve room_catalog -> rooms). Farklı işlevleri birleştirme. "
                "Listedeki her anahtar için tam olarak bir eşleme döndür."
            ),
            "\n".join(f"- {k}: {t}" for k, t in keys),
            ModuleNormalization,
            effort="low",
        )
        mapping = {m.key: m for m in result.mappings}
        merged = 0
        for a in analyses:
            seen: set[str] = set()
            kept = []
            for m in a.modules:
                target = mapping.get(m.key)
                if target and target.canonical != m.key:
                    m.key, m.title = target.canonical, target.title
                    merged += 1
                if m.key not in seen:
                    seen.add(m.key)
                    kept.append(m)
            a.modules = kept
        self.log(f"{len(keys)} modül anahtarı normalize edildi ({merged} eşleme birleştirildi).", "ok")

    def run(self, analyses: list[SiteAnalysis], matrix: list[dict]) -> Strategy:
        matrix_txt = "\n".join(f"- {r['key']} ({r['title']}): {r['count']}/{len(analyses)} rakipte" for r in matrix)
        summaries = "\n".join(
            f"- {a.name}: {a.summary}\n  Güçlü: {'; '.join(a.strengths)}\n  Zayıf: {'; '.join(a.weaknesses)}"
            for a in analyses
        )
        req = self.job.request
        strategy = self.llm.structured(
            self.system_prompt(
                "Kurallar: rakiplerin çoğunda olan modüller 'must'; yarısından azında olup değer katan "
                "modüller 'should'; rakiplerin zayıf yönlerini kapatan ve az rakipte olan modüller "
                "'differentiator'. Toplam 6-12 modül öner. Ödeme altyapısı gibi harici hizmet gerektiren "
                "modülleri önerirsen gerekçede bunu belirt."
            ),
            f"Özellik matrisi:\n{matrix_txt}\n\nRakip özetleri:\n{summaries}\n\n"
            f"Kullanıcı notları: {req.notes or '-'}",
            Strategy,
            effort="medium",
        )
        for m in strategy.recommended_modules:
            self.log(f"[{m.priority}] {m.title} — {m.reason}", "ok")
        return strategy
