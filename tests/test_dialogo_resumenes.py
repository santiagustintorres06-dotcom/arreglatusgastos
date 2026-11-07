from datetime import date
from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox

from models.tarjeta import ConsumoTarjeta, Tarjeta
from ui.dialogo_resumenes import COL_CIERRE, COL_ESTADO, COL_MES, COL_TOTAL, COL_VENCE, DialogoResumenes
from ui.dialogo_tarjeta import DialogoTarjeta

HOY = date(2026, 11, 7)


def _preparar(repo):
    macro = repo.crear(Tarjeta(nombre="Visa Macro", dia_cierre=22, dia_vencimiento=5))
    naranja = repo.crear(Tarjeta(nombre="Naranja Visa", dia_cierre=28, dia_vencimiento=10))
    for tid in (macro, naranja):
        repo.crear_consumo(
            ConsumoTarjeta(tarjeta_id=tid, fecha_compra="2026-11-23", descripcion="Zapatillas",
                           monto_total_cent=300000, monto_cuota_cent=100000, cantidad_cuotas=3)
        )
    return macro, naranja


def _fila(dlg, texto_mes):
    for f in range(dlg.tabla.rowCount()):
        if dlg.tabla.item(f, COL_MES).text() == texto_mes:
            return f
    raise AssertionError(f"No está el resumen {texto_mes}")


def test_cada_tarjeta_con_su_cierre(qapp, tarjeta_repo):
    macro, naranja = _preparar(tarjeta_repo)

    dlg = DialogoResumenes(tarjeta_repo, tarjeta_id=macro, hoy=HOY)
    assert "Cierra el día 22" in dlg.lbl_regla.text() and "mes siguiente" in dlg.lbl_regla.text()
    # Compra del 23/11 en Visa Macro: ya cerró → resumen de diciembre
    f_nov, f_dic = _fila(dlg, "Noviembre 2026"), _fila(dlg, "Diciembre 2026")
    assert dlg.tabla.item(f_nov, COL_TOTAL).text() == "$ 0,00"
    assert dlg.tabla.item(f_dic, COL_CIERRE).text() == "22/12/2026"
    assert dlg.tabla.item(f_dic, COL_VENCE).text() == "05/01/2027"
    assert dlg.tabla.item(f_dic, COL_TOTAL).text() == "$ 1.000,00"
    # Lista hasta el último resumen con cuotas (febrero 2027)
    _fila(dlg, "Febrero 2027")

    dlg.combo_tarjeta.setCurrentIndex(dlg.combo_tarjeta.findData(naranja))
    # En Naranja la misma compra entra en el resumen de noviembre (cierra 28/11)
    f_nov = _fila(dlg, "Noviembre 2026")
    assert dlg.tabla.item(f_nov, COL_VENCE).text() == "10/12/2026"
    assert dlg.tabla.item(f_nov, COL_TOTAL).text() == "$ 1.000,00"


def test_pagar_resumen_y_cambiar_fechas(qapp, tarjeta_repo):
    macro, _ = _preparar(tarjeta_repo)
    dlg = DialogoResumenes(tarjeta_repo, tarjeta_id=macro, hoy=HOY)

    dlg.tabla.selectRow(_fila(dlg, "Diciembre 2026"))
    assert dlg.btn_pagar.isEnabled()
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        dlg._pagar()
    consumo = [c for c in tarjeta_repo.listar_consumos() if c.tarjeta_id == macro][0]
    assert consumo.cuotas_pagadas == 1
    assert dlg.tabla.item(_fila(dlg, "Diciembre 2026"), COL_ESTADO).text() == "Pagado"
    assert dlg.hubo_cambios

    # El banco corrió el cierre de diciembre al 24 y el vencimiento al 7/1
    tarjeta_repo.guardar_ajuste_resumen(macro, 2026, 12, date(2026, 12, 24), date(2027, 1, 7))
    dlg._recargar()
    f = _fila(dlg, "Diciembre 2026")
    assert dlg.tabla.item(f, COL_CIERRE).text().startswith("24/12/2026")
    assert "✏️" in dlg.tabla.item(f, COL_CIERRE).text()
    assert dlg.tabla.item(f, COL_VENCE).text() == "07/01/2027"


def test_formulario_tarjeta_explica_cierre_y_vencimiento(qapp):
    dlg = DialogoTarjeta()
    dlg.spin_cierre.setValue(22)
    dlg.spin_vencimiento.setValue(5)
    assert "mes siguiente" in dlg.lbl_explicacion.text()
    dlg.spin_cierre.setValue(5)
    dlg.spin_vencimiento.setValue(15)
    assert "mismo mes" in dlg.lbl_explicacion.text()
