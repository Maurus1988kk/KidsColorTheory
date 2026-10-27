#!/usr/bin/env bash
# Crea dist/MixaPozioni (eseguibile unico). Richiede Python 3.10+.
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MixaPozioni main.py
echo
echo "Fatto! L'eseguibile e' in: dist/MixaPozioni"
