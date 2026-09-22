"""Mimar Ajanı: modül önerilerini veri modeline, sayfalara ve markaya dönüştürür."""
from __future__ import annotations

import re
import unicodedata

from ..schemas import SiteAnalysis, SiteSpec, Strategy
from .base import Agent

# Site motorunun kendi kullandığı URL segmentleri / tablo adları
RESERVED = {"admin", "api", "static", "p", "contact", "search", "newsletter", "health",
            "messages", "subscribers", "users", "sqlite_master",
            # Laravel/Filament rotaları ve tabloları
            "up", "uploads", "css", "js", "fonts", "livewire", "filament", "login", "logout", "storage",
            "build", "vendor", "cache", "cache_locks", "jobs", "job_batches", "failed_jobs", "sessions",
            "migrations", "password_reset_tokens", "credits"}
# Ayrılmış ad çakışırsa anlamlı bir alternatif
RENAME = {"jobs": "careers", "users": "members", "messages": "inquiries", "sessions": "session_items",
          "events_cache": "event_items"}
SQL_RESERVED = {"id", "created_at", "order", "group", "select", "from", "where", "table", "index", "key"}


def slugify(text: str, sep: str = "_") -> str:
    text = unicodedata.normalize("NFKD", text.replace("ı", "i").replace("İ", "I"))
    text = text.encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9]+", sep, text).strip(sep)
    return text or "item"


def sanitize_spec(spec: SiteSpec) -> list[str]:
    """LLM çıktısını motorun güvenle çalıştırabileceği hale getirir; yapılan düzeltmeleri döndürür."""
    fixes: list[str] = []
    spec.slug = slugify(spec.slug or spec.site_name, "-")

    names: set[str] = set()
    renamed: dict[str, str] = {}  # eski slug -> yeni ad (ilişkileri güncellemek için)
    for ent in spec.entities:
        name = slugify(ent.name)
        if name in RESERVED or name in names:
            name = RENAME.get(name, f"{name}_items")
            if name in names:
                name = f"{name}_items"
        if name != ent.name:
            fixes.append(f"entity '{ent.name}' -> '{name}'")
        renamed.setdefault(slugify(ent.name), name)
        ent.name = name
        names.add(name)

        seen: set[str] = set()
        clean_fields = []
        for f in ent.fields:
            fname = slugify(f.name)
            if fname in SQL_RESERVED:
                fname = f"{fname}_value"
            if fname in seen:
                continue
            seen.add(fname)
            f.name = fname
            if f.type != "select":
                f.options = []
            clean_fields.append(f)
        ent.fields = clean_fields
        if not ent.fields:
            from ..schemas import FieldSpec
            ent.fields = [FieldSpec(name="title", label="Başlık", type="string", required=True,
                                    options=[], relation=None, show_in_list=True)]
        field_names = {f.name for f in ent.fields}
        if slugify(ent.title_field) not in field_names:
            ent.title_field = next((f.name for f in ent.fields if f.type == "string"), ent.fields[0].name)
        else:
            ent.title_field = slugify(ent.title_field)
        img = slugify(ent.image_field) if ent.image_field else None
        ent.image_field = img if img in {f.name for f in ent.fields if f.type == "image"} else None

    for ent in spec.entities:
        for f in ent.fields:
            if f.type == "relation":
                target = slugify(f.relation or "")
                target = target if target in names else renamed.get(target, target)
                if target not in names:
                    fixes.append(f"{ent.name}.{f.name}: geçersiz ilişki '{f.relation}', string yapıldı")
                    f.type, f.relation = "string", None
                else:
                    f.relation = target
            elif f.type == "select" and not f.options:
                f.type = "string"
            else:
                f.relation = None

    slugs: set[str] = set()
    for page in spec.pages:
        s = slugify(page.slug, "-")
        while s in slugs:
            s += "-2"
        page.slug = s
        slugs.add(s)

    if not re.fullmatch(r"/[A-Za-z0-9/_#?=&.-]*", spec.hero.cta_link or ""):
        spec.hero.cta_link = f"/{spec.entities[0].name}" if spec.entities else "/contact"
        fixes.append("hero CTA linki site içi yola çevrildi")

    for attr in ("primary_color", "accent_color"):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", getattr(spec.branding, attr)):
            setattr(spec.branding, attr, "#0f766e" if attr == "primary_color" else "#f59e0b")
            fixes.append(f"geçersiz renk düzeltildi: {attr}")
    spec.branding.font_family = re.sub(r"[^A-Za-z0-9 ]", "", spec.branding.font_family) or "Inter"
    return fixes


