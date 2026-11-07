"""Etapa 3 (avisos, proyección, total real, atajos) y Etapa 4 (Excel, respaldos)."""

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import openpyxl
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from db.conexion import inicializar_bd, obtener_conexion, realizar_backup
from models.tarjeta import ConsumoTarjeta, Tarjeta
from repository.preferencias_repo import DIAS_AVISO, PreferenciasRepo
from services.alertas import alertas_vencimientos, texto_alerta
from services.export_service import ExportService
from ui.dialogo_tarjeta import DialogoTarjeta
from ui.grafico_proyeccion import DialogoProyeccion, datos_proyeccion
from ui.ventana_principal import TAB_CALENDARIO, TAB_TARJETAS, VentanaPrincipal

HOY = date(2026, 11, 7)


def _cargar(repo):
    """Visa vence el 10 del mismo mes (cierra el 5); Master vence el 3 del mes siguiente."""
    visa = repo.crear(Tarjeta(nombre="Visa", dia_cierre=5, dia_vencimiento=10))
    master = repo.crear(Tarjeta(nombre="Master", dia_cierre=25, dia_vencimiento=3))
    repo.crear_consumo(ConsumoTarjeta(tarjeta_id=visa, fecha_compra="2026-11-02", descripcion="Tele",
                                      monto_total_cent=300000, monto_cuota_cent=100000, cantidad_cuotas=3))
    repo.crear_consumo(ConsumoTarjeta(tarjeta_id=master, fecha_compra="2026-10-01", descripcion="Ropa",
                                      monto_total_cent=50000, monto_cuota_cent=50000, cantidad_cuotas=1))
    return visa, master


# ---------------- Alertas ----------------


def test_alertas_vencido_y_proximo(tarjeta_repo):
    _cargar(tarjeta_repo)
    alertas = alertas_vencimientos(tarjeta_repo, hoy=HOY, dias_aviso=5)
    # Master venció el 03/11 sin pagar (primero) y Visa vence el 10/11 (en 3 días)
    assert [(a.tarjeta_nombre, a.estado) for a in alertas] == [("Master", "vencido"), ("Visa", "proximo")]
    assert "venció el 03/11" in texto_alerta(alertas[0], HOY)
    assert "en 3 días" in texto_alerta(alertas[1], HOY)

    # Con 2 días de aviso, Visa todavía no se avisa
    assert [a.tarjeta_nombre for a in alertas_vencimientos(tarjeta_repo, hoy=HOY, dias_aviso=2)] == ["Master"]


def test_alertas_no_avisa_lo_pagado(tarjeta_repo):
    visa, master = _cargar(tarjeta_repo)
    for c in tarjeta_repo.listar_consumos():
        tarjeta_repo.marcar_pagadas_hasta(c.id, 1)
    assert alertas_vencimientos(tarjeta_repo, hoy=HOY) == []


def test_preferencias(db_conn):
    prefs = PreferenciasRepo(db_conn)
    assert prefs.dias_aviso() == 5 and prefs.mostrar_avisos()
    prefs.guardar(DIAS_AVISO, "3")
    assert prefs.dias_aviso() == 3
    prefs.guardar(DIAS_AVISO, "basura")
    assert prefs.dias_aviso() == 5


# ---------------- Proyección ----------------


def test_proyeccion_6_meses_y_explicacion(qapp, tarjeta_repo):
    _cargar(tarjeta_repo)
    datos = datos_proyeccion(tarjeta_repo, hoy=HOY)
    assert [e for e, _ in datos] == ["Nov 2026", "Dic 2026", "Ene 2027", "Feb 2027", "Mar 2027", "Abr 2027"]
    # Nov: Tele 1/3 + Ropa (vencida, sin pagar); Dic y Ene: Tele; después nada
    assert [m for _, m in datos] == [Decimal(1500), Decimal(1000), Decimal(1000), 0, 0, 0]
    dlg = DialogoProyeccion(tarjeta_repo, hoy=HOY)
    texto = dlg.lbl_resumen.text()
    assert "En Dic 2026 se liberan $ 500,00" in texto
    assert "Desde Feb 2027 no quedan cuotas" in texto
    dlg.grafico.resize(500, 260)
    dlg.grafico.grab()  # dibuja sin errores


# ---------------- Ventana principal ----------------


def _ventana(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo):
    return VentanaPrincipal(
        gasto_service=gasto_service, resumen_service=resumen_service, categoria_repo=categoria_repo,
        miembro_repo=miembro_repo, gasto_repo=gasto_repo, tarjeta_repo=tarjeta_repo,
    )


