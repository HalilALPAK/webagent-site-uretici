"""Web Agent masaüstü uygulaması (WebAgent.exe'nin giriş noktası).

Arka planda yerel sunucuyu başlatır ve arayüzü kendi penceresinde (Edge WebView2) açar.
WebView2 yoksa varsayılan tarayıcıda açar. Pencere kapanınca sunucu ve çalışan siteler durdurulur.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import traceback


def _redirect_output() -> None:
    """--noconsole paketlemede stdout/stderr None olur; günlükleri dosyaya yaz."""
    if sys.stdout is None or sys.stderr is None:
        from webagent.config import HOME_DIR
        HOME_DIR.mkdir(parents=True, exist_ok=True)
        log = open(HOME_DIR / "webagent.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def _isolate_child_processes() -> None:
    """PyInstaller'ın tek dosya önyükleyicisi SetDllDirectory ile geçici klasörünü (_MEIPASS) DLL arama yoluna
    ekler ve bu ayar alt süreçlere de geçer. Böylece PHP kendi VCRUNTIME140.dll'i yerine paketteki eski sürümü
    yükleyip çöker. Alt süreçler (PHP, Composer, Claude Code) temiz bir DLL arama yoluyla başlasın."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryW(None)
    meipass = getattr(sys, "_MEIPASS", "")
    os.environ["PATH"] = os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                                         if p and os.path.normcase(p) != os.path.normcase(meipass))


def _free_port(preferred: int = 8765) -> int:
    for port in (preferred, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("Boş port bulunamadı")


def main() -> None:
    _redirect_output()
    _isolate_child_processes()
    import uvicorn

    from webagent.web.app import app

    port = _free_port(int(os.environ.get("WEBAGENT_PORT", "8765")))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", log_config=None))
    threading.Thread(target=server.run, daemon=True, name="webagent-server").start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    url = f"http://127.0.0.1:{port}/"

    if os.environ.get("WEBAGENT_HEADLESS"):  # test/sunucu modu: pencere açmadan yalnızca sunucu
        print(f"Web Agent: {url}", flush=True)
        while not server.should_exit:
            time.sleep(1)
        return

    try:
        import webview
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.create_window("Web Agent — Rakip analiziyle site üretimi", url, width=1360, height=900,
                              min_size=(960, 640), text_select=True)
        webview.start()
    except Exception:
        traceback.print_exc()
        import webbrowser
        webbrowser.open(url)
        try:
            while True:  # tarayıcı modunda süreç açık kalsın
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    finally:
        server.should_exit = True
        time.sleep(0.5)
        from webagent.web.app import RUNNING
        for proc, _ in RUNNING.values():
            proc.terminate()
        os._exit(0)


if __name__ == "__main__":
    main()
