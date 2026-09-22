"""Laravel İnşa Ajanı: site tanımını gerçek bir Laravel 13 + Filament projesine dönüştürür.

Her site için üretilenler:
  - database/migrations/*  (her varlık için tablo)
  - app/Models/*           (Eloquent modelleri, cast'ler, belongsTo ilişkileri)
  - app/Filament/Resources/* (admin paneli: form, tablo, filtreler)
  - site.json / seed.json  (tema + yapı + örnek içerik), public/uploads/seed/* (görseller)
Ortak dosyalar (kontrolcü, rotalar, Blade şablonları, CSS, seeder, testler) laravel_stubs/ altından gelir.
"""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import time
from pathlib import Path


from ..config import LARAVEL_BASE, LARAVEL_STUBS, OUTPUT_DIR, php_bin
from ..values import coerce
from ..schemas import Site
from .base import Agent



RESERVED_CLASSES = {
    "User", "Message", "Subscriber", "Model", "Controller", "Request", "Response", "Route", "Resource",
    "Collection", "Str", "Arr", "Log", "File", "Storage", "Cache", "Event", "Job", "Mail", "Session",
    "View", "Schema", "Table", "Panel", "Page", "Site", "SiteConfig", "Filament", "Builder",
    # PHP ayrılmış kelimeleri
    "Class", "List", "Function", "Case", "Default", "Array", "Object", "String", "Int", "Float", "Bool",
    "Include", "Print", "Echo", "Match", "Enum", "Static", "Parent", "Self", "New", "Clone", "Global",
}
RESERVED_METHODS = {"query", "save", "update", "delete", "create", "fill", "push", "fresh", "load", "replicate",
                    "refresh", "touch", "increment", "decrement", "attributes", "relations", "table", "casts",
                    "connection", "key", "exists", "original", "changes"}
ICONS = {
    "rooms": "OutlinedHome", "services": "OutlinedSparkles", "product_catalog": "OutlinedShoppingBag",
    "booking_appointment": "OutlinedCalendarDays", "gallery": "OutlinedPhoto", "blog_news": "OutlinedNewspaper",
    "faq": "OutlinedQuestionMarkCircle", "testimonials_reviews": "OutlinedChatBubbleLeftRight",
    "team": "OutlinedUserGroup", "campaigns_discounts": "OutlinedGift", "events": "OutlinedTicket",
    "locations_map": "OutlinedMapPin", "jobs_careers": "OutlinedBriefcase", "pricing_plans": "OutlinedTag",
    "partners_references": "OutlinedBuildingOffice", "downloads_documents": "OutlinedDocumentText",
    "awards": "OutlinedTrophy", "press": "OutlinedNewspaper",
}


# Laravel'in `artisan serve` ile kullandığı yönlendirici; public/ klasöründen çalıştırılmalı.
SERVER_SCRIPT = "vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # .exe'den çalışırken konsol penceresi açılmasın


# ============================================================ yardımcılar

def php(s: object) -> str:
    """Python değerini PHP tek tırnaklı string literaline çevirir."""
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'") + "'"


