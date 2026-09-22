"""İçerik Ajanı: her varlık için özgün örnek (seed) kayıtlar üretir."""
from __future__ import annotations

from ..schemas import EntitySeed, EntitySpec, SiteSpec
from .base import Agent


class ContentAgent(Agent):
    name = "İçerik Ajanı"
    role = "Sitenin veritabanını dolduracak gerçekçi, özgün örnek içerik yazmak."

    def run(self, spec: SiteSpec, entity: EntitySpec, count: int = 6, legacy: str = "") -> list[dict]:
        fields_txt = "\n".join(
            f"- {f.name} ({f.type}{', seçenekler: ' + '/'.join(f.options) if f.options else ''}"
            f"{', ilişki: ' + f.relation if f.relation else ''}){' zorunlu' if f.required else ''}: {f.label}"
            for f in entity.fields
        )
        seed = self.llm.structured(
            self.system_prompt(
                "image tipindeki alanlara o kayda uygun görseli tarif eden 2-3 İngilizce anahtar kelime yaz "
                "(virgülle, ör. 'boutique hotel room, bed'); sistem bunlarla görsel bulacak. richtext alanlarında "
                "paragrafları boş satırla ayır, 2-4 paragraf yaz. Fiyatları hedef pazarın para biriminde "
                "sayı olarak ver. relation alanlarına hedef varlığın 1..N arası sıra numarasını yaz.\n"
                "İşletmenin mevcut sitesinden kayıtlar verildiyse ÖNCE onları kullan (adları ve fiyatları "
                "aynen koru, açıklamayı gerekiyorsa düzelt); sayı yetmezse gerçekçi yenilerini ekle."
            ),
            f"Site: {spec.site_name} — {spec.tagline}\nKonumlandırma: {spec.meta_description}\n"
            f"Varlık: {entity.label_plural} ({entity.name})\nAlanlar:\n{fields_txt}\n\n"
            f"Bu varlık için {count} adet kayıt üret." + legacy,
            EntitySeed,
            effort="low",
        )
        # image alanlarında şimdilik anahtar kelimeler durur; İnşa ajanı bunlardan görsel indirir.
        records = [{fv.field: fv.value for fv in rec.values} for rec in seed.records]
        self.log(f"{entity.label_plural}: {len(records)} örnek kayıt yazıldı.", "ok")
        return records
