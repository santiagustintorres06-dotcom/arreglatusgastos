from datetime import date
from decimal import Decimal
import pytest

from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.ventana_principal import VentanaPrincipal
from ui.vista_planilla import VistaPlanilla


def test_vista_planilla_filtros_y_totales(
    qapp,
    gasto_service: GastoService,
    resumen_service: ResumenService,
    categoria_repo: CategoriaRepo,
    miembro_repo: MiembroRepo,
):
    super_cat = categoria_repo.obtener_por_nombre("Supermercado")
    servicios_cat = categoria_repo.obtener_por_nombre("Servicios")

    # Crear 2 gastos en el mes de prueba
    gasto_service.crear("2026-10-10", "1500.00", super_cat.id, "Carne y verduras")
    gasto_service.crear("2026-10-12", "700.00", servicios_cat.id, "Factura Luz")

    vista = VistaPlanilla(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=categoria_repo,
        miembro_repo=miembro_repo,
    )
    vista.fijar_periodo(2026, 10)

    # Debe mostrar 2 gastos + 1 fila rápida
    assert vista.modelo.rowCount() == 3
    assert "2 gastos" in vista.lbl_conteo.text()
    assert "2.200,00" in vista.lbl_total_mes.text()

    # Probar filtro por texto
    vista.txt_buscar.setText("luz")
    assert vista.modelo.rowCount() == 2  # 1 filtrado + 1 fila rápida
    assert "1 gasto" in vista.lbl_conteo.text()
    assert "700,00" in vista.lbl_total_mes.text()

    # Limpiar filtro
    vista.txt_buscar.setText("")
    assert vista.modelo.rowCount() == 3


def test_ventana_principal_navegacion_mes(
    qapp,
    gasto_service: GastoService,
    resumen_service: ResumenService,
    categoria_repo: CategoriaRepo,
    miembro_repo: MiembroRepo,
    gasto_repo: GastoRepo,
):
    ventana = VentanaPrincipal(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=categoria_repo,
        miembro_repo=miembro_repo,
        gasto_repo=gasto_repo,
    )

    mes_inicial = ventana.mes_actual
    anio_inicial = ventana.anio_actual

    # Avanzar un mes
    ventana.btn_mes_siguiente.click()
    if mes_inicial == 12:
        assert ventana.mes_actual == 1
        assert ventana.anio_actual == anio_inicial + 1
    else:
        assert ventana.mes_actual == mes_inicial + 1

    # Retroceder mes
    ventana.btn_mes_anterior.click()
    assert ventana.mes_actual == mes_inicial
    assert ventana.anio_actual == anio_inicial


def test_vista_planilla_eliminacion_gasto(
    qapp,
    gasto_service: GastoService,
    resumen_service: ResumenService,
    categoria_repo: CategoriaRepo,
    monkeypatch,
):
    from PySide6.QtWidgets import QMessageBox

    super_cat = categoria_repo.obtener_por_nombre("Supermercado")
    gasto_service.crear("2026-10-10", "1500.00", super_cat.id, "Para borrar")

    vista = VistaPlanilla(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=categoria_repo,
    )
    vista.fijar_periodo(2026, 10)
    assert vista.modelo.rowCount() == 2

    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )

    vista.tabla.selectRow(0)
    vista._eliminar_gasto_seleccionado()

    assert vista.modelo.rowCount() == 1

