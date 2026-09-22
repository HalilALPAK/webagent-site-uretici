"""WebAgent.exe'yi üretir (PyInstaller, tek dosya).

Kullanım:  pip install pyinstaller pywebview
           python build_exe.py            → dist/WebAgent.exe
PHP, Composer ve Laravel temel projesi .exe'ye gömülmez (≈150 MB); ilk açılışta kurulum ekranı indirir.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
SEP = ";" if sys.platform == "win32" else ":"


def make_icon() -> Path:
    from PIL import Image, ImageDraw
    BUILD.mkdir(exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, size - 8, size - 8), radius=56, fill=(17, 24, 39))
    c, r = size // 2, 78
    d.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=(165, 180, 252))
    d.polygon([(c, c - r + 34), (c + r - 34, c), (c, c + r - 34), (c - r + 34, c)], fill=(79, 70, 229))
    path = BUILD / "webagent.ico"
    img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return path


def main() -> None:
    import PyInstaller.__main__

    for junk in [ROOT / "site_engine" / "site.db", *ROOT.rglob("__pycache__")]:
        if junk.is_dir():
            shutil.rmtree(junk, ignore_errors=True)
        elif junk.exists():
            junk.unlink()

    data = [
        ("webagent/web/templates", "webagent/web/templates"),
        ("webagent/web/static", "webagent/web/static"),
        ("laravel_stubs", "laravel_stubs"),
        ("site_engine", "site_engine"),
        ("DESIGN.md", "."),
    ]
    args = [
        str(ROOT / "desktop.py"),
        "--name", "WebAgent",
        "--onefile",
        "--noconsole",
        "--noconfirm",
        "--clean",
        "--icon", str(make_icon()),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
        "--collect-submodules", "uvicorn",
        "--collect-submodules", "webagent",
        "--collect-submodules", "anthropic",
        "--collect-data", "anthropic",
        "--hidden-import", "multipart",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "torch",
        "--exclude-module", "pandas",
        "--exclude-module", "numpy",
        "--exclude-module", "IPython",
    ]
    for src, dest in data:
        args += ["--add-data", f"{ROOT / src}{SEP}{dest}"]
    PyInstaller.__main__.run(args)
    exe = ROOT / "dist" / ("WebAgent.exe" if sys.platform == "win32" else "WebAgent")
    print(f"\nHazır: {exe}  ({exe.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
