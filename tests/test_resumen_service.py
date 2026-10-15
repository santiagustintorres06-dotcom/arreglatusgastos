from datetime import date
from decimal import Decimal
import pytest

from models.gasto import Gasto
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from services.resumen_service import ResumenService


def test_resumen_service_metricas_completas(
    resumen_service: ResumenService,
    gasto_repo: GastoRepo,
    categoria_repo: CategoriaRepo,
):
    super_cat = categoria_repo.obtener_por_nombre("Supermercado")
    servicios_cat = categoria_repo.obtener_por_nombre("Servicios")

    # Mes vacío
    assert resumen_service.total_mes(2026, 5) == Decimal("0.00")
    assert resumen_service.promedio_diario(2026, 5) == Decimal("0.00")
    dia_vacio, monto_vacio = resumen_service.dia_mayor_gasto(2026, 5)
    assert dia_vacio is None
    assert monto_vacio == Decimal("0.00")

    # Cargar gastos en Octubre 2026
    # Día 5: $2.000 (Supermercado)
    gasto_repo.crear(
        Gasto(
            fecha=date(2026, 10, 5),
            monto=Decimal("2000.00"),
            categoria_id=super_cat.id,
        )
    )
    # Día 10: $3.000 (Supermercado) + $1.000 (Servicios) = Total día $4.000
    gasto_repo.crear(
        Gasto(
            fecha=date(2026, 10, 10),
            monto=Decimal("3000.00"),
            categoria_id=super_cat.id,
        )
    )
    gasto_repo.crear(
        Gasto(
            fecha=date(2026, 10, 10),
            monto=Decimal("1000.00"),
            categoria_id=servicios_cat.id,
        )
    )

    # 1. Total del mes: 2000 + 3000 + 1000 = 6000
    total = resumen_service.total_mes(2026, 10)
    assert total == Decimal("6000.00")

    # 2. Promedio diario: 6000 / 31 días = 193.55
    promedio = resumen_service.promedio_diario(2026, 10)
    assert promedio == Decimal("193.55")

    # 3. Día de mayor gasto: Día 10 con $4000
    dia_pico, monto_pico = resumen_service.dia_mayor_gasto(2026, 10)
    assert dia_pico == date(2026, 10, 10)
    assert monto_pico == Decimal("4000.00")

    # 4. Resumen por categoría ordenado por mayor gasto
    resumen_cat = resumen_service.totales_por_categoria(2026, 10)
    assert len(resumen_cat) == 2
    # El primero debe ser Supermercado con 5000 (83.3%)
    assert resumen_cat[0]["nombre"] == "Supermercado"
    assert resumen_cat[0]["total"] == Decimal("5000.00")
    assert resumen_cat[0]["porcentaje"] == Decimal("83.3")
    # El segundo debe ser Servicios con 1000 (16.7%)
    assert resumen_cat[1]["nombre"] == "Servicios"
    assert resumen_cat[1]["total"] == Decimal("1000.00")
    assert resumen_cat[1]["porcentaje"] == Decimal("16.7")
