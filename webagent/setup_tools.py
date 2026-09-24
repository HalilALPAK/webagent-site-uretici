"""Laravel üretimi için gereken araçları kurar (ilk açılışta bir kez).

- Windows'ta taşınabilir PHP 8.4 (windows.php.net, SHA-256 doğrulamalı) → tools/php
- Linux/macOS'ta sistemdeki PHP kullanılır; yoksa dağıtımınıza uygun kurulum komutu gösterilir
- Composer (getcomposer.org, SHA-256 doğrulamalı) → tools/composer.phar
- Laravel 13 + Filament temel projesi → tools/laravel-base (her site bunun kopyasıdır)
Yönetici yetkisi gerekmez. PHP zaten PATH'teyse o kullanılır.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import subprocess
import zipfile
from typing import Callable

import httpx

from .config import LARAVEL_BASE, TOOLS_DIR, php_bin

PHP_DIR = TOOLS_DIR / "php"
COMPOSER = TOOLS_DIR / "composer.phar"
PHP_BRANCH = "8.4"
EXTENSIONS = ["curl", "fileinfo", "gd", "intl", "mbstring", "openssl", "pdo_sqlite", "sqlite3", "zip", "exif",
              "pdo_mysql", "mysqli"]
UA = {"User-Agent": "Mozilla/5.0 (web-agent setup)"}
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # .exe'den çalışırken konsol penceresi açılmasın

Log = Callable[[str], None]


class SetupError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def enable_extensions(ini_path) -> None:
    ini = ini_path.read_text(encoding="utf-8")
    ini = ini.replace(';extension_dir = "ext"', 'extension_dir = "ext"').replace("memory_limit = 128M", "memory_limit = 1G")
    for ext in EXTENSIONS:
        ini = re.sub(rf"^;extension={ext}\s*$", f"extension={ext}", ini, flags=re.M)
    ini_path.write_text(ini, encoding="utf-8")


# Laravel + Filament + üretilen sitelerin çalışması için gereken en küçük küme
REQUIRED_EXT = ["mbstring", "openssl", "curl", "dom", "xml", "tokenizer", "ctype", "fileinfo",
                "pdo_sqlite", "sqlite3", "zip", "gd", "intl"]
MIN_VERSION = (8, 2)
# apt/dnf/pacman/zypper için eklenti → paket adı kalıpları
PKG_HINTS = {
    "apt-get": ("sudo apt install -y", "php-cli php-sqlite3 php-curl php-mbstring php-xml php-zip php-gd php-intl"),
    "dnf": ("sudo dnf install -y", "php-cli php-pdo php-mbstring php-xml php-gd php-intl php-sodium"),
    "pacman": ("sudo pacman -S --needed", "php php-gd php-intl php-sqlite"),
    "zypper": ("sudo zypper install -y", "php8 php8-cli php8-sqlite php8-curl php8-mbstring php8-dom php8-zip php8-gd php8-intl"),
    "apk": ("sudo apk add", "php php-cli php-pdo_sqlite php-sqlite3 php-curl php-mbstring php-dom php-xml php-tokenizer php-fileinfo php-zip php-gd php-intl"),
    "brew": ("brew install", "php"),
}


def install_hint() -> str:
    """Kullanıcının dağıtımına uygun PHP kurulum komutu."""
    for mgr, (cmd, pkgs) in PKG_HINTS.items():
        if shutil.which(mgr):
            return f"{cmd} {pkgs}"
    return "Dağıtımınızın paket yöneticisiyle PHP 8.2+ kurun (cli, sqlite, curl, mbstring, xml, zip, gd, intl eklentileriyle)."


def php_report(php: str) -> tuple[tuple[int, int] | None, list[str]]:
    """PHP'nin sürümünü ve eksik eklentilerini döndürür."""
    try:
        out = subprocess.run([php, "-r", "echo PHP_MAJOR_VERSION.'.'.PHP_MINOR_VERSION.'|'.implode(',', get_loaded_extensions());"],
                             capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW).stdout
        ver_txt, _, ext_txt = out.strip().partition("|")
        version = tuple(int(x) for x in ver_txt.split(".")[:2])
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, list(REQUIRED_EXT)
    loaded = {e.strip().lower() for e in ext_txt.split(",")}
    missing = [e for e in REQUIRED_EXT if e not in loaded]
    return version, missing  # type: ignore[return-value]


