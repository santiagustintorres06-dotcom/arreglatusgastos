from datetime import date
from pathlib import Path
import shutil
import sqlite3

from config import CATEGORIAS_POR_DEFECTO
from paths import BACKUP_DIR, DB_PATH, asegurar_directorios

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def obtener_conexion(ruta_bd: Path | str | None = None) -> sqlite3.Connection:
    """Crea y retorna una conexión a la base de datos SQLite con claves foráneas activadas."""
    if ruta_bd is None:
        asegurar_directorios()
        ruta_bd = DB_PATH

    conn = sqlite3.connect(ruta_bd)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


ESQUEMA_SQL_DEFAULT = """
CREATE TABLE IF NOT EXISTS categoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    color TEXT,
    activa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS miembro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS gasto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    monto_cent INTEGER NOT NULL CHECK (monto_cent > 0),
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    miembro_id INTEGER REFERENCES miembro(id),
    descripcion TEXT,
    medio_pago TEXT,
    cuotas TEXT DEFAULT '',
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gasto_fecha ON gasto(fecha);

CREATE TABLE IF NOT EXISTS tarjeta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    dia_cierre INTEGER NOT NULL CHECK (dia_cierre BETWEEN 1 AND 31),
    dia_vencimiento INTEGER NOT NULL CHECK (dia_vencimiento BETWEEN 1 AND 31),
    limite_cent INTEGER,
    activa INTEGER NOT NULL DEFAULT 1,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS consumo_tarjeta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tarjeta_id INTEGER NOT NULL REFERENCES tarjeta(id),
    fecha_compra TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    monto_total_cent INTEGER NOT NULL CHECK (monto_total_cent > 0),
    monto_cuota_cent INTEGER NOT NULL CHECK (monto_cuota_cent > 0),
    cantidad_cuotas INTEGER NOT NULL CHECK (cantidad_cuotas >= 1),
    cuotas_pagadas INTEGER NOT NULL DEFAULT 0,
    precio_contado_cent INTEGER,
    estado TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'finalizado', 'cancelado')),
    gasto_id_planilla INTEGER REFERENCES gasto(id),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consumo_tarjeta_id ON consumo_tarjeta(tarjeta_id);
CREATE INDEX IF NOT EXISTS idx_consumo_estado ON consumo_tarjeta(estado);
"""


def inicializar_bd(conn: sqlite3.Connection) -> None:
    """Ejecuta el script DDL inicial y carga categorías por defecto si la base está vacía."""
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
    else:
        schema_sql = ESQUEMA_SQL_DEFAULT

    conn.executescript(schema_sql)

    cursor = conn.cursor()

    # Migración automática de columna cuotas si la base ya existía
    try:
        cursor.execute("ALTER TABLE gasto ADD COLUMN cuotas TEXT DEFAULT '';")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Migración/actualización automática de categoría Transporte -> Vehículo
    cursor.execute(
        "UPDATE categoria SET nombre = 'Vehículo' WHERE nombre = 'Transporte';"
    )
    conn.commit()

    # Verificar si ya existen categorías
    cursor.execute("SELECT COUNT(*) AS total FROM categoria;")
    row = cursor.fetchone()
    if row and row["total"] == 0:
        cursor.executemany(
            "INSERT INTO categoria (nombre, color, activa) VALUES (?, ?, 1);",
            CATEGORIAS_POR_DEFECTO,
        )
        conn.commit()


def realizar_backup(
    ruta_bd: Path | None = None,
    directorio_backups: Path | None = None,
    max_backups: int = 30,
) -> Path | None:
    """Realiza una copia diaria de la base de datos si existe, conservando solo los últimos max_backups."""
    if ruta_bd is None:
        ruta_bd = DB_PATH
    if directorio_backups is None:
        directorio_backups = BACKUP_DIR

    if not isinstance(ruta_bd, Path):
        ruta_bd = Path(ruta_bd)

    # Si la base de datos no existe o está en memoria, no realizamos copia
    if not ruta_bd.exists() or str(ruta_bd) == ":memory:":
        return None

    directorio_backups.mkdir(parents=True, exist_ok=True)
    fecha_hoy = date.today().strftime("%Y%m%d")
    archivo_destino = directorio_backups / f"gastos_{fecha_hoy}.db"

    # Si ya se hizo backup hoy, no lo duplicamos
    if not archivo_destino.exists():
        shutil.copy2(ruta_bd, archivo_destino)

    # Rotación: conservar solo los últimos max_backups ordenados por fecha
    backups_existentes = sorted(
        directorio_backups.glob("gastos_*.db"),
        key=lambda p: p.stat().st_mtime,
    )
    if len(backups_existentes) > max_backups:
        a_eliminar = backups_existentes[:-max_backups]
        for viejo in a_eliminar:
            try:
                viejo.unlink()
            except OSError:
                pass

    return archivo_destino
