"""Laravel üretimi için gereken araçları kurar (ilk açılışta bir kez).

- Taşınabilir PHP 8.4 (windows.php.net, SHA-256 doğrulamalı) → tools/php
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

from .config import LARAVEL_BASE, TOOLS_DIR

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


def install_php(log: Log) -> str:
    found = shutil.which("php")
    if found:
        log(f"PHP bulundu: {found}")
        return found
    exe = PHP_DIR / "php.exe"
    if exe.exists():
        return str(exe)
    if os.name != "nt":
        raise SetupError("PHP bulunamadı. Paket yöneticinizle PHP 8.3+ kurun (sqlite, intl, zip, gd eklentileriyle).")

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
