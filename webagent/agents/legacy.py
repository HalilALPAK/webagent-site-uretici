"""Miras Ajanı: kullanıcının mevcut sitesinden gerçek bilgileri ve görselleri devralır.

Yeni site uydurma içerikle değil, işletmenin kendi metinleri, hizmet listesi, iletişim bilgileri ve
fotoğraflarıyla kurulsun diye eski site taranır. Bulunamayan bilgiler `missing` listesine yazılır ve
plan raporunda "sizden istenecekler" olarak görünür.
"""
from __future__ import annotations

from ..schemas import LegacyInfo
from .base import Agent
from .crawler import CrawlerAgent
from .scout import normalize_url


class LegacyAgent(Agent):
    name = "Miras Ajanı"
    role = "Kullanıcının mevcut sitesinden gerçek bilgileri ve görselleri çıkarmak."

    def run(self, url: str) -> tuple[LegacyInfo | None, list[dict]]:
        """(bilgiler, görseller) döndürür. Site açılamazsa (None, [])."""
        url = normalize_url(url)
        self.log(f"Mevcut siteniz taranıyor: {url}")
        crawl = CrawlerAgent(self.job, None).run(url)
        if not crawl.ok:
            self.log(f"Mevcut site taranamadı ({crawl.error}); içerik sıfırdan yazılacak.", "warn")
            return None, []

        images = [img for page in crawl.pages for img in page.images]
        seen, unique = set(), []
        for img in images:
            if img["url"] not in seen:
                seen.add(img["url"])
                unique.append(img)

        info = self.llm.structured(
            self.system_prompt(
                "Bu, kullanıcının KENDİ mevcut sitesidir (rakip değil). Amacın oradaki gerçek bilgileri "
                "aynen çıkarmak: işletme adı, hakkımızda metni, telefon, e-posta, adres, çalışma saatleri, "
                "sosyal medya adresleri, hizmet/ürün listesi ve öne çıkan özellikler.\n"
                "Sitede olmayan hiçbir bilgiyi UYDURMA; bulamadığın alanı boş bırak ve 'missing' listesine "
                "yeni sitede gerekecek eksik bilgileri yaz (ör. fiyatlar, çalışma saatleri, ekip bilgisi)."
            ),
            f"Mevcut site taraması:\n{crawl.digest(12000)}",
            LegacyInfo,
            effort="medium",
        )
        self.log(
            f"Eski siteden alındı: {len(info.items)} kayıt, {len(unique)} görsel"
            + (f", iletişim: {info.phone or '-'} / {info.email or '-'}" if (info.phone or info.email) else ""),
            "ok",
        )
        if info.missing:
            self.log("Eski sitede bulunamayanlar: " + ", ".join(info.missing[:6]), "warn")
        return info, unique

    @staticmethod
    def as_prompt(info: LegacyInfo | None) -> str:
        """Mimar ve İçerik ajanlarının kullanacağı özet."""
        if not info:
            return ""
        items = "\n".join(f"  - {i.name}" + (f" ({i.category})" if i.category else "")
                          + (f" — {i.price}" if i.price else "") + (f": {i.description[:160]}" if i.description else "")
                          for i in info.items[:40])
        return (
            "\n\nİŞLETMENİN MEVCUT SİTESİNDEN ALINAN GERÇEK BİLGİLER (uydurma yerine bunları kullan):\n"
            f"Ad: {info.business_name}\nHakkında: {info.about[:1200]}\n"
            f"İletişim: {info.phone} · {info.email} · {info.address}\n"
            f"Çalışma saatleri: {info.working_hours or '(bilinmiyor)'}\n"
            f"Öne çıkanlar: {', '.join(info.highlights[:10])}\n"
            f"Mevcut kayıtlar:\n{items}\n"
        )
