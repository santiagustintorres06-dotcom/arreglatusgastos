"""Integración Calendario ↔ Tarjetas/Cuotas (Etapa 2B)."""

from datetime import date
from unittest.mock import patch

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QMessageBox

from models.tarjeta import ConsumoTarjeta, Tarjeta
from ui.ventana_principal import VentanaPrincipal


def _ventana(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo):
    v = VentanaPrincipal(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=categoria_repo,
        miembro_repo=miembro_repo,
        gasto_repo=gasto_repo,
        tarjeta_repo=tarjeta_repo,
    )
    return v


def _ir_a(v, anio, mes):
    v.anio_actual, v.mes_actual = anio, mes
    v._actualizar_vista_periodo()


def _preparar(tarjeta_repo):
    tid = tarjeta_repo.crear(Tarjeta(nombre="Visa", dia_cierre=25, dia_vencimiento=10))
    cid = tarjeta_repo.crear_consumo(
        ConsumoTarjeta(
            tarjeta_id=tid,
            fecha_compra="2030-01-05",
            descripcion="Heladera",
            monto_total_cent=600000,
            monto_cuota_cent=100000,
            cantidad_cuotas=6,
        )
    )
    return tid, cid


def test_calendario_muestra_vencimiento_y_detalle(
    qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo
):
    _preparar(tarjeta_repo)
    v = _ventana(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo)
    v.vista_tarjetas._recargar()
    cal = v.vista_calendario

    # Marzo 2030: cuota 3/6 vence el 10/03
    _ir_a(v, 2030, 3)
    assert date(2030, 3, 10) in cal.calendario.vencimientos
    cal._al_seleccionar_dia(QDate(2030, 3, 10))
    textos = [cal.lista_vencimientos.item(i).text() for i in range(cal.lista_vencimientos.count())]
    assert "Visa" in textos[0] and "1.000,00" in textos[0]
    assert any("Heladera" in t and "3/6" in t for t in textos)
    assert "Tarjetas: $ 1.000,00" in cal.lbl_tarjetas_mes.text()

    # Proyección: julio 2030 ya no tiene cuotas (la última es junio, 6/6)
    _ir_a(v, 2030, 6)
    assert date(2030, 6, 10) in cal.calendario.vencimientos
    _ir_a(v, 2030, 7)
    assert cal.calendario.vencimientos == {}
    assert cal.lbl_tarjetas_mes.text() == ""
    v.close()


def test_calendario_se_actualiza_al_pagar_y_cancelar(
    qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo
):
    _, cid = _preparar(tarjeta_repo)
    v = _ventana(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo)
    v.vista_tarjetas._recargar()
    _ir_a(v, 2030, 1)
    cal = v.vista_calendario
    assert cal.calendario.vencimientos[date(2030, 1, 10)][0].pendiente_cent == 100000

    # Marcar la cuota 1 pagada desde la pestaña Tarjetas
    v.vista_tarjetas.tabla.selectRow(0)
    v.vista_tarjetas._marcar_cuota_pagada()
    ev = cal.calendario.vencimientos[date(2030, 1, 10)][0]
    assert ev.estado == "pagado"

    # Cancelar el consumo → desaparece del calendario
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        v.vista_tarjetas.tabla.selectRow(0)
        v.vista_tarjetas._cancelar_consumo()
    assert cal.calendario.vencimientos == {}
    v.close()


def test_pasar_a_planilla_no_se_cuenta_dos_veces(
    qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo
):
    tid, cid = _preparar(tarjeta_repo)
    tarjeta_repo.marcar_cuota_pagada(cid)  # cuota de enero ya pagada
    v = _ventana(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo)
    _ir_a(v, 2030, 1)
    cal = v.vista_calendario
    assert "Total real: $ 1.000,00" in cal.lbl_tarjetas_mes.text()

    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
         patch.object(QMessageBox, "information"):
        v.vista_tarjetas._pasar_a_planilla()

    # Se pasó el total del resumen aunque la cuota ya estaba marcada como pagada
    gastos = gasto_service.listar_por_mes(2030, 1)
    assert len(gastos) == 1 and str(gastos[0].monto) == "1000.00"
    assert gastos[0].fecha == date(2030, 1, 10)

    # El calendario ya no lo suma aparte: sólo figura dentro de "Gastos"
    assert "1.000,00" in cal.lbl_total_mes.text()
    assert cal.lbl_tarjetas_mes.text() == ""
    assert cal.calendario.vencimientos[date(2030, 1, 10)][0].volcado_planilla

    # Borrar ese gasto en la Planilla libera el mes para volver a pasarlo
    gasto_service.eliminar(gastos[0].id)
    assert "Tarjetas: $ 1.000,00" in cal.lbl_tarjetas_mes.text()
    assert v.vista_tarjetas.btn_pasar_planilla.isEnabled()
    v.close()
