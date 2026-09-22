"""Rapor Ajanı: üretimden önce kullanıcının okuyacağı plan raporunu hazırlar.

Rapor iki parçadan oluşur:
  - Ölçülebilir gerçekler (kaç bölüm, hangi sayfalar, kaç görsel, veri nerede tutulacak) — koddan çıkar.
  - Değerlendirme (neden bu yapı, sizden ne istenecek, nelere dikkat) — Rapor Ajanı yazar.
Kullanıcı raporu okur, onaylarsa görsel seçimine geçilir.
"""
from __future__ import annotations

import time

from ..schemas import LegacyInfo, PlanReport, Site, Strategy
from .base import Agent


def facts(site: Site, seed: dict[str, list[dict]], images: dict, db: dict, legacy: LegacyInfo | None) -> dict:
    """Rapordaki sayısal bilgiler (LLM'e de verilir, ekranda tablo olarak da gösterilir)."""
    public = [e for e in site.entities if e.public]
    slots = sum(len(g["slots"]) for g in images.get("groups", []))
    suggested = sum(1 for c in images.get("choices", {}).values() if c.get("type") == "stock")
    own = sum(1 for g in images.get("groups", []) for c in g.get("pool", []) if c.get("own"))
    return {
        "site_name": site.site_name,
        "sector": site.sector,
        "entities": [{"label": e.label_plural, "name": e.name, "fields": len(e.fields),
                      "public": e.public, "records": len(seed.get(e.name, []))} for e in site.entities],
        "public_count": len(public),
        "pages": [p.title for p in site.pages],
        "modules": [{"title": m.title, "priority": m.priority} for m in site.modules],
        "theme": {"preset": site.theme.preset, "mode": site.theme.mode, "hero": site.theme.hero_variant,
                  "fonts": f"{site.theme.font_heading} / {site.theme.font_body}",
                  "colors": [site.theme.primary, site.theme.accent]},
        "images": {"slots": slots, "suggested": suggested, "own_site": own},
        "records_total": sum(len(v) for v in seed.values()),
        "database": "Sunucudaki MySQL" if db.get("type") == "mysql" else "Bu bilgisayarda SQLite",
        "contact": {"phone": site.contact_phone, "email": site.contact_email, "address": site.address},
        "legacy_used": bool(legacy),
        "legacy_items": len(legacy.items) if legacy else 0,
        "legacy_missing": legacy.missing if legacy else [],
        "created_at": time.strftime("%d.%m.%Y %H:%M"),
    }


class ReportAgent(Agent):
    name = "Rapor Ajanı"
    role = "Üretimden önce ne yapılacağını, nelerin kullanıcıdan isteneceğini ve risklerini raporlamak."

    def run(self, site: Site, strategy: Strategy, data: dict, legacy: LegacyInfo | None) -> PlanReport:
        entities = "\n".join(f"- {e['label']} ({e['name']}): {e['fields']} alan, {e['records']} örnek kayıt, "
                             f"{'sitede görünür' if e['public'] else 'yalnızca yönetimde'}" for e in data["entities"])
        modules = ", ".join(f"{m['title']} [{m['priority']}]" for m in data["modules"])
        report = self.llm.structured(
            self.system_prompt(
                "Kullanıcı teknik biri değil; işletme sahibi. Rapor sade, dürüst ve eyleme dönük olsun.\n"
                "- 'included': sitede ne olacağını işletme diliyle anlat (teknik tablo adları değil).\n"
                "- 'needed_from_user': yayından önce işletmeden gereken GERÇEK bilgiler (kendi fotoğrafları, "
                "doğru fiyatlar, gerçek müşteri yorumları, vergi/KVKK bilgileri, sosyal medya adresleri).\n"
                "- 'risks': örnek içeriğin yayına çıkmasının sakıncası, stok görsellerin lisans/atıf zorunluluğu, "
                "harici entegrasyon gerektiren modüller (ödeme, harita, WhatsApp), varsa eksik veriler.\n"
                "Abartma, uydurma istatistik verme; yalnızca verilen bilgilere dayan."
            ),
            f"Site: {data['site_name']} — {site.tagline}\nSektör: {data['sector']}\n"
            f"Konumlandırma: {strategy.positioning}\nHedef kitle: {strategy.target_audience}\n"
            f"Seçilen modüller: {modules}\n\nBölümler:\n{entities}\n"
            f"Sayfalar: {', '.join(data['pages'])}\n"
            f"Tasarım: {data['theme']['preset']} / {data['theme']['mode']} tema, hero: {data['theme']['hero']}\n"
            f"Görseller: {data['images']['slots']} görsel yeri, {data['images']['suggested']} hazır öneri, "
            f"{data['images']['own_site']} tanesi mevcut sitenizden\n"
            f"Veri: {data['database']}\n"
            f"İletişim: {data['contact']['phone'] or '(yok)'} · {data['contact']['email'] or '(yok)'} · "
            f"{data['contact']['address'] or '(yok)'}\n"
            + (f"Mevcut siteden {data['legacy_items']} kayıt devralındı. "
               f"Eski sitede bulunamayanlar: {', '.join(data['legacy_missing']) or '-'}\n" if legacy else
               "Kullanıcının mevcut sitesi verilmedi; içerik örnek olarak üretildi.\n"),
            PlanReport,
            effort="medium",
        )
        self.log(f"Plan raporu hazır: {len(report.included)} başlık, "
                 f"{len(report.needed_from_user)} sizden istenen, {len(report.risks)} uyarı.", "ok")
        return report


def report_markdown(report: PlanReport, data: dict) -> str:
    """Raporun indirilebilir metin hâli."""
    def items(rows):
        return "\n".join(f"- **{r.title}** — {r.detail}" for r in rows) or "- (yok)"

    entities = "\n".join(f"| {e['label']} | {e['fields']} | {e['records']} | "
                         f"{'Evet' if e['public'] else 'Hayır'} |" for e in data["entities"])
    return f"""# {data['site_name']} — Site Planı
*{data['created_at']} · {data['sector']}*

## Özet
{report.summary}

## Sitede ne olacak
{items(report.included)}

## Yapı
| Bölüm | Alan | Örnek kayıt | Sitede görünür |
|---|---|---|---|
{entities}

- **Sayfalar:** {', '.join(data['pages'])}
- **Tasarım:** {data['theme']['preset']} ({data['theme']['mode']}), {data['theme']['fonts']}, renkler {', '.join(data['theme']['colors'])}
- **Görseller:** {data['images']['slots']} görsel yeri · {data['images']['suggested']} hazır öneri · {data['images']['own_site']} mevcut sitenizden
- **Veri:** {data['database']}
- **İletişim:** {data['contact']['phone'] or '—'} · {data['contact']['email'] or '—'} · {data['contact']['address'] or '—'}

## Mevcut sitenizden devralınanlar
{chr(10).join('- ' + x for x in report.from_old_site) or '- (mevcut site verilmedi)'}

## Sizden istenecekler
{items(report.needed_from_user)}

## Dikkat edilecekler
{items(report.risks)}

## Yayına kadar adımlar
{chr(10).join(f'{i}. {s}' for i, s in enumerate(report.next_steps, 1)) or '1. (yok)'}
"""
