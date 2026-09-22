"""Ham (LLM/form) değerleri alan tipine çeviren dönüştürücü.

site_engine/db.py'de de aynısı vardır: o dosya üretilen Python sitelerine tek başına kopyalandığı için
paket dışından içe aktarılamaz. Burada değişiklik yaparsanız orayı da güncelleyin.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any


def coerce(field: dict, raw: Any) -> Any:
    """Formdan/JSON'dan gelen değeri alan tipine çevirir."""
    t = field["type"]
    if t == "bool":
        if isinstance(raw, bool):
            return int(raw)
        return 1 if str(raw).strip().lower() in ("1", "true", "on", "yes", "evet") else 0
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        if field.get("required"):
            raise ValueError("Bu alan zorunludur")
        return None
    s = str(raw).strip()
    if t in ("int", "relation"):
        return int(float(s))
    if t in ("float", "price"):
        num = re.sub(r"[^\d,.-]", "", s)
        if "," in num and "." in num:  # 1.234,56
            num = num.replace(".", "").replace(",", ".")
        elif "," in num:
            num = num.replace(",", ".")
        elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", num):  # 18.500 (TR binlik ayraç)
            num = num.replace(".", "")
        return float(num)
    if t == "date":
        return date.fromisoformat(s[:10]).isoformat()
    if t == "email" and "@" not in s:
        raise ValueError("Geçerli bir e-posta girin")
    if t in ("url", "image") and not s.startswith(("http://", "https://", "/")):
        raise ValueError("http(s):// ile başlayan bir adres girin")
    if t == "select" and field.get("options") and s not in field["options"]:
        raise ValueError("Geçersiz seçenek")
    return s
