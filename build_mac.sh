#!/usr/bin/env bash
# Crea dist/MixaPozioni.app (app per macOS). Richiede Python 3.10+.
# Nota: su macOS PyInstaller consiglia --onedir per le .app (--onefile + --windowed
# e' deprecato e piu' lento all'avvio): l'.app e' comunque un unico "file" per l'utente.
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --clean --onedir --windowed --name MixaPozioni main.py
echo
echo "Fatto! L'app e' in: dist/MixaPozioni.app"
