from datetime import date
from decimal import Decimal
import pytest
from PySide6.QtWidgets import QMessageBox

from models.tarjeta import ConsumoTarjeta, Tarjeta
from repository.categoria_repo import CategoriaRepo
from repository.tarjeta_repo import TarjetaRepo
from services.gasto_service import GastoService
from ui.vista_tarjetas import COL_CUOTAS, COL_DESC, COL_ESTADO, VistaTarjetas


def test_vista_tarjetas_carga_filtros_y_busqueda(
    qapp,
    tarjeta_repo: TarjetaRepo,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
):
    # 1. Crear 2 tarjetas
    t1_id = tarjeta_repo.crear(Tarjeta(nombre="Visa Galicia", dia_cierre=20, dia_vencimiento=5))
    t2_id = tarjeta_repo.crear(Tarjeta(nombre="Mastercard Santander", dia_cierre=15, dia_vencimiento=2))

    # 2. Crear consumos
    tarjeta_repo.crear_consumo(
        ConsumoTarjeta(
            tarjeta_id=t1_id,
            fecha_compra="2026-10-10",
            descripcion="Smart TV",
            monto_total_cent=12000000,
            monto_cuota_cent=2000000,
            cantidad_cuotas=6,
        )
    )
    tarjeta_repo.crear_consumo(
        ConsumoTarjeta(
            tarjeta_id=t2_id,
            fecha_compra="2026-10-12",
            descripcion="Zapatillas deportivas",
            monto_total_cent=5000000,
            monto_cuota_cent=5000000,
            cantidad_cuotas=1,
        )
    )

    vista = VistaTarjetas(
        tarjeta_repo=tarjeta_repo,
        gasto_service=gasto_service,
        categoria_repo=categoria_repo,
    )
    vista.fijar_periodo(2026, 10)

    # Debe mostrar 2 consumos en la tabla
    assert vista.tabla.rowCount() == 2

    # Probar filtro por tarjeta (Visa)
    idx_visa = vista.combo_filtro_tarjeta.findText("Visa Galicia")
    vista.combo_filtro_tarjeta.setCurrentIndex(idx_visa)
    assert vista.tabla.rowCount() == 1
    assert vista.tabla.item(0, COL_DESC).text() == "Smart TV"

    # Restablecer filtro tarjeta
    vista.combo_filtro_tarjeta.setCurrentIndex(0)
    assert vista.tabla.rowCount() == 2

    # Probar búsqueda por texto
    vista.txt_buscar.setText("zapat")
    assert vista.tabla.rowCount() == 1
    assert vista.tabla.item(0, COL_DESC).text() == "Zapatillas deportivas"

    vista.txt_buscar.setText("")
    assert vista.tabla.rowCount() == 2


def test_vista_tarjetas_marcar_pagada_y_deshacer(
    qapp,
    tarjeta_repo: TarjetaRepo,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
    monkeypatch,
):
    t_id = tarjeta_repo.crear(Tarjeta(nombre="Visa", dia_cierre=20, dia_vencimiento=5))
    c_id = tarjeta_repo.crear_consumo(
        ConsumoTarjeta(
            tarjeta_id=t_id,
            fecha_compra="2026-10-01",
            descripcion="Celular",
            monto_total_cent=6000000,
            monto_cuota_cent=2000000,
            cantidad_cuotas=3,
        )
    )

    vista = VistaTarjetas(
        tarjeta_repo=tarjeta_repo,
        gasto_service=gasto_service,
        categoria_repo=categoria_repo,
    )

    vista.tabla.selectRow(0)
    assert "0/3" in vista.tabla.item(0, COL_CUOTAS).text()

    # Marcar cuota pagada
    vista._marcar_cuota_pagada()
    assert "1/3" in vista.tabla.item(0, COL_CUOTAS).text()

    # Deshacer cuota con confirmación Yes
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )
    vista.tabla.selectRow(0)
    vista._deshacer_cuota()
    assert "0/3" in vista.tabla.item(0, COL_CUOTAS).text()


