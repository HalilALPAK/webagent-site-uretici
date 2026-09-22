"""Tasarım Ajanı: DESIGN.md rehberine göre sitenin görsel kimliğini ve sayfa kurgusunu seçer."""
from __future__ import annotations

import re

from ..config import DESIGN_GUIDE
from ..schemas import EntityDisplay, NavLabel, Site, SiteSpec, Strategy, ThemeSpec
from .base import Agent

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
PRESET_COLORS = {  # DESIGN.md §4 — geçersiz renk gelirse geri dönülecek değerler
    "luxury": ("#1f2a2e", "#b08d57", "#faf7f2"), "wellness": ("#134e4a", "#f59e0b", "#f7faf9"),
    "corporate": ("#0f2742", "#c2410c", "#f8fafc"), "bold": ("#111111", "#ef4444", "#ffffff"),
    "tech": ("#0b1020", "#6366f1", "#ffffff"), "warm": ("#3f2a1e", "#d97706", "#fbf6ef"),
    "fresh": ("#1e1b4b", "#ec4899", "#ffffff"), "nature": ("#1c3d2e", "#ca8a04", "#f6f7f2"),
}
# Koyu modda geri dönülecek değerler: (primary = koyu zeminde okunan açık marka tonu, accent, surface, ink)
DARK_PRESETS = {
    "luxury": ("#d8bd8a", "#b08d57", "#14181a", "#e9e6e1"), "wellness": ("#5eead4", "#f59e0b", "#0d1516", "#e6efee"),
    "corporate": ("#93c5fd", "#fb923c", "#0d1420", "#e5e9f0"), "bold": ("#fca5a5", "#ef4444", "#0d0d0d", "#ededed"),
    "tech": ("#a5b4fc", "#6366f1", "#0b1020", "#e6e8f2"), "warm": ("#fcd9a8", "#d97706", "#171210", "#efe7e0"),
    "fresh": ("#f9a8d4", "#ec4899", "#120f1f", "#ecebf2"), "nature": ("#a3d9a5", "#ca8a04", "#101a14", "#e6eee8"),
}
# Kullanıcının seçtiği görünüm → zorunlu mod
STYLE_MODE = {"light": "light", "colorful": "light", "minimal": "light", "dark": "dark"}
STYLE_HINTS = {
    "light": "Aydınlık ve sade bir site: kırık beyaz zemin, koyu metin, renk yalnızca CTA ve küçük vurgularda.",
    "dark": "KOYU TEMA: surface koyu (ör. #0f1115), ink açık (ör. #e7e9ee), primary koyu zeminde okunan AÇIK bir "
            "marka tonu (ör. #93c5fd), accent canlı. mode alanı 'dark' olmalı.",
    "colorful": "Canlı ve renkli: doygun accent, primary de renkli olsun (gri/lacivert değil); rozetler ve CTA belirgin.",
    "minimal": "Çok sade: neredeyse renksiz, primary koyu nötr, tek sakin accent, bol boşluk, radius none ya da soft.",
}

DEFAULT_DISPLAY = {
    "faq": "faq", "testimonials_reviews": "testimonials", "team": "team", "gallery": "gallery",
    "blog_news": "list", "events": "list", "portfolio_projects": "gallery", "social_proof_stats": "stats",
}


