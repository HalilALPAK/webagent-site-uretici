"""Proje genel ayarları ve basit .env yükleyici.

İki kök dizin vardır:
  RES_DIR  — salt okunur kaynaklar (şablonlar, DESIGN.md, laravel_stubs). .exe içinde paketlenir.
  HOME_DIR — yazılabilir veriler (görevler, üretilen siteler, PHP/Laravel araçları, .env).
Geliştirme ortamında ikisi de proje klasörüdür; .exe'de HOME_DIR = Belgeler/WebAgent.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
RES_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
if os.environ.get("WEBAGENT_HOME"):
    HOME_DIR = Path(os.environ["WEBAGENT_HOME"])
elif FROZEN:
    HOME_DIR = Path.home() / "Documents" / "WebAgent"
else:
    HOME_DIR = RES_DIR
ROOT = RES_DIR  # geriye uyumluluk

DATA_DIR = HOME_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"
OUTPUT_DIR = HOME_DIR / "output"
TOOLS_DIR = HOME_DIR / "tools"
ENV_FILE = HOME_DIR / ".env"
ENGINE_DIR = RES_DIR / "site_engine"
LARAVEL_STUBS = RES_DIR / "laravel_stubs"
DESIGN_GUIDE = RES_DIR / "DESIGN.md"


def load_env(path: Path = ENV_FILE) -> None:
    """python-dotenv bağımlılığı olmadan KEY=VALUE satırlarını okur."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value and key.strip() not in os.environ:
            os.environ[key.strip()] = value


def save_env_value(key: str, value: str) -> None:
    """HOME_DIR/.env içindeki bir anahtarı ekler/günceller (ör. sihirbazda girilen API anahtarı)."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    lines = [ln for ln in lines if not ln.startswith(f"{key}=")] + [f"{key}={value}"]
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


load_env()

MODEL = os.environ.get("WEBAGENT_MODEL", "claude-opus-5")
PORT = int(os.environ.get("WEBAGENT_PORT", "8000"))

# Üretilecek sitelerin teknolojisi: laravel (varsayılan) | python
STACK = os.environ.get("WEBAGENT_STACK", "laravel")
LARAVEL_BASE = Path(os.environ.get("LARAVEL_BASE", TOOLS_DIR / "laravel-base"))


def php_bin() -> str | None:
    """PHP_BIN ortam değişkeni, taşınabilir PHP (tools/php) ya da PATH'teki php."""
    import shutil
    env = os.environ.get("PHP_BIN")
    if env and Path(env).exists():
        return env
    local = TOOLS_DIR / "php" / ("php.exe" if os.name == "nt" else "php")
    if local.exists():
        return str(local)
    return shutil.which("php")


def tools_ready() -> bool:
    # Filament paneli en son adımda kurulur; bu dosya varsa kurulum tamamlanmıştır
    return bool(php_bin()) and (LARAVEL_BASE / "app" / "Providers" / "Filament" / "AdminPanelProvider.php").exists()


# Tarayıcı ajanı ayarları
CRAWL_USER_AGENT = "WebAgentResearchBot/1.0 (+competitive-analysis)"
CRAWL_MAX_PAGES_PER_SITE = 6
CRAWL_TIMEOUT = 15.0

for d in (JOBS_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)
