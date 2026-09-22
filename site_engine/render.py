"""Şablon yardımcıları: güvenli mini-markdown ve alan biçimlendirme."""
from __future__ import annotations

import html
import re

from markupsafe import Markup


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<em>\1</em>", text)
    # yalnızca http(s) ve site içi linklere izin ver
    text = re.sub(
        r"\[([^\]]+)\]\(((?:https?://|/)[^)\s]*)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text,
    )
    return text


def markdown(src: str | None) -> Markup:
    """#, ##, ###, - listeler, **kalın**, *italik*, [link](url) ve paragraflar."""
    if not src:
        return Markup("")
    out, para, items = [], [], []

    def flush():
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in src.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if not s:
            flush()
        elif m := re.match(r"^(#{1,3})\s+(.*)", s):
            flush()
            level = len(m.group(1)) + 1  # sayfada h1 başlık zaten var
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
        elif m := re.match(r"^[-*]\s+(.*)", s):
            if para:
                out.append(f"<p>{_inline(' '.join(para))}</p>")
                para.clear()
            items.append(m.group(1))
        else:
            if items:
                flush()
            para.append(s)
    flush()
    return Markup("\n".join(out))


def excerpt(text: str | None, n: int = 140) -> str:
    if not text:
        return ""
    plain = re.sub(r"[#*\[\]()_`>-]", "", str(text))
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain if len(plain) <= n else plain[: n].rsplit(" ", 1)[0] + "…"


def fmt(value, field: dict, currency: str = "₺", relations: dict | None = None) -> str:
    """Alan değerini liste/detay görünümü için metne çevirir."""
    if value is None or value == "":
        return "—"
    t = field["type"]
    if t == "bool":
        return "Evet" if value else "Hayır"
    if t == "price":
        s = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} {currency}"
    if t == "relation":
        return (relations or {}).get(field["name"], {}).get(value, f"#{value}")
    if t in ("text", "richtext"):
        return excerpt(value, 90)
    return str(value)
