@echo off
REM Abre el programa (desde el codigo fuente) con DATOS DE PRUEBA en demo_datos.
REM No toca los datos reales. Para empezar de cero:  probar_demo.bat --nueva-prueba
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe main.py --prueba %*
) else (
    python main.py --prueba %*
)