def test_total_real_y_atajos(qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo):
    tid = tarjeta_repo.crear(Tarjeta(nombre="Visa", dia_cierre=5, dia_vencimiento=10))
    tarjeta_repo.crear_consumo(ConsumoTarjeta(tarjeta_id=tid, fecha_compra="2030-03-01", descripcion="X",
                                              monto_total_cent=200000, monto_cuota_cent=200000, cantidad_cuotas=1))
    gasto_service.crear("2030-03-15", "500", categoria_repo.obtener_por_nombre("Otros").id, "Pan")
    v = _ventana(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo)
    v.anio_actual, v.mes_actual = 2030, 3
    v._actualizar_vista_periodo()
    texto = v.lbl_status_total.text()
    assert "Planilla: $ 500,00" in texto and "Tarjetas: $ 2.000,00" in texto
    assert "Total real del mes: $ 2.500,00" in texto

    v.show()
    v.activateWindow()
    QTest.qWaitForWindowActive(v, 2000)
    QTest.keyClick(v, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
    assert v.tabs.currentIndex() == TAB_CALENDARIO
    QTest.keyClick(v, Qt.Key.Key_3, Qt.KeyboardModifier.ControlModifier)
    assert v.tabs.currentIndex() == TAB_TARJETAS
    QTest.keyClick(v, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
    assert (v.anio_actual, v.mes_actual) == (2030, 4)
    v.close()


def test_aviso_en_ventana(qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo):
    hoy = date.today()
    tid = tarjeta_repo.crear(Tarjeta(nombre="Visa", dia_cierre=1, dia_vencimiento=2))
    # Compra de hace 2 meses en 1 pago: ya venció y no se pagó
    compra = date(hoy.year - (1 if hoy.month <= 2 else 0), (hoy.month - 3) % 12 + 1, 15)
    tarjeta_repo.crear_consumo(ConsumoTarjeta(tarjeta_id=tid, fecha_compra=compra.isoformat(), descripcion="X",
                                              monto_total_cent=10000, monto_cuota_cent=10000, cantidad_cuotas=1))
    v = _ventana(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, tarjeta_repo)
    assert not v.frame_aviso.isHidden()
    assert "Visa" in v.lbl_aviso.text() and "venció" in v.lbl_aviso.text()
    v._cerrar_aviso()
    assert v.frame_aviso.isHidden()
    v.close()


def test_enter_confirma_formulario(qapp):
    dlg = DialogoTarjeta()
    dlg.show()
    dlg.txt_nombre.setText("Visa Macro")
    dlg.txt_nombre.setFocus()
    QTest.keyClick(dlg.txt_nombre, Qt.Key.Key_Return)
    assert dlg.result() == 1
    assert dlg.resultado().nombre == "Visa Macro"


# ---------------- Etapa 4: Excel y respaldos ----------------


def test_excel_incluye_hoja_tarjetas(tmp_path, gasto_repo, categoria_repo, miembro_repo, resumen_service, tarjeta_repo):
    _cargar(tarjeta_repo)
    servicio = ExportService(gasto_repo, categoria_repo, miembro_repo, resumen_service, tarjeta_repo=tarjeta_repo)
    ruta = servicio.exportar_a_excel(tmp_path / "gastos.xlsx", 2026, 11)
    wb = openpyxl.load_workbook(ruta)
    assert wb.sheetnames == ["Gastos", "Resumen por Categoría", "Tarjetas"]
    valores = [[c for c in fila if c is not None] for fila in wb["Tarjetas"].iter_rows(values_only=True)]
    planos = [str(v) for fila in valores for v in fila]
    assert "Detalle de consumos" in planos
    assert "Proyección: cuotas a pagar en los próximos 6 meses" in planos
    assert any(f[:4] == ["Visa", "10/11/2026", "Tele", "1/3"] for f in valores)
    assert ["11/2026", 1500] in valores


def test_respaldo_incluye_tablas_nuevas(tmp_path: Path):
    ruta = tmp_path / "gastos.db"
    conn = obtener_conexion(ruta)
    inicializar_bd(conn)
    conn.execute("INSERT INTO tarjeta (nombre, dia_cierre, dia_vencimiento) VALUES ('Visa', 22, 5)")
    conn.commit()
    conn.close()
    copia = realizar_backup(ruta, tmp_path / "backups")
    c = sqlite3.connect(copia)
    tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"tarjeta", "consumo_tarjeta", "resumen_tarjeta_mes", "ajuste_resumen_tarjeta", "preferencia"} <= tablas
    assert c.execute("SELECT nombre FROM tarjeta").fetchone()[0] == "Visa"
    c.close()