def test_vista_tarjetas_adelantar_y_cancelar(
    qapp,
    tarjeta_repo: TarjetaRepo,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
    monkeypatch,
):
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )
    t_id = tarjeta_repo.crear(Tarjeta(nombre="Visa", dia_cierre=20, dia_vencimiento=5))
    c_id = tarjeta_repo.crear_consumo(
        ConsumoTarjeta(
            tarjeta_id=t_id,
            fecha_compra="2026-10-01",
            descripcion="Heladera",
            monto_total_cent=12000000,
            monto_cuota_cent=2000000,
            cantidad_cuotas=6,
        )
    )

    vista = VistaTarjetas(
        tarjeta_repo=tarjeta_repo,
        gasto_service=gasto_service,
        categoria_repo=categoria_repo,
    )
    vista.tabla.selectRow(0)

    # Adelantar cuotas restantes -> pasa a finalizado y 6/6 pagadas
    vista._adelantar_cuotas()
    consumo = tarjeta_repo.obtener_consumo(c_id)
    assert consumo.cuotas_pagadas == 6
    assert consumo.estado == "finalizado"

    # Cancelar consumo -> cancelado
    c2_id = tarjeta_repo.crear_consumo(
        ConsumoTarjeta(
            tarjeta_id=t_id,
            fecha_compra="2026-10-02",
            descripcion="Gasto cancelado",
            monto_total_cent=100000,
            monto_cuota_cent=100000,
            cantidad_cuotas=1,
        )
    )
    vista._recargar()
    for row in range(vista.tabla.rowCount()):
        if vista.tabla.item(row, COL_DESC).text() == "Gasto cancelado":
            vista.tabla.selectRow(row)
            break
    vista._cancelar_consumo()
    consumo2 = tarjeta_repo.obtener_consumo(c2_id)
    assert consumo2.estado == "cancelado"


def test_vista_tarjetas_pasar_a_planilla(
    qapp,
    tarjeta_repo: TarjetaRepo,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
    monkeypatch,
):
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args, **kwargs: None
    )

    t_id = tarjeta_repo.crear(Tarjeta(nombre="Visa Crédito", dia_cierre=20, dia_vencimiento=5))
    tarjeta_repo.crear_consumo(
        ConsumoTarjeta(
            tarjeta_id=t_id,
            fecha_compra="2026-10-05",  # Antes del cierre del 20/10 -> 1ra cuota en 10/2026
            descripcion="Supermercado mensual",
            monto_total_cent=3000000,  # $ 30.000,00
            monto_cuota_cent=3000000,
            cantidad_cuotas=1,
        )
    )

    vista = VistaTarjetas(
        tarjeta_repo=tarjeta_repo,
        gasto_service=gasto_service,
        categoria_repo=categoria_repo,
    )
    vista.fijar_periodo(2026, 10)

    assert not tarjeta_repo.esta_mes_volcado_planilla(t_id, 2026, 10)
    assert vista.btn_pasar_planilla.isEnabled()

    # Pasar a planilla
    vista._pasar_a_planilla()

    # Ahora debe figurar como volcado en BD
    assert tarjeta_repo.esta_mes_volcado_planilla(t_id, 2026, 10)
    assert not vista.btn_pasar_planilla.isEnabled()
    assert "Volcado" in vista.btn_pasar_planilla.text()

    # El gasto debe figurar en el servicio de gastos
    gastos_oct = gasto_service.gasto_repo.listar_por_mes(2026, 10)
    gastos_tarjeta = [g for g in gastos_oct if "Resumen Tarjeta Visa Crédito" in g.descripcion]
    assert len(gastos_tarjeta) == 1
    assert gastos_tarjeta[0].monto == Decimal("30000.00")
    assert gastos_tarjeta[0].medio_pago == "Crédito"

    # Si se intenta pasar nuevamente, no duplica
    vista._pasar_a_planilla()
    gastos_oct_2 = gasto_service.gasto_repo.listar_por_mes(2026, 10)
    assert len([g for g in gastos_oct_2 if "Resumen Tarjeta Visa Crédito" in g.descripcion]) == 1