def system_php_problem(php: str) -> str | None:
    """Sistemdeki PHP yeterliyse None, değilse kısa açıklama döndürür."""
    version, missing = php_report(php)
    if version is None:
        return "çalıştırılamadı"
    if version < MIN_VERSION:
        return f"sürüm {version[0]}.{version[1]}, en az 8.2 gerekiyor"
    if missing:
        return "eksik eklentiler: " + ", ".join(missing)
    return None


def install_php(log: Log) -> str:
    found = php_bin()
    if found and not str(found).startswith(str(PHP_DIR)):  # sistemde PHP var
        problem = system_php_problem(found)
        if not problem:
            log(f"PHP bulundu: {found}")
            return found
        log(f"Sistemdeki PHP kullanılamıyor ({problem}).")
    exe = PHP_DIR / ("php.exe" if os.name == "nt" else "php")
    if exe.exists():
        return str(exe)
    if os.name != "nt":  # Linux/macOS: PHP paket yöneticisinden kurulur (tek satırlık komut gösterilir)
        raise SetupError("Uygun bir PHP bulunamadı. Şu komutla kurun:\n  " + install_hint() +
                         "\nKurduktan sonra 'Tekrar dene' düğmesine basın.")

    releases = httpx.get("https://windows.php.net/downloads/releases/releases.json", headers=UA, timeout=60,
                         follow_redirects=True).json()
    info = releases[PHP_BRANCH]["nts-vs17-x64"]["zip"]
    url = f"https://windows.php.net/downloads/releases/{info['path']}"
    log(f"PHP indiriliyor ({info.get('size', '')}): {info['path']}")
    data = httpx.get(url, headers=UA, timeout=600, follow_redirects=True).content
    if _sha256(data) != info["sha256"]:
        raise SetupError("PHP arşivinin SHA-256 özeti eşleşmedi; kurulum durduruldu.")
    zipfile.ZipFile(io.BytesIO(data)).extractall(PHP_DIR)
    shutil.copy(PHP_DIR / "php.ini-development", PHP_DIR / "php.ini")
    enable_extensions(PHP_DIR / "php.ini")
    log("PHP kuruldu ve doğrulandı.")
    return str(exe)


def install_composer(log: Log) -> None:
    if COMPOSER.exists():
        return
    stable = httpx.get("https://getcomposer.org/versions", timeout=60, follow_redirects=True).json()["stable"][0]
    base = f"https://getcomposer.org{stable['path']}"
    log(f"Composer {stable['version']} indiriliyor…")
    data = httpx.get(base, timeout=300, follow_redirects=True).content
    expected = httpx.get(base + ".sha256sum", timeout=60, follow_redirects=True).text.split()[0]
    if _sha256(data) != expected:
        raise SetupError("composer.phar SHA-256 özeti eşleşmedi; kurulum durduruldu.")
    COMPOSER.write_bytes(data)
    log("Composer kuruldu ve doğrulandı.")


def create_base(php: str, log: Log) -> None:
    if (LARAVEL_BASE / "app" / "Providers" / "Filament" / "AdminPanelProvider.php").exists():
        log("Laravel temel projesi hazır.")
        return
    env = {**os.environ, "COMPOSER_HOME": str(TOOLS_DIR / ".composer"), "COMPOSER_NO_INTERACTION": "1"}

    def run(args: list[str], cwd) -> None:
        log("› " + " ".join(a if " " not in a else f'"{a}"' for a in args[1:]))
        proc = subprocess.Popen([php, *args], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        for line in proc.stdout:
            line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
            if line and not line.startswith(("-", "0/", " ")):
                log("  " + line[:160])
        if proc.wait() != 0:
            raise SetupError(f"Komut başarısız: {' '.join(args[:3])}")

    if LARAVEL_BASE.exists():
        shutil.rmtree(LARAVEL_BASE)
    run([str(COMPOSER), "create-project", "laravel/laravel", LARAVEL_BASE.name, "--no-interaction", "--prefer-dist"], TOOLS_DIR)
    run([str(COMPOSER), "require", "filament/filament", "--no-interaction", "-W"], LARAVEL_BASE)
    run(["artisan", "filament:install", "--panels", "--no-interaction"], LARAVEL_BASE)
    log("Laravel + Filament temel projesi hazır.")


def setup_all(log: Log = print) -> None:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    php = install_php(log)
    install_composer(log)
    create_base(php, log)
    log("Kurulum tamamlandı.")
