"""site.json'daki varlık tanımlarından SQLite şeması üreten veri katmanı."""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator

IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")

SQL_TYPES = {"int": "INTEGER", "bool": "INTEGER", "relation": "INTEGER", "float": "REAL", "price": "REAL"}

SYSTEM_TABLES = {
    "messages": """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, phone TEXT,
        subject TEXT, body TEXT, is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""",
    "subscribers": """CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""",
}


def q(name: str) -> str:
    """Tablo/sütun adını doğrulayıp tırnaklar (SQL enjeksiyonuna karşı)."""
    if not IDENT.match(name):
        raise ValueError(f"Geçersiz tanımlayıcı: {name!r}")
    return f'"{name}"'


class ValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


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


class DB:
    def __init__(self, path: Path, spec: dict):
        self.path = path
        self.spec = spec
        self.entities = {e["name"]: e for e in spec["entities"]}

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        """İşlem sonunda commit eden ve bağlantıyı kapatan bağlam."""
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    # ------------------------------------------------------------ şema
    def init_schema(self) -> None:
        with self.conn() as c:
            for sql in SYSTEM_TABLES.values():
                c.execute(sql)
            for ent in self.entities.values():
                cols = [f"{q(f['name'])} {SQL_TYPES.get(f['type'], 'TEXT')}" for f in ent["fields"]]
                c.execute(
                    f"CREATE TABLE IF NOT EXISTS {q(ent['name'])} (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + ", ".join(cols + ["created_at TEXT DEFAULT CURRENT_TIMESTAMP"]) + ")"
                )
                # spec sonradan değişirse eksik sütunları ekle
                existing = {r["name"] for r in c.execute(f"PRAGMA table_info({q(ent['name'])})")}
                for f in ent["fields"]:
                    if f["name"] not in existing:
                        c.execute(f"ALTER TABLE {q(ent['name'])} ADD COLUMN {q(f['name'])} {SQL_TYPES.get(f['type'], 'TEXT')}")

    def is_empty(self) -> bool:
        with self.conn() as c:
            return all(c.execute(f"SELECT COUNT(*) FROM {q(n)}").fetchone()[0] == 0 for n in self.entities)

    def seed(self, data: dict[str, list[dict]]) -> None:
        """Örnek veriyi yükler. relation alanları 'hedefteki N. kayıt' olarak gelir."""
        ids: dict[str, list[int]] = {}
        pending: list[tuple[str, int, str, str]] = []  # (tablo, id, alan, hedef sıra no)
        with self.conn() as c:
            for name, ent in self.entities.items():
                ids[name] = []
                for rec in data.get(name, []):
                    row, rels = {}, []
                    for f in ent["fields"]:
                        raw = rec.get(f["name"])
                        if f["type"] == "relation":
                            if raw not in (None, ""):
                                rels.append((f["name"], str(raw)))
                            continue
                        try:
                            row[f["name"]] = coerce({**f, "required": False}, raw)
                        except (ValueError, TypeError):
                            row[f["name"]] = None
                    if row:
                        cur = c.execute(self._insert_sql(name, row), list(row.values()))
                    else:
                        cur = c.execute(f"INSERT INTO {q(name)} DEFAULT VALUES")
                    ids[name].append(cur.lastrowid)
                    pending.extend((name, cur.lastrowid, fname, v) for fname, v in rels)
            for name, row_id, fname, value in pending:
                target = next(f["relation"] for f in self.entities[name]["fields"] if f["name"] == fname)
                try:
                    idx = int(float(value)) - 1
                    target_id = ids.get(target, [])[idx] if 0 <= idx < len(ids.get(target, [])) else None
                except ValueError:
                    target_id = None
                if target_id:
                    c.execute(f"UPDATE {q(name)} SET {q(fname)} = ? WHERE id = ?", (target_id, row_id))

    # ------------------------------------------------------------ CRUD
    @staticmethod
    def _insert_sql(name: str, row: dict) -> str:
        cols = ", ".join(q(k) for k in row)
        return f"INSERT INTO {q(name)} ({cols}) VALUES ({', '.join('?' for _ in row)})"

    def validate(self, name: str, data: dict, partial: bool = False) -> dict:
        ent = self.entities[name]
        out, errors = {}, {}
        for f in ent["fields"]:
            if partial and f["name"] not in data:
                continue
            raw = data.get(f["name"])
            if f["type"] == "bool" and raw is None and not partial:
                raw = False
            try:
                out[f["name"]] = coerce(f, raw)
            except (ValueError, TypeError) as e:
                errors[f["name"]] = str(e) if str(e) else "Geçersiz değer"
        if errors:
            raise ValidationError(errors)
        return out

    def list(self, name: str, search: str = "", page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
        ent = self.entities[name]
        where, params = "", []
        text_fields = [f["name"] for f in ent["fields"] if f["type"] in ("string", "text", "richtext", "select", "email")]
        if search and text_fields:
            where = "WHERE " + " OR ".join(f"{q(f)} LIKE ?" for f in text_fields)
            params = [f"%{search}%"] * len(text_fields)
        with self.conn() as c:
            total = c.execute(f"SELECT COUNT(*) FROM {q(name)} {where}", params).fetchone()[0]
            rows = c.execute(
                f"SELECT * FROM {q(name)} {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [per_page, max(0, page - 1) * per_page],
            ).fetchall()
        return [dict(r) for r in rows], total

    def get(self, name: str, row_id: int) -> dict | None:
        with self.conn() as c:
            r = c.execute(f"SELECT * FROM {q(name)} WHERE id = ?", (row_id,)).fetchone()
        return dict(r) if r else None

    def create(self, name: str, data: dict) -> int:
        row = self.validate(name, data)
        with self.conn() as c:
            return c.execute(self._insert_sql(name, row), list(row.values())).lastrowid

    def update(self, name: str, row_id: int, data: dict, partial: bool = False) -> None:
        row = self.validate(name, data, partial=partial)
        if not row:
            return
        sets = ", ".join(f"{q(k)} = ?" for k in row)
        with self.conn() as c:
            c.execute(f"UPDATE {q(name)} SET {sets} WHERE id = ?", list(row.values()) + [row_id])

    def delete(self, name: str, row_id: int) -> None:
        with self.conn() as c:
            c.execute(f"DELETE FROM {q(name)} WHERE id = ?", (row_id,))

    def count(self, name: str) -> int:
        with self.conn() as c:
            return c.execute(f"SELECT COUNT(*) FROM {q(name)}").fetchone()[0]

    def titles(self, name: str) -> dict[int, str]:
        """relation alanlarını göstermek için id -> başlık haritası."""
        ent = self.entities[name]
        with self.conn() as c:
            rows = c.execute(f"SELECT id, {q(ent['title_field'])} AS t FROM {q(name)}").fetchall()
        return {r["id"]: str(r["t"] or f"#{r['id']}") for r in rows}

    # ------------------------------------------------------------ sistem tabloları
    def add_message(self, **kw) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO messages (name, email, phone, subject, body) VALUES (?,?,?,?,?)",
                      (kw.get("name"), kw.get("email"), kw.get("phone"), kw.get("subject"), kw.get("body")))

    def messages(self) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM messages ORDER BY id DESC")]

    def mark_read(self, msg_id: int) -> None:
        with self.conn() as c:
            c.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (msg_id,))

    def delete_message(self, msg_id: int) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM messages WHERE id = ?", (msg_id,))

    def subscribe(self, email: str) -> None:
        with self.conn() as c:
            c.execute("INSERT OR IGNORE INTO subscribers (email) VALUES (?)", (email,))

    def subscribers(self) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM subscribers ORDER BY id DESC")]

    def unread_count(self) -> int:
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM messages WHERE is_read = 0").fetchone()[0]
