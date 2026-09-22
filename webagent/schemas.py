"""Ajanlar arasında dolaşan yapılandırılmış veri modelleri.

LLM'den dönen modeller (Claude structured outputs ile doğrulanır) varsayılan
değer içermez; tüm alanlar zorunludur ki şema katı kalsın.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- Keşif ajanı

class Competitor(BaseModel):
    name: str
    url: str = Field(description="Sitenin ana sayfa URL'si (https://...)")
    why: str = Field(description="Neden bu sektörde güçlü bir rakip olduğu, tek cümle")


class CompetitorList(BaseModel):
    competitors: list[Competitor]


# ---------------------------------------------------------------- Miras ajanı (kullanıcının eski sitesi)

class LegacyItem(BaseModel):
    name: str = Field(description="Eski sitedeki hizmet/ürün/oda vb. adı, aynen")
    description: str = Field(description="Eski sitedeki açıklaması (kısaltılabilir, uydurma ekleme)")
    price: str = Field(description="Varsa fiyat, yoksa boş")
    category: str = Field(description="Varsa kategori, yoksa boş")


class LegacyInfo(BaseModel):
    """Kullanıcının mevcut sitesinden alınan gerçek bilgiler. Uydurma bilgi EKLENMEZ."""
    business_name: str
    about: str = Field(description="Hakkımızda/kurumsal metin (eski siteden, kısaltılmış)")
    phone: str
    email: str
    address: str
    working_hours: str = Field(description="Çalışma saatleri, yazmıyorsa boş")
    social_links: list[str]
    items: list[LegacyItem] = Field(description="Eski sitedeki hizmet/ürün/oda/şube gibi kayıtlar")
    highlights: list[str] = Field(description="İşletmenin öne çıkardığı gerçek özellikler")
    missing: list[str] = Field(description="Eski sitede bulunamayan ama yeni sitede gereken bilgiler")


# ---------------------------------------------------------------- Analist ajanı

MODULE_KEYS = [
    "product_catalog", "shopping_cart", "checkout_payment", "services", "pricing_plans",
    "booking_appointment", "blog_news", "portfolio_projects", "team", "testimonials_reviews",
    "faq", "gallery", "contact_form", "newsletter", "search", "user_accounts",
    "locations_map", "events", "jobs_careers", "live_chat", "multi_language",
    "campaigns_discounts", "comparison", "downloads_documents", "video_content",
    "partners_references", "quote_request", "support_tickets", "social_proof_stats",
]


class DetectedModule(BaseModel):
    key: str = Field(description="Kanonik modül anahtarı (listeden) ya da snake_case özel anahtar")
    title: str = Field(description="Modülün insan okunur adı (hedef dilde)")
    evidence: str = Field(description="Sitede bu modülü gösteren kanıt (menü, form, URL, metin)")


class SiteAnalysis(BaseModel):
    url: str
    name: str
    summary: str = Field(description="Sitenin ne yaptığı, hedef kitlesi, 2-3 cümle")
    modules: list[DetectedModule]
    content_types: list[str] = Field(description="Sitede yönetilen içerik türleri (ör. ürün, hizmet, doktor, blog yazısı)")
    strengths: list[str]
    weaknesses: list[str]


# ---------------------------------------------------------------- Strateji ajanı

class KeyMapping(BaseModel):
    key: str = Field(description="Analizlerde geçen orijinal modül anahtarı")
    canonical: str = Field(description="Eş anlamlı anahtarların birleştiği ortak snake_case anahtar")
    title: str = Field(description="Ortak anahtarın hedef dildeki adı")


class ModuleNormalization(BaseModel):
    mappings: list[KeyMapping]



class ModuleRecommendation(BaseModel):
    key: str
    title: str
    priority: Literal["must", "should", "differentiator"]
    reason: str


class Strategy(BaseModel):
    positioning: str = Field(description="Yeni sitenin rakiplerden nasıl ayrışacağı, 2-3 cümle")
    target_audience: str
    recommended_modules: list[ModuleRecommendation]


# ---------------------------------------------------------------- Mimar ajanı

FieldType = Literal[
    "string", "text", "richtext", "int", "float", "price", "bool", "date",
    "email", "url", "phone", "image", "select", "relation",
]


class FieldSpec(BaseModel):
    name: str = Field(description="snake_case, ASCII, SQL sütun adı olarak geçerli")
    label: str
    type: FieldType
    required: bool
    options: list[str] = Field(description="Sadece type=select için seçenekler; aksi halde boş liste")
    relation: str | None = Field(description="Sadece type=relation için hedef entity adı; aksi halde null")
    show_in_list: bool = Field(description="Admin ve genel listede sütun olarak gösterilsin mi")


class EntitySpec(BaseModel):
    name: str = Field(description="snake_case, ASCII, çoğul tablo adı ve URL segmenti (ör. products, services)")
    label: str = Field(description="Tekil insan okunur ad")
    label_plural: str
    module_key: str = Field(description="Bu varlığın karşıladığı modül anahtarı")
    public: bool = Field(description="Ziyaretçilere liste/detay sayfası olarak gösterilsin mi")
    show_on_home: bool = Field(description="Ana sayfada öne çıkan bölüm olarak gösterilsin mi")
    title_field: str = Field(description="Kaydı temsil eden alan adı (ör. name, title)")
    image_field: str | None = Field(description="Kart görseli olarak kullanılacak image alanı, yoksa null")
    fields: list[FieldSpec]


class PageSpec(BaseModel):
    slug: str = Field(description="URL için kısa, ASCII, kebab-case (ör. hakkimizda)")
    title: str
    in_nav: bool
    body_markdown: str = Field(description="Sayfa içeriği; basit markdown (#, ##, -, paragraflar)")


class Branding(BaseModel):
    primary_color: str = Field(description="Hex renk, ör. #0f766e")
    accent_color: str = Field(description="Hex renk")
    font_family: str = Field(description="Google Fonts ailesi adı, ör. Inter")
    tone: str


class HeroSpec(BaseModel):
    headline: str
    subheadline: str
    cta_text: str
    cta_link: str = Field(description="Site içi yol, ör. /services veya /iletisim")


class SiteSpec(BaseModel):
    site_name: str
    slug: str = Field(description="Klasör adı için kebab-case ASCII")
    tagline: str
    language: str
    sector: str
    meta_description: str
    branding: Branding
    hero: HeroSpec
    modules: list[ModuleRecommendation]
    entities: list[EntitySpec]
    pages: list[PageSpec]
    contact_form: bool
    newsletter: bool
    search: bool
    contact_email: str
    contact_phone: str
    address: str


# ---------------------------------------------------------------- Tasarım ajanı (DESIGN.md)

Display = Literal["cards", "feature", "list", "gallery", "testimonials", "faq", "team", "stats"]


class HomeSection(BaseModel):
    entity: str = Field(description="Public bir entity adı")
    display: Display
    eyebrow: str = Field(description="Bölüm üstü kısa etiket, 1-3 kelime")
    title: str = Field(description="Fayda anlatan bölüm başlığı")
    subtitle: str = Field(description="En fazla 1 cümle")


class EntityDisplay(BaseModel):
    entity: str
    display: Display = Field(description="Liste sayfasında kullanılacak düzen")


class NavLabel(BaseModel):
    entity: str
    label: str = Field(description="Menüde görünecek 1-2 kelimelik kısa etiket, ör. 'Odalar'")


class ThemeSpec(BaseModel):
    preset: Literal["luxury", "wellness", "corporate", "bold", "tech", "warm", "fresh", "nature"]
    mode: Literal["light", "dark"] = Field(description="Sitenin genel zemini: aydınlık ya da koyu")
    primary: str = Field(description="Hex, beyaz metinle AA kontrast")
    accent: str = Field(description="Hex, CTA/fiyat vurgusu")
    surface: str = Field(description="Hex, kırık beyaz zemin")
    ink: str = Field(description="Hex, gövde metni")
    font_heading: str = Field(description="Google Fonts ailesi, Türkçe destekli")
    font_body: str = Field(description="Google Fonts sans-serif ailesi, Türkçe destekli")
    radius: Literal["none", "soft", "round", "pill"]
    hero_variant: Literal["image", "split", "centered"]
    hero_eyebrow: str
    hero_image_keywords: str = Field(description="Hero görseli için 2-3 İngilizce anahtar kelime, virgülle")
    trust_items: list[str] = Field(description="3-4 kısa güven öğesi")
    nav_entities: list[str] = Field(description="Menüde gösterilecek en fazla 4 public entity adı")
    nav_labels: list[NavLabel] = Field(description="nav_entities'teki her varlık için kısa menü etiketi")
    primary_cta_text: str = Field(description="En fazla 3 kelime, fiille başlar")
    primary_cta_link: str = Field(description="Site içi yol, ör. /contact veya /rooms")
    home_sections: list[HomeSection] = Field(description="En fazla 5 bölüm, art arda aynı display yok")
    entity_displays: list[EntityDisplay] = Field(description="Her public entity için liste sayfası düzeni")
    cta_band_title: str
    cta_band_text: str


class Revision(BaseModel):
    """Revizyon Ajanı'nın çıktısı: güncellenmiş site tanımı + kullanıcıya gösterilecek özet."""
    summary: str = Field(description="Yapılan değişikliklerin kısa özeti (kullanıcıya gösterilir)")
    site: "Site"