class ArchitectAgent(Agent):
    name = "Mimar Ajanı"
    role = "Seçilen modülleri veritabanı varlıkları, alanlar, sayfalar ve marka kimliğine dönüştürmek."

    def run(self, strategy: Strategy, analyses: list[SiteAnalysis], legacy: str = "") -> SiteSpec:
        req = self.job.request
        modules = "\n".join(f"- {m.key} [{m.priority}]: {m.title} — {m.reason}" for m in strategy.recommended_modules)
        content_types = sorted({c for a in analyses for c in a.content_types})
        spec = self.llm.structured(
            self.system_prompt(
                "Çıktın, genel bir site motoru tarafından doğrudan çalıştırılacak. Motorun yetenekleri:\n"
                "- Her 'entity' için SQLite tablosu, admin panelinde CRUD, REST API (/api/<entity>) ve "
                "public=true ise /<entity> liste + /<entity>/<id> detay sayfası oluşturulur.\n"
                "- Alan tipleri: string, text, richtext, int, float, price, bool, date, email, url, phone, "
                "image (görsel URL'si), select (options ile), relation (başka entity'ye bağlantı).\n"
                "- İletişim formu (/contact) mesajları admin panelinde gelen kutusuna düşer; bülten aboneleri saklanır.\n"
                "- Statik sayfalar /p/<slug> altında markdown olarak sunulur.\n"
                "Modülleri bu yeteneklerle eşle: ör. booking_appointment -> 'appointments' entity'si (public=false, "
                "form ile değil admin'den yönetilir) ve randevu talebi için iletişim formu; faq -> 'faqs' entity; "
                "testimonials -> 'testimonials' entity; blog -> 'posts' entity (richtext içerik, image kapak). "
                "Entity adları İngilizce snake_case çoğul olsun (URL'de görünür); label'lar hedef dilde olsun. "
                "Her entity'de bir başlık alanı olsun, 4-10 alan yeterli. 'id' ve 'created_at' alanlarını ekleme, motor ekler. "
                "En az 'hakkimizda' benzeri bir kurumsal sayfa ve KVKK/gizlilik sayfası ekle. "
                "İletişim bilgileri (telefon, e-posta, adres) kullanıcı verdiyse ya da mevcut sitesinden "
                "geldiyse AYNEN kullan; yoksa açıkça örnek olduğu belli olan yer tutucu yaz. "
                "İşletmenin mevcut sitesinden bilgi verildiyse hizmet/ürün adlarını ve kurumsal metni oradan al."
            ),
            f"Marka adı: {req.brand_name or '(sen öner, rakiplerden farklı ve özgün olsun)'}\n"
            f"Konumlandırma: {strategy.positioning}\nHedef kitle: {strategy.target_audience}\n"
            f"Seçilen modüller:\n{modules}\n\nRakiplerde görülen içerik türleri: {', '.join(content_types)}\n"
            f"Kullanıcı notları: {req.notes or '-'}\n"
            f"İletişim bilgileri — telefon: {req.contact_phone or '(verilmedi)'}, "
            f"e-posta: {req.contact_email or '(verilmedi)'}, adres: {req.address or '(verilmedi)'}"
            + legacy,
            SiteSpec,
            effort="high",
        )
        spec.modules = strategy.recommended_modules
        spec.language = req.language
        spec.sector = req.sector
        if req.brand_name:
            spec.site_name = req.brand_name
        # kullanıcının girdiği iletişim bilgileri her zaman geçerlidir
        spec.contact_phone = req.contact_phone.strip() or spec.contact_phone
        spec.contact_email = req.contact_email.strip() or spec.contact_email
        spec.address = req.address.strip() or spec.address
        for fix in sanitize_spec(spec):
            self.log(f"Düzeltme: {fix}", "warn")
        self.log(
            f"'{spec.site_name}' tasarlandı: {len(spec.entities)} varlık "
            f"({', '.join(e.name for e in spec.entities)}), {len(spec.pages)} sayfa.", "ok"
        )
        return spec
