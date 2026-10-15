@echo off
echo ========================================================
echo   Compilando Organizador de Gastos Familiares (.exe)
echo ========================================================
echo.

REM Activar entorno virtual
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Instalar pyinstaller si no estuviera instalado
python -m pip install pyinstaller

REM Generar ejecutable portable con PyInstaller
echo Compilando aplicacion con PyInstaller (modo onedir)...
pyinstaller --noconfirm --windowed --name GastosFamilia --add-data "db/schema.sql;db" main.py

echo.
echo ========================================================
echo   Compilacion completada con exito!
echo   La carpeta portable se encuentra en: dist\GastosFamilia\
echo   Puedes copiar esa carpeta completa a un pendrive o PC.
echo ========================================================
echo.
pause