def studly(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[_\-\s]+", name) if p)


def camel(name: str) -> str:
    s = studly(name)
    return s[:1].lower() + s[1:]


def singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "ches", "shes", "zes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def model_name(entity: str, taken: set[str]) -> str:
    parts = entity.split("_")
    name = studly("_".join(parts[:-1] + [singular(parts[-1])]))
    if name in RESERVED_CLASSES or not re.match(r"^[A-Z]", name):
        name += "Item"
    while name in taken:
        name += "Item"
    taken.add(name)
    return name


def enrich(site: Site) -> dict:
    """site.json için motorun ihtiyaç duyduğu türetilmiş bilgileri ekler (model, slug, sütun, ilişki metodu)."""
    data = site.model_dump()
    taken: set[str] = set()
    titles = {e["name"]: e["title_field"] for e in data["entities"]}
    for ent in data["entities"]:
        ent["model"] = model_name(ent["name"], taken)
        ent["slug"] = ent["name"].replace("_", "-")
        for f in ent["fields"]:
            if f["type"] == "relation":
                base = re.sub(r"_id$", "", f["name"])
                method = camel(base)
                if method in RESERVED_METHODS:
                    method += "Rel"
                f["column"], f["method"] = f"{base}_id", method
                f["relation_title"] = titles.get(f["relation"], "id")
            else:
                f["column"] = f["name"]
    data["currency"] = "₺" if data.get("language", "tr").startswith("tr") else "$"
    return data


# ============================================================ PHP kod üreticileri

MIGRATION_TYPES = {
    "string": "string", "email": "string", "url": "string", "phone": "string", "image": "string",
    "select": "string", "text": "text", "richtext": "longText", "int": "integer", "float": "double",
    "date": "date",
}


def gen_migration(ent: dict) -> str:
    cols = []
    for f in ent["fields"]:
        col = php(f["column"])
        t = f["type"]
        if t == "relation":
            cols.append(f"$table->foreignId({col})->nullable()->index();")
        elif t == "price":
            cols.append(f"$table->decimal({col}, 12, 2)->nullable();")
        elif t == "bool":
            cols.append(f"$table->boolean({col})->default(false);")
        else:
            cols.append(f"$table->{MIGRATION_TYPES.get(t, 'string')}({col})->nullable();")
    body = "\n            ".join(cols)
    return f"""<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{{
    public function up(): void
    {{
        Schema::create({php(ent['name'])}, function (Blueprint $table) {{
            $table->id();
            {body}
            $table->timestamps();
        }});
    }}

    public function down(): void
    {{
        Schema::dropIfExists({php(ent['name'])});
    }}
}};
"""


def gen_add_columns(table: str, fields: list[dict]) -> str:
    """Var olan tabloya yeni sütun ekleyen migration (revizyonlarda kullanılır)."""
    cols = []
    for f in fields:
        col, t = php(f["column"]), f["type"]
        if t == "relation":
            cols.append(f"$table->foreignId({col})->nullable()->index();")
        elif t == "price":
            cols.append(f"$table->decimal({col}, 12, 2)->nullable();")
        elif t == "bool":
            cols.append(f"$table->boolean({col})->default(false);")
        else:
            cols.append(f"$table->{MIGRATION_TYPES.get(t, 'string')}({col})->nullable();")
    body = "\n            ".join(cols)
    drops = ", ".join(php(f["column"]) for f in fields)
    return f"""<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{{
    public function up(): void
    {{
        Schema::table({php(table)}, function (Blueprint $table) {{
            {body}
        }});
    }}

    public function down(): void
    {{
        Schema::table({php(table)}, function (Blueprint $table) {{
            $table->dropColumn([{drops}]);
        }});
    }}
}};
"""


def gen_model(ent: dict, by_name: dict[str, dict]) -> str:
    casts = {"bool": "boolean", "date": "date", "price": "decimal:2", "int": "integer", "float": "float"}
    cast_lines = [f"{php(f['column'])} => {php(casts[f['type']])}," for f in ent["fields"] if f["type"] in casts]
    relations = []
    for f in ent["fields"]:
        if f["type"] == "relation":
            target = by_name[f["relation"]]["model"]
            relations.append(f"""
    public function {f['method']}(): BelongsTo
    {{
        return $this->belongsTo({target}::class, {php(f['column'])});
    }}
""")
    casts_block = "\n            ".join(cast_lines)
    return f"""<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;
use Illuminate\\Database\\Eloquent\\Relations\\BelongsTo;

class {ent['model']} extends Model
{{
    protected $table = {php(ent['name'])};

    protected $guarded = ['id'];

    protected function casts(): array
    {{
        return [
            {casts_block}
        ];
    }}
{''.join(relations)}}}
"""


def _form_component(f: dict, currency_code: str) -> str:
    col, label, t = php(f["column"]), php(f["label"]), f["type"]
    req = "->required()" if f.get("required") else ""
    match t:
        case "text":
            c = f"Textarea::make({col})->rows(4)->columnSpanFull()"
        case "richtext":
            c = f"MarkdownEditor::make({col})->columnSpanFull()"
        case "int":
            c = f"TextInput::make({col})->integer()"
        case "float":
            c = f"TextInput::make({col})->numeric()"
        case "price":
            c = f"TextInput::make({col})->numeric()->prefix({php(currency_code)})"
        case "bool":
            c, req = f"Toggle::make({col})", ""
        case "date":
            c = f"DatePicker::make({col})->native(false)->displayFormat('d.m.Y')"
        case "email":
            c = f"TextInput::make({col})->email()->maxLength(255)"
        case "url":
            c = f"TextInput::make({col})->url()->maxLength(255)"
        case "phone":
            c = f"TextInput::make({col})->tel()->maxLength(40)"
        case "image":
            c = f"FileUpload::make({col})->image()->imageEditor()->directory('content')->columnSpanFull()"
        case "select":
            opts = ", ".join(f"{php(o)} => {php(o)}" for o in f["options"])
            c = f"Select::make({col})->options([{opts}])->native(false)"
        case "relation":
            c = f"Select::make({col})->relationship({php(f['method'])}, {php(f['relation_title'])})->searchable()->preload()"
        case _:
            c = f"TextInput::make({col})->maxLength(255)"
    return f"{c}->label({label}){req},"


def _table_column(f: dict, ent: dict, currency_code: str) -> str | None:
    col, label, t = php(f["column"]), php(f["label"]), f["type"]
    is_title = f["name"] == ent["title_field"]
    if not (f.get("show_in_list") or is_title or f["name"] == ent.get("image_field")):
        return None
    match t:
        case "image":
            c = f"ImageColumn::make({col})->square()"
        case "bool":
            c = f"IconColumn::make({col})->boolean()"
        case "price":
            c = f"TextColumn::make({col})->money({php(currency_code)}, locale: 'tr')->sortable()"
        case "date":
            c = f"TextColumn::make({col})->date('d.m.Y')->sortable()"
        case "int" | "float":
            c = f"TextColumn::make({col})->numeric()->sortable()"
        case "select":
            c = f"TextColumn::make({col})->badge()->searchable()"
        case "relation":
            c = f"TextColumn::make({php(f['method'] + '.' + f['relation_title'])})"
        case "text" | "richtext":
            c = f"TextColumn::make({col})->limit(60)->wrap()"
        case _:
            c = f"TextColumn::make({col})->searchable()" + ("->sortable()" if is_title else "->limit(40)")
    return f"{c}->label({label}),"


def gen_resource(ent: dict, group: str, currency_code: str, sort: int, badge_unread: bool = False) -> dict[str, str]:
    """Filament 5 kaynak dosyalarını üretir: {göreli_yol: içerik}."""
    model, plural = ent["model"], studly(ent["name"])
    ns = f"App\\Filament\\Resources\\{plural}"
    form = "\n                ".join(_form_component(f, currency_code) for f in ent["fields"])
    image_cols = [f for f in ent["fields"] if f["name"] == ent.get("image_field")]
    ordered = image_cols + [f for f in ent["fields"] if f not in image_cols]
    columns = [c for f in ordered if (c := _table_column(f, ent, currency_code))]
    columns.append("TextColumn::make('created_at')->label('Eklenme')->dateTime('d.m.Y H:i')->sortable()->toggleable(isToggledHiddenByDefault: true),")
    filters = []
    for f in ent["fields"]:
        if f["type"] == "select":
            opts = ", ".join(f"{php(o)} => {php(o)}" for o in f["options"])
            filters.append(f"SelectFilter::make({php(f['column'])})->label({php(f['label'])})->options([{opts}]),")
        elif f["type"] == "bool":
            filters.append(f"TernaryFilter::make({php(f['column'])})->label({php(f['label'])}),")
        elif f["type"] == "relation":
            filters.append(f"SelectFilter::make({php(f['column'])})->label({php(f['label'])})->relationship({php(f['method'])}, {php(f['relation_title'])}),")
    icon = ICONS.get(ent.get("module_key", ""), "OutlinedRectangleStack")
    badge = """
    public static function getNavigationBadge(): ?string
    {
        return ($n = static::getModel()::where('is_read', false)->count()) ? (string) $n : null;
    }
""" if badge_unread else ""
    nl = "\n                "
    resource = f"""<?php

namespace {ns};

use {ns}\\Pages\\Create{model};
use {ns}\\Pages\\Edit{model};
use {ns}\\Pages\\List{plural};
use App\\Models\\{model};
use BackedEnum;
use Filament\\Actions\\BulkActionGroup;
use Filament\\Actions\\DeleteBulkAction;
use Filament\\Actions\\EditAction;
use Filament\\Forms\\Components\\DatePicker;
use Filament\\Forms\\Components\\FileUpload;
use Filament\\Forms\\Components\\MarkdownEditor;
use Filament\\Forms\\Components\\Select;
use Filament\\Forms\\Components\\TextInput;
use Filament\\Forms\\Components\\Textarea;
use Filament\\Forms\\Components\\Toggle;
use Filament\\Resources\\Resource;
use Filament\\Schemas\\Schema;
use Filament\\Support\\Icons\\Heroicon;
use Filament\\Tables\\Columns\\IconColumn;
use Filament\\Tables\\Columns\\ImageColumn;
use Filament\\Tables\\Columns\\TextColumn;
use Filament\\Tables\\Filters\\SelectFilter;
use Filament\\Tables\\Filters\\TernaryFilter;
use Filament\\Tables\\Table;
use UnitEnum;

class {model}Resource extends Resource
{{
    protected static ?string $model = {model}::class;

    protected static ?string $slug = {php(ent['slug'])};

    protected static ?string $recordTitleAttribute = {php(ent['title_field'])};

    protected static ?string $modelLabel = {php(ent['label'])};

    protected static ?string $pluralModelLabel = {php(ent['label_plural'])};

    protected static string|UnitEnum|null $navigationGroup = {php(group)};

    protected static ?int $navigationSort = {sort};

    protected static string|BackedEnum|null $navigationIcon = Heroicon::{icon};
{badge}
    public static function form(Schema $schema): Schema
    {{
        return $schema
            ->components([
                {form}
            ]);
    }}

    public static function table(Table $table): Table
    {{
        return $table
            ->columns([
                {nl.join(columns)}
            ])
            ->filters([
                {nl.join(filters)}
            ])
            ->defaultSort('id', 'desc')
            ->recordActions([
                EditAction::make(),
            ])
            ->toolbarActions([
                BulkActionGroup::make([
                    DeleteBulkAction::make(),
                ]),
            ]);
    }}

    public static function getPages(): array
    {{
        return [
            'index' => List{plural}::route('/'),
            'create' => Create{model}::route('/create'),
            'edit' => Edit{model}::route('/{{record}}/edit'),
        ];
    }}
}}
"""
    pages = {
        f"List{plural}": ("ListRecords", "CreateAction", "Filament\\Actions\\CreateAction"),
        f"Create{model}": ("CreateRecord", None, None),
        f"Edit{model}": ("EditRecord", "DeleteAction", "Filament\\Actions\\DeleteAction"),
    }
    base = f"app/Filament/Resources/{plural}"
    files = {f"{base}/{model}Resource.php": resource}
    for cls, (parent, action, action_fqcn) in pages.items():
        use_action = f"use {action_fqcn};\n" if action_fqcn else ""
        actions = f"""

    protected function getHeaderActions(): array
    {{
        return [
            {action}::make(),
        ];
    }}""" if action else ""
        files[f"{base}/Pages/{cls}.php"] = f"""<?php

namespace {ns}\\Pages;

use {ns}\\{model}Resource;
{use_action}use Filament\\Resources\\Pages\\{parent};

class {cls} extends {parent}
{{
    protected static string $resource = {model}Resource::class;{actions}
}}
"""
    return files


SYSTEM_RESOURCES = [
    ({"name": "messages", "model": "Message", "slug": "messages", "label": "Mesaj", "label_plural": "Mesajlar",
      "title_field": "name", "image_field": None, "module_key": "contact", "fields": [
          {"name": "name", "column": "name", "label": "Ad soyad", "type": "string", "required": True, "show_in_list": True, "options": []},
          {"name": "email", "column": "email", "label": "E-posta", "type": "email", "required": True, "show_in_list": True, "options": []},
          {"name": "phone", "column": "phone", "label": "Telefon", "type": "phone", "required": False, "show_in_list": False, "options": []},
          {"name": "subject", "column": "subject", "label": "Konu", "type": "string", "required": False, "show_in_list": True, "options": []},
          {"name": "body", "column": "body", "label": "Mesaj", "type": "text", "required": True, "show_in_list": False, "options": []},
          {"name": "is_read", "column": "is_read", "label": "Okundu", "type": "bool", "required": False, "show_in_list": True, "options": []},
      ]}, True),
    ({"name": "subscribers", "model": "Subscriber", "slug": "subscribers", "label": "Abone", "label_plural": "Bülten aboneleri",
      "title_field": "email", "image_field": None, "module_key": "newsletter", "fields": [
          {"name": "email", "column": "email", "label": "E-posta", "type": "email", "required": True, "show_in_list": True, "options": []},
      ]}, False),
]


# ============================================================ ajan

class LaravelBuilderAgent(Agent):
    name = "İnşa Ajanı"
    role = "Tasarımı Laravel 13 + Filament projesine (frontend + backend + admin + veritabanı) dönüştürmek."

    def run(self, site: Site, seed: dict[str, list[dict]], images: dict[str, Path] | None = None,
            credits: list[dict] | None = None, db: dict | None = None) -> Path:
        """images: {yuva_id: dosya} (Görsel Ajanı'ndan), db: {"type": "sqlite"} ya da MySQL bağlantı bilgisi."""
        php_exe = php_bin()
        if not php_exe or not (LARAVEL_BASE / "vendor").is_dir():
            raise RuntimeError("PHP veya Laravel temel projesi bulunamadı. Önce `python setup_laravel.py` çalıştırın.")
        images, credits, db = images or {}, credits or [], db or {"type": "sqlite"}

        data = enrich(site)
        target = OUTPUT_DIR / f"{data['slug']}-{self.job.id}"
        if target.exists():
            shutil.rmtree(target)

        self.log("Laravel + Filament temel projesi kopyalanıyor…")
        shutil.copytree(LARAVEL_BASE, target, ignore=shutil.ignore_patterns(
            ".env", "*.sqlite", "*.log", "node_modules", ".git", "ExampleTest.php", "welcome.blade.php"))
        shutil.copytree(LARAVEL_STUBS, target, dirs_exist_ok=True)

        self._place_images(data, seed, images, credits, target)
        self._place_logo(data, target)
        (target / "seed.json").write_text(json.dumps(self._coerce_seed(data, seed), ensure_ascii=False, indent=2), encoding="utf-8")
        (target / "site.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        self._write_code(data, target, with_migrations=True)
        self.log(f"{len(data['entities'])} tablo için migration, model ve Filament kaynağı üretildi.", "ok")

        password = secrets.token_urlsafe(12)
        email = "admin@" + (re.sub(r"[^a-z0-9]", "", data["slug"])[:20] or "site") + ".test"
        lang = "tr" if data.get("language", "tr").startswith("tr") else "en"
        app_key = "base64:" + base64.b64encode(secrets.token_bytes(32)).decode()
        (target / ".env").write_text("\n".join([
            f'APP_NAME="{data["site_name"]}"', "APP_ENV=local", f"APP_KEY={app_key}", "APP_DEBUG=true",
            "APP_URL=http://127.0.0.1:8000", f"APP_LOCALE={lang}", "APP_FALLBACK_LOCALE=en", f"APP_FAKER_LOCALE={lang}_TR" if lang == "tr" else "APP_FAKER_LOCALE=en_US",
            "LOG_CHANNEL=stack", "LOG_LEVEL=warning", *self._db_env(db), "SESSION_DRIVER=database",
            "SESSION_LIFETIME=240", "CACHE_STORE=database", "QUEUE_CONNECTION=sync", "FILESYSTEM_DISK=public",
            f"ADMIN_EMAIL={email}", f"ADMIN_PASSWORD={password}", "",
        ]), encoding="utf-8")
        (target / "database" / "database.sqlite").touch()

        where = "yerel SQLite" if db["type"] == "sqlite" else f"MySQL ({db.get('host')}/{db.get('database')})"
        self.log(f"Veritabanı kuruluyor ({where}) ve örnek içerik yükleniyor…")
        proc = subprocess.run([php_exe, "artisan", "migrate:fresh", "--seed", "--force", "--no-interaction"],
                              cwd=target, capture_output=True, text=True, encoding="utf-8", timeout=300,
                              creationflags=NO_WINDOW)
        if proc.returncode != 0:
            raise RuntimeError(f"migrate --seed başarısız:\n{(proc.stdout + proc.stderr)[-2500:]}")

        server = "..\\" + SERVER_SCRIPT.replace("/", "\\")
        (target / "run.bat").write_text(
            "@echo off\r\ncd /d %~dp0public\r\n"
            "echo Site: http://127.0.0.1:8100   Admin: http://127.0.0.1:8100/admin\r\n"
            f"\"{php_exe}\" -S 127.0.0.1:8100 {server}\r\n",
            encoding="utf-8")
        self.job.put("admin_credentials", {"user": email, "password": password})
        self.log(f"Laravel projesi hazır: {target}", "ok")
        return target

    # ------------------------------------------------------------ içerik
    def _coerce_seed(self, data: dict, seed: dict[str, list[dict]]) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for ent in data["entities"]:
            rows = []
            for rec in seed.get(ent["name"], []):
                row = {}
                for f in ent["fields"]:
                    raw = rec.get(f["name"])
                    if f["type"] == "image":
                        row[f["name"]] = raw  # _place_images dosya yolunu yazdı (ya da None)
                        continue
                    if f["type"] == "relation":
                        row[f["name"]] = int(float(raw)) if str(raw or "").strip().replace(".", "", 1).isdigit() else None
                        continue
                    try:
                        value = coerce({**f, "required": False}, raw)
                    except (ValueError, TypeError):
                        value = None
                    row[f["name"]] = bool(value) if f["type"] == "bool" else value
                rows.append(row)
            out[ent["name"]] = rows
        return out

    @staticmethod
    def _write_code(data: dict, target: Path, with_migrations: bool) -> None:
        """Model, Filament kaynağı ve (isteğe bağlı) tablo migration'larını yazar."""
        by_name = {e["name"]: e for e in data["entities"]}
        currency_code = "TRY" if data["currency"] == "₺" else "USD"
        files: dict[str, str] = {}
        for i, ent in enumerate(data["entities"]):
            if with_migrations:
                files[f"database/migrations/2026_01_01_{200 + i:06d}_create_{ent['name']}_table.php"] = gen_migration(ent)
            files[f"app/Models/{ent['model']}.php"] = gen_model(ent, by_name)
            files.update(gen_resource(ent, "İçerik" if ent["public"] else "Operasyon", currency_code, sort=i + 1))
        for i, (ent, badge) in enumerate(SYSTEM_RESOURCES):
            files.update(gen_resource(ent, "Etkileşim", currency_code, sort=50 + i, badge_unread=badge))
        for rel, content in files.items():
            path = target / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    @staticmethod
    def diff_spec(old: dict, new: dict) -> dict:
        """İki site tanımı arasındaki fark: veritabanı güncellemesi ve kullanıcıya özet için."""
        old_ents = {e["name"]: e for e in old.get("entities", [])}
        new_ents = {e["name"]: e for e in new["entities"]}
        added_fields: dict[str, list[dict]] = {}
        removed_fields: dict[str, list[str]] = {}
        for name, ent in new_ents.items():
            if name not in old_ents:
                continue
            old_cols = {f.get("column", f["name"]) for f in old_ents[name]["fields"]}
            new_cols = {f.get("column", f["name"]) for f in ent["fields"]}
            fresh = [f for f in ent["fields"] if f.get("column", f["name"]) not in old_cols]
            if fresh:
                added_fields[name] = fresh
            if gone := sorted(old_cols - new_cols):
                removed_fields[name] = gone
        old_pages = {p["slug"] for p in old.get("pages", [])}
        new_pages = {p["slug"] for p in new["pages"]}
        return {
            "added_entities": [n for n in new_ents if n not in old_ents],
            "removed_entities": [n for n in old_ents if n not in new_ents],
            "added_fields": added_fields, "removed_fields": removed_fields,
            "added_pages": sorted(new_pages - old_pages), "removed_pages": sorted(old_pages - new_pages),
            "theme_changed": [k for k, v in new["theme"].items()
                              if k != "hero_image" and old.get("theme", {}).get(k) != v],
        }

    def revise(self, site: Site, target: Path, seed_new: dict[str, list[dict]],
               images: dict[str, Path] | None = None, credits: list[dict] | None = None) -> dict:
        """Var olan siteyi yerinde günceller. Veri silinmez: tablo ve sütunlar yalnızca eklenir."""
        php_exe = php_bin()
        old_data = json.loads((target / "site.json").read_text(encoding="utf-8"))
        data = enrich(site)
        diff = self.diff_spec(old_data, data)

        backup = target / ".revisions" / time.strftime("%Y%m%d-%H%M%S")
        backup.mkdir(parents=True, exist_ok=True)
        for name in ("site.json", "seed.json", "database/database.sqlite"):
            if (src := target / name).exists():
                shutil.copy(src, backup / Path(name).name)
        self.log(f"Yedek alındı: .revisions/{backup.name}")

        shutil.copytree(LARAVEL_STUBS, target, dirs_exist_ok=True)  # şablon/CSS güncellemeleri
        data["theme"]["hero_image"] = old_data.get("theme", {}).get("hero_image")  # eski görseller korunur
        self._place_images(data, seed_new, images or {}, credits or [], target)
        self._place_logo(data, target)
        have = {c["file"] for c in data.get("image_credits", [])}
        data["image_credits"] = data.get("image_credits", []) + [
            c for c in old_data.get("image_credits", []) if c["file"] not in have]
        (target / "site.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_code(data, target, with_migrations=False)

        stamp = time.strftime("%Y_%m_%d_%H%M%S")
        by_name = {e["name"]: e for e in data["entities"]}
        migrations = target / "database" / "migrations"
        for i, name in enumerate(diff["added_entities"]):
            (migrations / f"{stamp}{i:02d}_create_{name}_table.php").write_text(
                gen_migration(by_name[name]), encoding="utf-8")
        for i, (name, fields) in enumerate(diff["added_fields"].items(), start=50):
            (migrations / f"{stamp}{i:02d}_add_columns_to_{name}_table.php").write_text(
                gen_add_columns(name, fields), encoding="utf-8")

        rows = {n: r for n, r in self._coerce_seed(data, seed_new).items() if r}
        (target / "revision-seed.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

        for command, label in ((["migrate", "--force"], "Veritabanı güncellemesi"),
                               (["db:seed", "--class=RevisionSeeder", "--force"], "Yeni içerik eklenmesi"),
                               (["view:clear"], "Şablon yenileme"),
                               (["config:clear"], "Ayar yenileme")):
            proc = subprocess.run([php_exe, "artisan", *command], cwd=target, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=300, creationflags=NO_WINDOW)
            if proc.returncode != 0:
                raise RuntimeError(f"{label} başarısız:\n{(proc.stdout + proc.stderr)[-1500:]}")

        parts = []
        if diff["added_entities"]:
            parts.append(f"{len(diff['added_entities'])} yeni tablo")
        if diff["added_fields"]:
            parts.append(f"{sum(len(v) for v in diff['added_fields'].values())} yeni alan")
        if diff["removed_entities"] or diff["removed_fields"]:
            parts.append("kaldırılanlar sitede görünmüyor (veri korundu)")
        if diff["theme_changed"]:
            parts.append("tema güncellendi")
        self.log("Site güncellendi: " + (", ".join(parts) or "metin ve içerik değişiklikleri"), "ok")
        return diff

    @staticmethod
    def _db_env(db: dict) -> list[str]:
        if db.get("type") != "mysql":
            return ["DB_CONNECTION=sqlite"]
        def q(v: object) -> str:  # .env değerini tırnakla (boşluk, # vb. için)
            return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'
        return ["DB_CONNECTION=mysql", f"DB_HOST={q(db['host'])}", f"DB_PORT={int(db.get('port') or 3306)}",
                f"DB_DATABASE={q(db['database'])}", f"DB_USERNAME={q(db['username'])}", f"DB_PASSWORD={q(db.get('password', ''))}"]

    def _place_logo(self, data: dict, target: Path) -> None:
        """Kullanıcı logo yüklediyse public/uploads/logo.png olarak koyar (yoksa harf logosu kullanılır)."""
        dest = target / "public" / "uploads" / "logo.png"
        source = self.job.artifacts.get("logo")
        if source and Path(source).exists():
            from PIL import Image
            dest.parent.mkdir(parents=True, exist_ok=True)
            img = Image.open(source)
            img = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img.convert("RGB")
            img.thumbnail((600, 200))
            img.save(dest, "PNG")
            self.log("Logonuz siteye yerleştirildi.", "ok")
        if dest.exists():
            data["branding"]["logo"] = "logo.png"

    @staticmethod
    def _place_images(data: dict, seed: dict[str, list[dict]], images: dict[str, Path], credits: list[dict],
                      target: Path) -> None:
        """Görsel Ajanı'nın hazırladığı dosyaları public/uploads/seed altına koyar ve seed'e yollarını yazar."""
        folder = target / "public" / "uploads" / "seed"
        folder.mkdir(parents=True, exist_ok=True)

        def put(slot: str) -> str | None:
            src = images.get(slot)
            if not src or not Path(src).exists():
                return None
            shutil.copy(src, folder / f"{slot}.jpg")
            return f"seed/{slot}.jpg"

        # Yeni hero görseli seçilmediyse mevcut olan korunur (revizyonda kaybolmasın)
        if (hero := put("hero")) or not data["theme"].get("hero_image"):
            data["theme"]["hero_image"] = hero
        for ent in data["entities"]:
            for f in (f for f in ent["fields"] if f["type"] == "image"):
                for i, rec in enumerate(seed.get(ent["name"], []), start=1):
                    rec[f["name"]] = put(f"{ent['name']}__{f['name']}__{i}")
        data["image_credits"] = [c | {"file": f"seed/{c['slot']}.jpg"} for c in credits if images.get(c["slot"])]
