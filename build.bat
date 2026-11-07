@echo off
echo ========================================================
echo   Generando Organizador de Gastos Familiares portable
echo   (los datos que ya existan en dist\GastosFamilia\data se conservan)
echo ========================================================
echo.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python -m pip install -q pyinstaller
python herramientas\construir_portable.py
echo.
pause
