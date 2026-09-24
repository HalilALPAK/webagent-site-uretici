#!/usr/bin/env bash
# Web Agent — Linux/macOS kurulum ve başlatma betiği.
#
#   ./webagent.sh          kurulumu tamamlar ve uygulamayı açar
#   ./webagent.sh build    tek dosyalık çalıştırılabilir üretir (dist/WebAgent-linux-<mimari>)
#
# Hazır ikili dosya dağıtımınızda çalışmıyorsa (eski glibc, farklı mimari) bu betiği kullanın.
set -euo pipefail
cd "$(dirname "$0")"

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 veya üstü gerekiyor. Kurun:  sudo apt install python3 python3-venv" >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Sanal ortam hazırlanıyor…"
  "$PY" -m venv .venv 2>/dev/null || {
    # python3-venv paketi eksikse pip'i elle getir
    "$PY" -m venv --without-pip .venv
    curl -fsSL https://bootstrap.pypa.io/get-pip.py -o .venv/get-pip.py
    .venv/bin/python .venv/get-pip.py -q
    rm -f .venv/get-pip.py
  }
fi
.venv/bin/python -m pip install -q --upgrade pip
echo "Python paketleri kuruluyor…"
.venv/bin/python -m pip install -q -r requirements.txt

if [ "${1:-run}" = "build" ]; then
  .venv/bin/python -m pip install -q pyinstaller
  exec .venv/bin/python build_exe.py
fi

# Pencere desteği: GTK/WebKit varsa uygulama kendi penceresinde açılır, yoksa tarayıcıda
if .venv/bin/python -c 'import gi' 2>/dev/null; then
  .venv/bin/python -m pip install -q pywebview || true
fi

if ! command -v php >/dev/null 2>&1; then
  echo "Not: PHP kurulu değil. Site üretimi için gerekir:"
  echo "  sudo apt install -y php-cli php-sqlite3 php-curl php-mbstring php-xml php-zip php-gd php-intl"
fi

exec .venv/bin/python desktop.py
