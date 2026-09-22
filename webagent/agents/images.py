"""Görsel Ajanı: görsel gruplarını (hero, her varlığın görsel alanı) çıkarır, hazır görsel adayları bulur
ve kullanıcının seçimlerini (hazır / kendi yüklediği / boş) dosyaya dönüştürür.

Grup  = birbiriyle ilgili görseller (ör. "Şubelerimiz"); her kayıt bir yuva (slot).
Seçim = {"type": "stock", "cid": aday_id} | {"type": "upload", "file": yol} | {"type": "none"}
Hazır görseller Openverse'ten gelir (ticari kullanıma açık CC lisanslı). Anonim limit: 20 istek/dk, 200/gün.
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import httpx

from ..schemas import Site
from .base import Agent

UA = {"User-Agent": "WebAgent/1.0 (site generator)"}


def _query_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+", (text or "").split(",")[0])[:4]


def save_image(data: bytes, path: Path, max_w: int) -> bool:
    """Görseli doğrular, küçültür ve JPEG olarak yazar."""
    from PIL import Image, ImageOps
    try:
        img = ImageOps.exif_transpose(Image.open(BytesIO(data))).convert("RGB")
    except Exception:
        return False
    if img.width < 300:
        return False
    img.thumbnail((max_w, max_w))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=84, optimize=True, progressive=True)
    return True


class ImageAgent(Agent):
    name = "Görsel Ajanı"
    role = "Görsel gruplarını çıkarmak, hazır görsel adayları bulmak ve kullanıcı seçimlerini uygulamak."

    # ------------------------------------------------------------ 1) gruplar + adaylar
    def find_candidates(self, site: Site, seed: dict[str, list[dict]], include_hero: bool = True,
                        own_images: list[dict] | None = None) -> dict:
        groups: list[dict] = []
        theme = site.theme
        if include_hero and theme.hero_variant != "centered":
            groups.append({
                "id": "hero", "label": "Ana sayfa görseli", "hint": "Sitenin en üstündeki büyük görsel",
                "query": theme.hero_image_keywords, "wide": theme.hero_variant == "image", "max_w": 2000,
                "slots": [{"id": "hero", "title": site.site_name}],
            })
        for ent in site.entities:
            image_fields = [f for f in ent.fields if f.type == "image"]
            for f in image_fields:
                records = seed.get(ent.name, [])
                if not records:
                    continue
                label = ent.label_plural + (f" — {f.label}" if len(image_fields) > 1 else "")
                groups.append({
                    "id": f"{ent.name}__{f.name}", "label": label,
                    "hint": f"{len(records)} kayıt · {'sitede görünür' if ent.public else 'yalnızca yönetim panelinde'}",
                    # içerik ajanı İngilizce anahtar kelime yazar; yoksa temanın (İngilizce) hero kelimeleri
                    "query": str(records[0].get(f.name) or theme.hero_image_keywords),
                    "wide": ent.module_key != "team", "max_w": 1400,
                    "slots": [{"id": f"{ent.name}__{f.name}__{i}", "title": str(rec.get(ent.title_field) or f"#{i}")}
                              for i, rec in enumerate(records, start=1)],
                })

        client = httpx.Client(headers=UA, timeout=30, follow_redirects=True)
        own = [{"id": f"own-{i}", "url": img["url"], "thumb": img["url"], "title": img.get("alt") or "Eski sitenizden",
                "creator": "", "license": "", "license_url": "", "source_url": img["url"], "own": True}
               for i, img in enumerate(own_images or [])]
        if own:
            self.log(f"Mevcut sitenizden {len(own)} görsel öneri havuzuna eklendi.", "ok")
        choices: dict[str, dict] = {}
        found = 0
        taken: set[str] = set()  # aynı görsel iki gruba birden önerilmesin
        for g in groups:
            # önce kullanıcının kendi görselleri, sonra hazır (CC) öneriler
            g["pool"] = [c for c in own if c["id"] not in taken] + [
                c for c in self._search_pool(client, g["query"], g["wide"], need=len(g["slots"]) + 6)
                if c["id"] not in taken]
            for slot, cand in zip(g["slots"], g["pool"]):
                choices[slot["id"]] = {"type": "stock", "cid": cand["id"]}
                taken.add(cand["id"])
                found += 1
            for slot in g["slots"][len(g["pool"]):]:
                choices[slot["id"]] = {"type": "none"}
        client.close()
        total = sum(len(g["slots"]) for g in groups)
        self.log(f"{len(groups)} görsel grubu, {total} görsel yuvası; {found} yuva için hazır görsel önerildi.", "ok")
        return {"groups": groups, "choices": choices}

    def _search_pool(self, client: httpx.Client, query: str, wide: bool, need: int) -> list[dict]:
        """Tam sorgu yetmezse kelime atarak genişletir. Aynı görsel iki kez önerilmez."""
        words = _query_words(query) or ["business"]
        pool: list[dict] = []
        seen: set[str] = set()
        for n in range(len(words), 0, -1):
            params = {"q": " ".join(words[:n]), "page_size": 20,  # anonim üst sınır 20
                      "license_type": "commercial", "mature": "false"}
            if wide:
                params["aspect_ratio"] = "wide"
            try:
                r = client.get("https://api.openverse.org/v1/images/", params=params)
                results = r.json().get("results", []) if r.status_code == 200 else []
                if r.status_code != 200:
                    self.log(f"Görsel araması başarısız ({r.status_code}): {params['q']}", "warn")
            except (httpx.HTTPError, ValueError):
                results = []
            for x in sorted(results, key=lambda x: "nd" in (x.get("license") or "")):  # türev izni olanlar önce
                if x["id"] in seen or (x.get("width") or 0) < 900 or x.get("source") not in ("flickr", "wikimedia"):
                    continue
                seen.add(x["id"])
                pool.append({
                    "id": x["id"], "url": x["url"], "thumb": x.get("thumbnail") or x["url"],
                    "title": x.get("title") or "", "creator": x.get("creator") or "",
                    "license": f"CC {(x.get('license') or '').upper()} {x.get('license_version') or ''}".strip(),
                    "license_url": x.get("license_url") or "", "source_url": x.get("foreign_landing_url") or "",
                })
            if len(pool) >= need or n <= 2:
                break
        return pool

    # ------------------------------------------------------------ 2) seçimleri uygula
    def materialize(self, images: dict, staging: Path) -> tuple[dict[str, Path], list[dict]]:
        """Seçimleri dosyaya çevirir: {yuva_id: dosya_yolu}, CC atıf listesi."""
        staging.mkdir(parents=True, exist_ok=True)
        client = httpx.Client(headers=UA, timeout=40, follow_redirects=True)
        files: dict[str, Path] = {}
        credits: list[dict] = []
        used = {c.get("cid") for c in images["choices"].values() if c.get("type") == "stock"}
        stock = uploaded = 0

        for g in images["groups"]:
            by_id = {c["id"]: c for c in g["pool"]}
            spare = [c for c in g["pool"] if c["id"] not in used]
            for slot in g["slots"]:
                choice = images["choices"].get(slot["id"], {"type": "none"})
                dest = staging / f"{slot['id']}.jpg"
                if choice["type"] == "upload" and Path(choice.get("file", "")).exists():
                    if save_image(Path(choice["file"]).read_bytes(), dest, g["max_w"]):
                        files[slot["id"]] = dest
                        uploaded += 1
                    continue
                if choice["type"] != "stock":
                    continue
                # seçilen aday inmezse aynı gruptaki kullanılmamış bir adayla dene
                for cand in [by_id.get(choice.get("cid"))] + spare:
                    if cand and self._download(client, cand, dest, g["max_w"]):
                        files[slot["id"]] = dest
                        credits.append({k: cand[k] for k in ("title", "creator", "license", "license_url", "source_url")}
                                       | {"slot": slot["id"]})
                        stock += 1
                        if cand in spare:
                            spare.remove(cand)
                        break
        client.close()
        self.log(f"Görseller hazır: {stock} hazır görsel, {uploaded} yüklenen görsel.", "ok")
        return files, credits

    @staticmethod
    def _download(client: httpx.Client, cand: dict, dest: Path, max_w: int) -> bool:
        url = cand["url"]
        m = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w/\w\w)/([^/]+)$", url)
        if m and not url.lower().endswith(".svg"):  # dev dosya yerine Wikimedia küçük resmi
            url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{m.group(2)}/1600px-{m.group(2)}"
        try:
            r = client.get(url)
        except httpx.HTTPError:
            return False
        return r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and save_image(r.content, dest, max_w)
