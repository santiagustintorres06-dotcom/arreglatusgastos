from datetime import date
from decimal import Decimal
import pytest
from PySide6.QtCore import QDate

from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.vista_calendario import VistaCalendario


def test_vista_calendario_panel_lateral_y_sincronizacion(
    qapp,
    gasto_service: GastoService,
    resumen_service: ResumenService,
    categoria_repo: CategoriaRepo,
    miembro_repo: MiembroRepo,
    gasto_repo: GastoRepo,
):
    cat_super = categoria_repo.obtener_por_nombre("Supermercado")
    cat_serv = categoria_repo.obtener_por_nombre("Servicios")

    # Crear gastos en fechas específicas
    g1 = gasto_service.crear("2026-10-15", "3000.00", cat_super.id, "Asado familiar")
    g2 = gasto_service.crear("2026-10-15", "500.00", cat_serv.id, "Gas")
    g3 = gasto_service.crear("2026-10-20", "1200.00", cat_super.id, "Almacén")

    vista = VistaCalendario(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=categoria_repo,
        miembro_repo=miembro_repo,
        gasto_repo=gasto_repo,
    )
    vista.fijar_periodo(2026, 10)

    # 1. Verificar total mensual en el header
    assert "4.700,00" in vista.lbl_total_mes.text()

    # 2. Seleccionar el día 15
    vista._al_seleccionar_dia(QDate(2026, 10, 15))
    assert vista.lista_gastos.count() == 2
    assert "3.500,00" in vista.lbl_total_dia.text()
    assert "Asado familiar" in vista.lista_gastos.item(0).text()

    # 3. Seleccionar el día 20
    vista._al_seleccionar_dia(QDate(2026, 10, 20))
    assert vista.lista_gastos.count() == 1
    assert "1.200,00" in vista.lbl_total_dia.text()

    # 4. Seleccionar un día sin gastos (ej. día 25)
    vista._al_seleccionar_dia(QDate(2026, 10, 25))
    assert vista.lista_gastos.count() == 1
    assert "No hay gastos" in vista.lista_gastos.item(0).text()
    assert "0,00" in vista.lbl_total_dia.text()