class Site(SiteSpec):
    """Mimar + Tasarım ajanlarının birleşik çıktısı (İnşa ajanına giden)."""
    theme: ThemeSpec


# ---------------------------------------------------------------- İçerik ajanı

class FieldValue(BaseModel):
    field: str
    value: str = Field(description="Metin olarak değer. bool için true/false, tarih için YYYY-AA-GG, relation için hedef kaydın sıra numarası (1'den başlar)")


class SeedRecord(BaseModel):
    values: list[FieldValue]


class EntitySeed(BaseModel):
    entity: str
    records: list[SeedRecord]


# ---------------------------------------------------------------- Rapor ajanı

class ReportItem(BaseModel):
    title: str = Field(description="Kısa başlık")
    detail: str = Field(description="1-2 cümle açıklama")


class PlanReport(BaseModel):
    """Üretimden önce kullanıcının okuyacağı plan raporu."""
    summary: str = Field(description="3-5 cümle: ne kurulacak, neden bu yapı seçildi")
    included: list[ReportItem] = Field(description="Sitede yer alacak bölümler/özellikler ve ne işe yaradıkları")
    from_old_site: list[str] = Field(description="Mevcut siteden devralınanlar; eski site yoksa boş liste")
    needed_from_user: list[ReportItem] = Field(description="Yayından önce işletmeden istenecek gerçek bilgi/görseller")
    risks: list[ReportItem] = Field(description="Dikkat edilmesi gerekenler (örnek içerik, lisans, entegrasyon gerektirenler)")
    next_steps: list[str] = Field(description="Yayına kadar sırayla yapılacaklar")


# ---------------------------------------------------------------- QA ajanı

class QAResult(BaseModel):
    passed: bool
    checks: list[str] = []
    errors: list[str] = []
