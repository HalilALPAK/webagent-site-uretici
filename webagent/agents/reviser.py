"""Revizyon Ajanı: hazır sitede kullanıcının kendi cümleleriyle istediği değişiklikleri yapar.

Örnek istekler: "şubelerimize açılış saati ekle", "ana sayfada yorumları en üste al",
"rengi daha koyu yap", "SSS bölümünü kaldır", "kampanyalar diye yeni bir bölüm aç".

Çıktı yeni bir site tanımıdır; İnşa Ajanı bunu var olan projeye uygular. Veri silinmez:
kaldırılan alanlar yalnızca sitede görünmez olur, tablolar ve sütunlar veritabanında kalır.
"""
from __future__ import annotations

import json

from ..config import DESIGN_GUIDE
from ..schemas import Revision, Site
from .architect import sanitize_spec
from .base import Agent
from .designer import sanitize_theme


class ReviserAgent(Agent):
    name = "Revizyon Ajanı"
    role = "Yayındaki sitenin yapısını, içeriğini ve tasarımını kullanıcının isteğine göre güncellemek."

    def run(self, current: dict, instruction: str) -> tuple[Site, str]:
        guide = DESIGN_GUIDE.read_text(encoding="utf-8")
        entity_names = ", ".join(e["name"] for e in current["entities"])
        revision = self.llm.structured(
            self.system_prompt(
                "Sana yayındaki bir sitenin tam tanımı (site.json) ve kullanıcının değişiklik isteği verilir. "
                "Aynı tanımı, YALNIZCA istenen değişiklik uygulanmış hâlde döndür.\n"
                "Kurallar:\n"
                "1. İstenmeyen hiçbir alanı değiştirme; metinleri, alanları ve sıralamayı olduğu gibi koru.\n"
                f"2. Var olan entity adlarını ({entity_names}) ve alan (field) adlarını DEĞİŞTİRME; "
                "veritabanı bunlara bağlıdır. Yalnızca label/görünen metinler değiştirilebilir.\n"
                "3. Bir şeyin kaldırılması isteniyorsa listeden çıkar (veri korunur, sitede görünmez).\n"
                "4. Yeni alan eklersen mutlaka yeni bir name ver; yeni entity eklersen snake_case çoğul ad kullan.\n"
                "5. Tasarım değişikliklerinde aşağıdaki rehbere uy.\n\n"
                "<tasarim_rehberi>\n" + guide + "\n</tasarim_rehberi>"
            ),
            f"Yayındaki site tanımı:\n{json.dumps(current, ensure_ascii=False)[:120000]}\n\n"
            f"Kullanıcının isteği: {instruction}",
            Revision,
            effort="high",
            max_tokens=32000,
        )
        site = revision.site
        for fix in sanitize_spec(site):
            self.log(f"Düzeltme: {fix}", "warn")
        for fix in sanitize_theme(site.theme, site, self.job.request.style):
            self.log(f"Düzeltme: {fix}", "warn")
        # marka ve iletişim bilgileri kullanıcıya aittir; ajan değiştirmesin
        req = self.job.request
        site.contact_phone = req.contact_phone.strip() or site.contact_phone
        site.contact_email = req.contact_email.strip() or site.contact_email
        site.address = req.address.strip() or site.address
        self.log(revision.summary, "ok")
        return site, revision.summary
