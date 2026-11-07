@echo off
REM Abre el programa con DATOS DE PRUEBA (carpeta demo_datos). No toca los datos reales.
REM Para empezar de cero con la prueba:  probar_demo.bat --nueva
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe herramientas\cargar_demo.py %*
) else (
    python herramientas\cargar_demo.py %*
)
