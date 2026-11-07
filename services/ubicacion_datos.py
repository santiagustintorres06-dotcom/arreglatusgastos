"""Detecta otras copias del programa con datos en la misma PC.

Problema real: si hay dos carpetas del programa (por ejemplo una en el
Escritorio y otra en Descargas), cada una tiene su propia base de datos.
Lo cargado en una no aparece al abrir la otra y parece que "no se guardó".
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

NOMBRE_AVISOS_IGNORADOS = "avisos_ignorados.txt"


@dataclass
class CopiaDatos:
    ruta_bd: Path
    cantidad_gastos: int
    cantidad_consumos: int
    modificada: datetime

    @property
    def carpeta_programa(self) -> Path:
        return self.ruta_bd.parent.parent

    @property
    def tiene_datos(self) -> bool:
        return self.cantidad_gastos > 0 or self.cantidad_consumos > 0


def contar_datos(ruta_bd: Path) -> tuple[int, int]:
    """(gastos, consumos de tarjeta) de una base, abriéndola en solo lectura."""
    try:
        conn = sqlite3.connect(f"file:{ruta_bd.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0, 0
    try:
        tablas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        gastos = conn.execute("SELECT COUNT(*) FROM gasto").fetchone()[0] if "gasto" in tablas else 0
        consumos = (
            conn.execute("SELECT COUNT(*) FROM consumo_tarjeta").fetchone()[0]
            if "consumo_tarjeta" in tablas
            else 0
        )
        return gastos, consumos
    except sqlite3.Error:
        return 0, 0
    finally:
        conn.close()


def carpetas_habituales() -> list[Path]:
    """Lugares donde un usuario suele dejar la carpeta del programa."""
    home = Path.home()
    candidatas = [home / "Desktop", home / "Escritorio", home / "Documents", home / "Documentos", home / "Downloads", home / "Descargas"]
    onedrive = os.environ.get("OneDrive")
    if onedrive:
        candidatas += [Path(onedrive) / "Desktop", Path(onedrive) / "Escritorio", Path(onedrive) / "Documents", Path(onedrive) / "Documentos"]
    vistas: list[Path] = []
    for c in candidatas:
        try:
            if c.is_dir() and c.resolve() not in vistas:
                vistas.append(c.resolve())
        except OSError:
            continue
    return vistas


def buscar_bases(raices: list[Path], profundidad_max: int = 3) -> list[Path]:
    """Busca archivos data/gastos.db hasta cierta profundidad (sin recorrer todo el disco)."""
    encontradas: list[Path] = []
    ignorar = {".git", ".venv", "node_modules", "__pycache__", "AppData", "backups", "_internal", "build"}

    def recorrer(carpeta: Path, nivel: int) -> None:
        candidata = carpeta / "data" / "gastos.db"
        if candidata.is_file():
            encontradas.append(candidata.resolve())
        if nivel >= profundidad_max:
            return
        try:
            hijos = [h for h in carpeta.iterdir() if h.is_dir() and h.name not in ignorar and not h.name.startswith(".")]
        except OSError:
            return
        for h in hijos:
            recorrer(h, nivel + 1)

    for raiz in raices:
        recorrer(raiz, 0)
    # Sin repetidos, manteniendo el orden
    return list(dict.fromkeys(encontradas))


def otras_copias_con_datos(bd_actual: Path, raices: list[Path] | None = None) -> list[CopiaDatos]:
    """Otras bases del programa (distintas de la actual) que tienen datos cargados."""
    raices = carpetas_habituales() if raices is None else raices
    try:
        actual = bd_actual.resolve()
    except OSError:
        actual = bd_actual
    copias: list[CopiaDatos] = []
    for ruta in buscar_bases(raices):
        if ruta == actual:
            continue
        gastos, consumos = contar_datos(ruta)
        try:
            modificada = datetime.fromtimestamp(ruta.stat().st_mtime)
        except OSError:
            continue
        copia = CopiaDatos(ruta, gastos, consumos, modificada)
        if copia.tiene_datos:
            copias.append(copia)
    return sorted(copias, key=lambda c: c.modificada, reverse=True)


def leer_ignorados(directorio_datos: Path) -> set[str]:
    archivo = directorio_datos / NOMBRE_AVISOS_IGNORADOS
    try:
        return {l.strip() for l in archivo.read_text(encoding="utf-8").splitlines() if l.strip()}
    except OSError:
        return set()


def guardar_ignorados(directorio_datos: Path, rutas: set[str]) -> None:
    try:
        (directorio_datos / NOMBRE_AVISOS_IGNORADOS).write_text("\n".join(sorted(rutas)), encoding="utf-8")
    except OSError:
        pass
