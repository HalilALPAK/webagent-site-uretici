"""Laravel üretimi için gereken araçları komut satırından kurar (uygulama bunu ilk açılışta kendisi de yapar).

Kullanım:  python setup_laravel.py
"""
from webagent.setup_tools import SetupError, setup_all

if __name__ == "__main__":
    try:
        setup_all()
    except SetupError as e:
        raise SystemExit(str(e))
    print("\nTamam. Artık `python run.py` ile site üretebilirsiniz.")
