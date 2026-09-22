"""İnşa Ajanı: site motorunu kopyalar, spec + seed verisini yazar, admin kimliğini üretir."""
from __future__ import annotations

import json
import re
import secrets
import shutil
from pathlib import Path

from ..config import ENGINE_DIR, OUTPUT_DIR
from ..schemas import SiteSpec
from .base import Agent


class BuilderAgent(Agent):
    name = "İnşa Ajanı"
    role = "Tasarımı çalışır bir web uygulamasına (frontend + backend + admin + veritabanı) dönüştürmek."

    def run(self, spec: SiteSpec, seed: dict[str, list[dict]]) -> Path:
        target = OUTPUT_DIR / f"{spec.slug}-{self.job.id}"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(
            ENGINE_DIR, target,
            ignore=shutil.ignore_patterns("__pycache__", "*.db", ".env", "site.json", "seed.json", "example_site.json", "example_seed.json"),
        )

        (target / "site.json").write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        seed = {name: [dict(r) for r in rows] for name, rows in seed.items()}
        for ent in spec.entities:
            for f in (f for f in ent.fields if f.type == "image"):
                for i, rec in enumerate(seed.get(ent.name, []), start=1):
                    words = re.findall(r"[a-z]+", str(rec.get(f.name) or ent.name).lower().split(",")[0])[:3]
                    rec[f.name] = f"https://loremflickr.com/1200/900/{','.join(words) or 'business'}?lock={i}"
        (target / "seed.json").write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")

        password = secrets.token_urlsafe(12)
        (target / ".env").write_text(
            "ADMIN_USER=admin\n"
            f"ADMIN_PASSWORD={password}\n"
            f"SECRET_KEY={secrets.token_hex(32)}\n"
            f"API_TOKEN={secrets.token_urlsafe(24)}\n",
            encoding="utf-8",
        )
        self.job.put("admin_credentials", {"user": "admin", "password": password})
        self.log(f"Proje yazıldı: {target}", "ok")
        return target
