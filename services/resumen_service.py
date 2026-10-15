import calendar
from datetime import date
from decimal import Decimal

from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo


class ResumenService:
    """Calcula métricas agregadas del mes: totales, promedios y día de mayor gasto."""

    def __init__(self, gasto_repo: GastoRepo, categoria_repo: CategoriaRepo):
        self.gasto_repo = gasto_repo
        self.categoria_repo = categoria_repo

    def totales_por_dia(self, anio: int, mes: int) -> dict[date, Decimal]:
        """Retorna un diccionario {fecha: total_gastado} para cada día con gastos en el mes."""
        return self.gasto_repo.totales_por_dia(anio, mes)

    def total_mes(self, anio: int, mes: int) -> Decimal:
        """Calcula el total absoluto gastado en el mes."""
        totales_dia = self.totales_por_dia(anio, mes)
        return sum(totales_dia.values(), Decimal("0.00"))

    def totales_por_categoria(self, anio: int, mes: int) -> list[dict]:
        """Calcula los gastos por categoría enriquecidos con nombre, color y porcentaje del total."""
        totales_map = self.gasto_repo.totales_por_categoria(anio, mes)
        total_general = sum(totales_map.values(), Decimal("0.00"))

        categorias_activas = self.categoria_repo.listar(solo_activas=False)
        cat_by_id = {c.id: c for c in categorias_activas}

        resumen = []
        for cat_id, subtotal in totales_map.items():
            cat = cat_by_id.get(cat_id)
            porcentaje = (
                ((subtotal / total_general) * 100).quantize(Decimal("0.1"))
                if total_general > 0
                else Decimal("0.0")
            )
            resumen.append(
                {
                    "categoria_id": cat_id,
                    "nombre": cat.nombre if cat else "Desconocida",
                    "color": cat.color if cat else "#7f8c8d",
                    "total": subtotal,
                    "porcentaje": porcentaje,
                }
            )

        # Ordenar de mayor a menor gasto
        resumen.sort(key=lambda x: x["total"], reverse=True)
        return resumen

    def promedio_diario(self, anio: int, mes: int) -> Decimal:
        """Calcula el promedio gastado por día en el mes."""
        total = self.total_mes(anio, mes)
        if total == 0:
            return Decimal("0.00")

        dias_mes = calendar.monthrange(anio, mes)[1]
        return (total / Decimal(dias_mes)).quantize(Decimal("0.01"))

    def dia_mayor_gasto(self, anio: int, mes: int) -> tuple[date | None, Decimal]:
        """Encuentra el día con mayor monto total gastado en el mes.
        Retorna (fecha, monto) o (None, Decimal('0.00')) si no hay gastos.
        """
        totales_dia = self.totales_por_dia(anio, mes)
        if not totales_dia:
            return None, Decimal("0.00")

        dia_pico = max(totales_dia.items(), key=lambda item: item[1])
        return dia_pico[0], dia_pico[1]
