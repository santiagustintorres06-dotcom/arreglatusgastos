import sqlite3
from models.tarjeta import Tarjeta, ConsumoTarjeta


def _fila_a_tarjeta(row: sqlite3.Row) -> Tarjeta:
    return Tarjeta(
        id=row["id"],
        nombre=row["nombre"],
        dia_cierre=row["dia_cierre"],
        dia_vencimiento=row["dia_vencimiento"],
        limite_cent=row["limite_cent"],
        activa=bool(row["activa"]),
        creado_en=row["creado_en"],
    )


def _fila_a_consumo(row: sqlite3.Row) -> ConsumoTarjeta:
    return ConsumoTarjeta(
        id=row["id"],
        tarjeta_id=row["tarjeta_id"],
        fecha_compra=row["fecha_compra"],
        descripcion=row["descripcion"],
        monto_total_cent=row["monto_total_cent"],
        monto_cuota_cent=row["monto_cuota_cent"],
        cantidad_cuotas=row["cantidad_cuotas"],
        cuotas_pagadas=row["cuotas_pagadas"],
        precio_contado_cent=row["precio_contado_cent"],
        estado=row["estado"],
        gasto_id_planilla=row["gasto_id_planilla"],
        creado_en=row["creado_en"],
    )


class TarjetaRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def listar(self, solo_activas: bool = False) -> list[Tarjeta]:
        sql = "SELECT * FROM tarjeta"
        if solo_activas:
            sql += " WHERE activa = 1"
        sql += " ORDER BY nombre"
        rows = self._conn.execute(sql).fetchall()
        return [_fila_a_tarjeta(r) for r in rows]

    def obtener(self, id_tarjeta: int) -> Tarjeta | None:
        row = self._conn.execute(
            "SELECT * FROM tarjeta WHERE id = ?", (id_tarjeta,)
        ).fetchone()
        return _fila_a_tarjeta(row) if row else None

    def crear(self, t: Tarjeta) -> int:
        cur = self._conn.execute(
            """INSERT INTO tarjeta (nombre, dia_cierre, dia_vencimiento, limite_cent, activa)
               VALUES (?, ?, ?, ?, ?)""",
            (t.nombre, t.dia_cierre, t.dia_vencimiento, t.limite_cent, int(t.activa)),
        )
        self._conn.commit()
        return cur.lastrowid

    def actualizar(self, t: Tarjeta) -> None:
        self._conn.execute(
            """UPDATE tarjeta SET nombre=?, dia_cierre=?, dia_vencimiento=?,
               limite_cent=?, activa=? WHERE id=?""",
            (t.nombre, t.dia_cierre, t.dia_vencimiento, t.limite_cent, int(t.activa), t.id),
        )
        self._conn.commit()

    def desactivar(self, id_tarjeta: int) -> None:
        self._conn.execute(
            "UPDATE tarjeta SET activa = 0 WHERE id = ?", (id_tarjeta,)
        )
        self._conn.commit()

    # --- Consumos ---

    def listar_consumos(
        self,
        tarjeta_id: int | None = None,
        estado: str | None = None,
    ) -> list[ConsumoTarjeta]:
        where = ["1=1"]
        params: list = []
        if tarjeta_id is not None:
            where.append("tarjeta_id = ?")
            params.append(tarjeta_id)
        if estado is not None:
            where.append("estado = ?")
            params.append(estado)
        sql = (
            "SELECT * FROM consumo_tarjeta WHERE "
            + " AND ".join(where)
            + " ORDER BY fecha_compra DESC"
        )
        rows = self._conn.execute(sql, params).fetchall()
        return [_fila_a_consumo(r) for r in rows]

    def obtener_consumo(self, id_consumo: int) -> ConsumoTarjeta | None:
        row = self._conn.execute(
            "SELECT * FROM consumo_tarjeta WHERE id = ?", (id_consumo,)
        ).fetchone()
        return _fila_a_consumo(row) if row else None

    def crear_consumo(self, c: ConsumoTarjeta) -> int:
        cur = self._conn.execute(
            """INSERT INTO consumo_tarjeta
               (tarjeta_id, fecha_compra, descripcion, monto_total_cent,
                monto_cuota_cent, cantidad_cuotas, cuotas_pagadas,
                precio_contado_cent, estado, gasto_id_planilla)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                c.tarjeta_id,
                c.fecha_compra,
                c.descripcion,
                c.monto_total_cent,
                c.monto_cuota_cent,
                c.cantidad_cuotas,
                c.cuotas_pagadas,
                c.precio_contado_cent,
                c.estado,
                c.gasto_id_planilla,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def actualizar_consumo(self, c: ConsumoTarjeta) -> None:
        self._conn.execute(
            """UPDATE consumo_tarjeta SET
               tarjeta_id=?, fecha_compra=?, descripcion=?, monto_total_cent=?,
               monto_cuota_cent=?, cantidad_cuotas=?, cuotas_pagadas=?,
               precio_contado_cent=?, estado=?, gasto_id_planilla=?
               WHERE id=?""",
            (
                c.tarjeta_id,
                c.fecha_compra,
                c.descripcion,
                c.monto_total_cent,
                c.monto_cuota_cent,
                c.cantidad_cuotas,
                c.cuotas_pagadas,
                c.precio_contado_cent,
                c.estado,
                c.gasto_id_planilla,
                c.id,
            ),
        )
        self._conn.commit()

    def marcar_cuota_pagada(self, id_consumo: int) -> None:
        self._conn.execute(
            """UPDATE consumo_tarjeta
               SET cuotas_pagadas = MIN(cuotas_pagadas + 1, cantidad_cuotas),
                   estado = CASE
                       WHEN cuotas_pagadas + 1 >= cantidad_cuotas THEN 'finalizado'
                       ELSE estado
                   END
               WHERE id = ? AND estado = 'activo'""",
            (id_consumo,),
        )
        self._conn.commit()

    def deshacer_ultima_cuota(self, id_consumo: int) -> None:
        self._conn.execute(
            """UPDATE consumo_tarjeta
               SET cuotas_pagadas = MAX(cuotas_pagadas - 1, 0),
                   estado = 'activo'
               WHERE id = ?""",
            (id_consumo,),
        )
        self._conn.commit()

    def cancelar_consumo(self, id_consumo: int) -> None:
        self._conn.execute(
            "UPDATE consumo_tarjeta SET estado = 'cancelado' WHERE id = ?",
            (id_consumo,),
        )
        self._conn.commit()

    def registrar_gasto_planilla(self, id_consumo: int, gasto_id: int) -> None:
        self._conn.execute(
            "UPDATE consumo_tarjeta SET gasto_id_planilla = ? WHERE id = ?",
            (gasto_id, id_consumo),
        )
        self._conn.commit()

    def consumos_por_mes(self, anio: int, mes: int) -> list[ConsumoTarjeta]:
        """Retorna consumos cuya cuota correspondiente vence en el mes dado."""
        rows = self._conn.execute(
            "SELECT * FROM consumo_tarjeta WHERE estado != 'cancelado'"
        ).fetchall()
        return [_fila_a_consumo(r) for r in rows]
