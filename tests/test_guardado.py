"""Tests de las correcciones de guardado (datos que "desaparecían")."""

import sqlite3
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import QAbstractItemView, QApplication

from db.conexion import inicializar_bd, obtener_conexion, respaldo_al_cerrar
from models.tarjeta import Tarjeta
from ui.vista_planilla import VistaPlanilla


def _crear_vista(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo):
    return VistaPlanilla(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=categoria_repo,
        miembro_repo=miembro_repo,
        gasto_repo=gasto_repo,
    )


def test_fila_rapida_no_duplica_el_gasto(
    qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo, db_conn
):
    vista = _crear_vista(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo)
    hoy = date.today()
    vista.fijar_periodo(hoy.year, hoy.month)
    m = vista.modelo
    fila = m.rowCount() - 1
    m.setData(m.index(fila, m.COL_DESCRIPCION), "Pan")
    m.setData(m.index(fila, m.COL_MONTO), "1500")

    en_bd = db_conn.execute("SELECT COUNT(*) FROM gasto").fetchone()[0]
    assert en_bd == 1
    assert len(m.gastos) == 1  # antes quedaba 2 (duplicado visual)


def test_fila_rapida_usa_el_mes_que_se_esta_viendo(
    qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo
):
    vista = _crear_vista(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo)
    vista.fijar_periodo(2025, 3)
    m = vista.modelo
    fila = m.rowCount() - 1
    m.setData(m.index(fila, m.COL_MONTO), "200")

    gastos = gasto_service.listar_por_mes(2025, 3)
    assert len(gastos) == 1
    assert gastos[0].fecha == date(2025, 3, 1)


def test_celda_a_medio_escribir_se_guarda_al_confirmar(
    qapp, gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo
):
    cat = categoria_repo.obtener_por_nombre("Otros")
    hoy = date.today()
    gasto_service.crear(hoy, "100", cat.id, "Original")
    vista = _crear_vista(gasto_service, resumen_service, categoria_repo, miembro_repo, gasto_repo)
    vista.fijar_periodo(hoy.year, hoy.month)
    vista.show()

    idx = vista.modelo.index(0, vista.modelo.COL_DESCRIPCION)
    vista.tabla.setCurrentIndex(idx)
    vista.tabla.edit(idx)
    qapp.processEvents()
    editor = vista.tabla.indexWidget(idx) or QApplication.focusWidget()
    assert vista.tabla.state() == QAbstractItemView.State.EditingState
    editor.setText("Editado sin Enter")

    # Simula el cierre del programa sin presionar Enter
    vista.confirmar_edicion_pendiente()

    assert gasto_service.listar_por_mes(hoy.year, hoy.month)[0].descripcion == "Editado sin Enter"
    vista.close()


def test_eliminar_gasto_volcado_desde_tarjeta(gasto_service, categoria_repo, tarjeta_repo, db_conn):
    cat = categoria_repo.obtener_por_nombre("Servicios")
    gasto = gasto_service.crear("2026-11-10", "5000", cat.id, "Resumen Tarjeta Visa")
    tid = tarjeta_repo.crear(Tarjeta(nombre="Visa", dia_cierre=25, dia_vencimiento=10))
    tarjeta_repo.registrar_mes_volcado_planilla(tid, 2026, 11, gasto.id, 500000)

    gasto_service.eliminar(gasto.id)  # antes fallaba por la clave foránea

    assert db_conn.execute("SELECT COUNT(*) FROM gasto").fetchone()[0] == 0
    assert not tarjeta_repo.esta_mes_volcado_planilla(tid, 2026, 11)


def test_respaldo_al_cerrar(tmp_path: Path):
    ruta = tmp_path / "gastos.db"
    conn = obtener_conexion(ruta)
    inicializar_bd(conn)
    conn.close()

    destino = respaldo_al_cerrar(ruta, tmp_path / "backups")

    assert destino is not None and destino.exists()
    copia = sqlite3.connect(destino)
    assert copia.execute("SELECT COUNT(*) FROM categoria").fetchone()[0] > 0
    copia.close()


def test_detecta_carpeta_temporal(tmp_path: Path):
    import tempfile

    from main import _carpeta_es_temporal

    assert _carpeta_es_temporal(Path(tempfile.gettempdir()) / "Temp1_GastosFamilia.zip" / "GastosFamilia")
    assert not _carpeta_es_temporal(Path.home() / "Desktop" / "GastosFamilia")
