@echo off
REM Crea dist\MixaPozioni.exe (file unico, senza console). Richiede Python 3.10+.
setlocal
cd /d "%~dp0"
if not exist .venv (
    py -3 -m venv .venv || goto :errore
)
call .venv\Scripts\activate.bat || goto :errore
python -m pip install --upgrade pip || goto :errore
python -m pip install -r requirements-dev.txt || goto :errore
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MixaPozioni main.py || goto :errore
echo.
echo Fatto! L'eseguibile e' in: dist\MixaPozioni.exe
exit /b 0
:errore
echo.
echo ERRORE durante la build.
exit /b 1