def _luminance(hex_color: str) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def sanitize_theme(theme: ThemeSpec, spec: SiteSpec, style: str = "auto") -> list[str]:
    """Rehberin ölçülebilir kurallarını kodla uygular; yapılan düzeltmeleri döndürür."""
    fixes: list[str] = []
    if style in STYLE_MODE and theme.mode != STYLE_MODE[style]:
        theme.mode = STYLE_MODE[style]
        fixes.append(f"görünüm seçimine uyduruldu: {theme.mode}")
    dark = theme.mode == "dark"
    if dark:
        p_primary, p_accent, p_surface, p_ink = DARK_PRESETS[theme.preset]
    else:
        p_primary, p_accent, p_surface = PRESET_COLORS[theme.preset]
        p_ink = "#1c1917"
    for attr, fallback in (("primary", p_primary), ("accent", p_accent), ("surface", p_surface), ("ink", p_ink)):
        if not HEX.match(getattr(theme, attr)):
            setattr(theme, attr, fallback)
            fixes.append(f"geçersiz renk: {attr}")
    if dark:
        # koyu modda zemin gerçekten koyu, primary de zemin üzerinde okunur olmalı
        if _luminance(theme.surface) > 0.25:
            theme.surface = p_surface
            fixes.append("koyu tema için zemin koyulaştırıldı")
        if contrast(theme.primary, theme.surface) < 4.5:
            theme.primary = p_primary
            fixes.append("primary koyu zeminde okunmuyordu → preset rengi")
    else:
        if _luminance(theme.surface) < 0.6:
            theme.surface = p_surface
            fixes.append("aydınlık tema için zemin açıldı")
        if contrast(theme.primary, "#ffffff") < 4.5:
            theme.primary = p_primary
            fixes.append("primary beyaz metinle yetersiz kontrast → preset rengi")
    if contrast(theme.ink, theme.surface) < 7:
        theme.ink = p_ink
        fixes.append("ink/surface kontrastı düzeltildi")
    if style == "minimal" and theme.radius in ("round", "pill"):
        theme.radius = "soft"
        fixes.append("sade görünüm için köşeler yumuşatıldı")
    for attr in ("font_heading", "font_body"):
        setattr(theme, attr, re.sub(r"[^A-Za-z0-9 ]", "", getattr(theme, attr)).strip() or "Inter")
    if theme.font_heading == theme.font_body and theme.preset != "tech":
        theme.font_body = "Inter"
        fixes.append("başlık ve gövde fontu ayrıldı")

    public = [e.name for e in spec.entities if e.public]
    theme.nav_entities = [n for n in dict.fromkeys(theme.nav_entities) if n in public][:4] or public[:4]
    labels = {n.entity: n.label.strip() for n in theme.nav_labels if n.label.strip()}
    for ent in spec.entities:  # etiket yoksa ya da uzunsa varlık adının ilk kelimesi
        if ent.name in theme.nav_entities and len(labels.get(ent.name, "x" * 99)) > 18:
            labels[ent.name] = ent.label_plural if len(ent.label_plural) <= 18 else ent.label_plural.split()[0]
    theme.nav_labels = [NavLabel(entity=k, label=v) for k, v in labels.items() if k in theme.nav_entities]

    sections, last = [], None
    for s in theme.home_sections:
        if s.entity not in public or any(x.entity == s.entity for x in sections):
            continue
        if s.display == last:  # art arda aynı düzen olmasın
            s.display = "feature" if s.display != "feature" else "cards"
            fixes.append(f"{s.entity}: tekrarlayan düzen değiştirildi")
        sections.append(s)
        last = s.display
        if len(sections) == 5:
            break
    theme.home_sections = sections

    shown = {d.entity: d for d in theme.entity_displays if d.entity in public}
    for ent in spec.entities:
        if ent.public and ent.name not in shown:
            shown[ent.name] = EntityDisplay(entity=ent.name, display=DEFAULT_DISPLAY.get(ent.module_key, "cards"))
    theme.entity_displays = list(shown.values())

    for attr in ("primary_cta_link",):
        if not re.fullmatch(r"/[A-Za-z0-9/_#?=&.-]*", getattr(theme, attr) or ""):
            setattr(theme, attr, "/contact")
    if len(theme.primary_cta_text.split()) > 3:
        theme.primary_cta_text = " ".join(theme.primary_cta_text.split()[:3])
        fixes.append("CTA metni kısaltıldı")
    theme.trust_items = [t for t in theme.trust_items if t.strip()][:4]
    return fixes


class DesignerAgent(Agent):
    name = "Tasarım Ajanı"
    role = "DESIGN.md rehberine göre sitenin tema, tipografi, menü ve ana sayfa kurgusunu belirlemek."

    def run(self, spec: SiteSpec, strategy: Strategy) -> Site:
        guide = DESIGN_GUIDE.read_text(encoding="utf-8")
        entities = "\n".join(
            f"- {e.name} ({e.label_plural}) modül={e.module_key} public={e.public} görsel={'var' if e.image_field else 'yok'}"
            for e in spec.entities
        )
        style = self.job.request.style
        theme = self.llm.structured(
            self.system_prompt(
                "Aşağıdaki tasarım rehberine harfiyen uy; özellikle §1'deki hataları tekrarlama ve §11 kontrol "
                "listesini uygula.\n\n<tasarim_rehberi>\n" + guide + "\n</tasarim_rehberi>"
            ),
            f"Site: {spec.site_name} — {spec.tagline}\nSektör: {spec.sector}\n"
            f"Konumlandırma: {strategy.positioning}\nHedef kitle: {strategy.target_audience}\n"
            f"Mimarın önerdiği marka tonu: {spec.branding.tone}\n\nVarlıklar:\n{entities}\n\n"
            "Bu site için theme çıktısını üret.",
            ThemeSpec,
            effort="medium",
        )
        for fix in sanitize_theme(theme, spec, style):
            self.log(f"Düzeltme: {fix}", "warn")
        # eski motorla uyumluluk için branding'i de temaya eşitle
        spec.branding.primary_color, spec.branding.accent_color = theme.primary, theme.accent
        spec.branding.font_family = theme.font_body
        spec.hero.cta_text, spec.hero.cta_link = theme.primary_cta_text, theme.primary_cta_link
        self.log(
            f"Tema: {theme.preset} ({theme.mode}) · {theme.font_heading}/{theme.font_body} · hero={theme.hero_variant} · "
            f"menü={', '.join(theme.nav_entities)} · ana sayfa={' → '.join(f'{s.entity}:{s.display}' for s in theme.home_sections)}",
            "ok",
        )
        return Site(**spec.model_dump(), theme=theme)
