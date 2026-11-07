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

CREATE TABLE IF NOT EXISTS resumen_tarjeta_mes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tarjeta_id INTEGER NOT NULL REFERENCES tarjeta(id),
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    gasto_id INTEGER NOT NULL REFERENCES gasto(id),
    total_cent INTEGER NOT NULL,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tarjeta_id, anio, mes)
);

CREATE INDEX IF NOT EXISTS idx_resumen_tarjeta_mes ON resumen_tarjeta_mes(tarjeta_id, anio, mes);

-- Fechas de cierre/vencimiento corregidas a mano para un resumen puntual
-- (los bancos a veces corren el cierre unos días). mes = mes de cierre.
CREATE TABLE IF NOT EXISTS ajuste_resumen_tarjeta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tarjeta_id INTEGER NOT NULL REFERENCES tarjeta(id),
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    fecha_cierre TEXT NOT NULL,
    fecha_vencimiento TEXT NOT NULL,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tarjeta_id, anio, mes)
);
