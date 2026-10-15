import calendar
from datetime import date
from decimal import Decimal
import sqlite3

from models.gasto import Gasto


class GastoRepo:
    """Acceso a datos para la entidad Gasto (tabla gasto)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _fila_a_gasto(self, fila: sqlite3.Row) -> Gasto:
        fecha_obj = (
            date.fromisoformat(fila["fecha"])
            if isinstance(fila["fecha"], str)
            else fila["fecha"]
        )
        cuotas_val = fila["cuotas"] if "cuotas" in fila.keys() and fila["cuotas"] else ""
        return Gasto(
            id=fila["id"],
            fecha=fecha_obj,
            monto=Gasto.centavos_a_decimal(fila["monto_cent"]),
            categoria_id=fila["categoria_id"],
            miembro_id=fila["miembro_id"],
            descripcion=fila["descripcion"] or "",
            medio_pago=fila["medio_pago"] or "",
            cuotas=cuotas_val,
            creado_en=fila["creado_en"],
        )

    def _rango_mes(self, anio: int, mes: int) -> tuple[str, str]:
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        inicio = f"{anio:04d}-{mes:02d}-01"
        fin = f"{anio:04d}-{mes:02d}-{ultimo_dia:02d}"
        return inicio, fin

    def crear(self, gasto: Gasto) -> Gasto:
        cursor = self.conn.cursor()
        fecha_str = (
            gasto.fecha.isoformat()
            if isinstance(gasto.fecha, date)
            else str(gasto.fecha)
        )
        cursor.execute(
            """
            INSERT INTO gasto (fecha, monto_cent, categoria_id, miembro_id, descripcion, medio_pago, cuotas)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                fecha_str,
                gasto.monto_cent,
                gasto.categoria_id,
                gasto.miembro_id,
                gasto.descripcion.strip() if gasto.descripcion else "",
                gasto.medio_pago.strip() if gasto.medio_pago else "",
                gasto.cuotas.strip() if gasto.cuotas else "",
            ),
        )
        gasto.id = cursor.lastrowid
        self.conn.commit()
        return gasto

    def actualizar(self, gasto: Gasto) -> None:
        if gasto.id is None:
            raise ValueError("No se puede actualizar un gasto sin ID.")
        cursor = self.conn.cursor()
        fecha_str = (
            gasto.fecha.isoformat()
            if isinstance(gasto.fecha, date)
            else str(gasto.fecha)
        )
        cursor.execute(
            """
            UPDATE gasto
            SET fecha = ?, monto_cent = ?, categoria_id = ?, miembro_id = ?, descripcion = ?, medio_pago = ?, cuotas = ?
            WHERE id = ?;
            """,
            (
                fecha_str,
                gasto.monto_cent,
                gasto.categoria_id,
                gasto.miembro_id,
                gasto.descripcion.strip() if gasto.descripcion else "",
                gasto.medio_pago.strip() if gasto.medio_pago else "",
                gasto.cuotas.strip() if gasto.cuotas else "",
                gasto.id,
            ),
        )
        self.conn.commit()

    def eliminar(self, id_gasto: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM gasto WHERE id = ?;", (id_gasto,))
        self.conn.commit()

    def obtener_por_id(self, id_gasto: int) -> Gasto | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, fecha, monto_cent, categoria_id, miembro_id, descripcion, medio_pago, cuotas, creado_en
            FROM gasto
            WHERE id = ?;
            """,
            (id_gasto,),
        )
        fila = cursor.fetchone()
        if not fila:
            return None
        return self._fila_a_gasto(fila)

    def listar_por_mes(
        self,
        anio: int,
        mes: int,
        categoria_id: int | None = None,
        miembro_id: int | None = None,
    ) -> list[Gasto]:
        inicio, fin = self._rango_mes(anio, mes)
        query = [
            "SELECT id, fecha, monto_cent, categoria_id, miembro_id, descripcion, medio_pago, cuotas, creado_en",
            "FROM gasto",
            "WHERE fecha >= ? AND fecha <= ?",
        ]
        params: list[object] = [inicio, fin]

        if categoria_id is not None:
            query.append("AND categoria_id = ?")
            params.append(categoria_id)

        if miembro_id is not None:
            query.append("AND miembro_id = ?")
            params.append(miembro_id)

        query.append("ORDER BY fecha ASC, id ASC;")

        cursor = self.conn.cursor()
        cursor.execute(" ".join(query), params)
        filas = cursor.fetchall()
        return [self._fila_a_gasto(r) for r in filas]

    def listar_por_fecha(self, fecha: date | str) -> list[Gasto]:
        fecha_str = fecha.isoformat() if isinstance(fecha, date) else str(fecha)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, fecha, monto_cent, categoria_id, miembro_id, descripcion, medio_pago, cuotas, creado_en
            FROM gasto
            WHERE fecha = ?
            ORDER BY id ASC;
            """,
            (fecha_str,),
        )
        filas = cursor.fetchall()
        return [self._fila_a_gasto(r) for r in filas]

    def totales_por_dia(self, anio: int, mes: int) -> dict[date, Decimal]:
        """Calcula el total gastado agrupado por fecha para el mes dado."""
        inicio, fin = self._rango_mes(anio, mes)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT fecha, SUM(monto_cent) AS total_cent
            FROM gasto
            WHERE fecha >= ? AND fecha <= ?
            GROUP BY fecha
            ORDER BY fecha ASC;
            """,
            (inicio, fin),
        )
        filas = cursor.fetchall()
        resultado: dict[date, Decimal] = {}
        for r in filas:
            f = date.fromisoformat(r["fecha"])
            resultado[f] = Gasto.centavos_a_decimal(r["total_cent"])
        return resultado

    def totales_por_categoria(self, anio: int, mes: int) -> dict[int, Decimal]:
        """Calcula el total gastado agrupado por categoria_id para el mes dado."""
        inicio, fin = self._rango_mes(anio, mes)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT categoria_id, SUM(monto_cent) AS total_cent
            FROM gasto
            WHERE fecha >= ? AND fecha <= ?
            GROUP BY categoria_id;
            """,
            (inicio, fin),
        )
        filas = cursor.fetchall()
        return {r["categoria_id"]: Gasto.centavos_a_decimal(r["total_cent"]) for r in filas}
