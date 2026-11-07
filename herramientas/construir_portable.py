"""Genera la versión portable (dist/GastosFamilia) SIN perder datos.

PyInstaller borra por completo la carpeta dist/GastosFamilia antes de
generarla de nuevo, incluida data/ (la base y los respaldos). Si alguien ya
estaba usando ese portable, perdía todo. Este script:

1. Frena si el programa está abierto (archivos en uso).
2. Copia dist/GastosFamilia/data a respaldos_portable/data_FECHA_HORA.
3. Genera el portable con GastosFamilia.spec.
4. Vuelve a poner los datos en dist/GastosFamilia/data.
5. Agrega el instructivo y el acceso al modo prueba.

Uso: build.bat  (o  .venv\\Scripts\\python.exe herramientas\\construir_portable.py)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist" / "GastosFamilia"
RESPALDOS = RAIZ / "respaldos_portable"


def programa_abierto() -> bool:
    try:
        salida = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq GastosFamilia.exe"],
            capture_output=True, text=True, check=False,
        ).stdout
    except OSError:
        return False
    return "GastosFamilia.exe" in salida


def respaldar_datos() -> Path | None:
    datos = DIST / "data"
    if not datos.is_dir() or not any(datos.iterdir()):
        return None
    destino = RESPALDOS / f"data_{datetime.now():%Y%m%d_%H%M%S}"
    shutil.copytree(datos, destino)
    return destino


def main() -> int:
    if programa_abierto():
        print("\n*** El programa GastosFamilia esta abierto. Cerralo y volve a intentar. ***\n")
        return 1

    respaldo = respaldar_datos()
    if respaldo:
        print(f"Datos existentes copiados a: {respaldo}")

    print("Generando el portable con PyInstaller...")
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "GastosFamilia.spec"], cwd=RAIZ
    )
    if r.returncode != 0:
        print("\n*** Fallo la compilacion. ***")
        if respaldo:
            print(f"Los datos estan a salvo en: {respaldo}")
        return r.returncode

    if respaldo:
        shutil.copytree(respaldo, DIST / "data", dirs_exist_ok=True)
        print("Datos restaurados en dist\\GastosFamilia\\data")

    shutil.copy2(RAIZ / "README_INSTALACION.txt", DIST / "README_INSTALACION.txt")
    shutil.copy2(RAIZ / "herramientas" / "Probar con datos de ejemplo.bat", DIST / "Probar con datos de ejemplo.bat")

    print("\nListo. Portable en:", DIST)
    print("Copia la carpeta GastosFamilia COMPLETA a donde se vaya a usar (ej. Escritorio)")
    print("y usa siempre esa copia. No uses el programa directamente desde 'dist'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
