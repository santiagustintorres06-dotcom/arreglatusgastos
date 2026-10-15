from datetime import date
from decimal import Decimal
import pytest
from PySide6.QtWidgets import QApplication

from models.gasto import Gasto
from repository.categoria_repo import CategoriaRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from ui.dialogo_gasto import DialogoGasto


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dialogo_gasto_nuevo(
    qapp,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
    miembro_repo: MiembroRepo,
):
    dialogo = DialogoGasto(
        gasto_service=gasto_service,
        categoria_repo=categoria_repo,
        miembro_repo=miembro_repo,
        fecha_inicial=date(2026, 10, 15),
    )
    assert dialogo.windowTitle() == "Nuevo Gasto"
    assert dialogo.cmb_categoria.count() > 0

    # Simular ingreso inválido
    dialogo.txt_monto.setText("-10")
    dialogo._guardar()
    assert not dialogo.lbl_error.isHidden()
    assert "mayor a" in dialogo.lbl_error.text()

    # Simular ingreso válido
    dialogo.txt_monto.setText("450,75")
    dialogo.txt_descripcion.setText("Almuerzo")
    dialogo._guardar()
    assert dialogo.lbl_error.isHidden()


def test_dialogo_gasto_edicion(
    qapp,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
    miembro_repo: MiembroRepo,
):
    cat = categoria_repo.obtener_por_nombre("Supermercado")
    gasto = gasto_service.crear(
        fecha="2026-10-15",
        monto="800.00",
        categoria_id=cat.id,
        descripcion="Original",
    )

    dialogo = DialogoGasto(
        gasto_service=gasto_service,
        categoria_repo=categoria_repo,
        miembro_repo=miembro_repo,
        gasto=gasto,
    )
    assert dialogo.windowTitle() == "Editar Gasto"
    assert "800" in dialogo.txt_monto.text()
    assert dialogo.txt_descripcion.text() == "Original"

    # Editar
    dialogo.txt_monto.setText("950.50")
    dialogo.txt_descripcion.setText("Modificado")
    dialogo._guardar()

    actualizado = gasto_service.obtener_por_id(gasto.id)
    assert actualizado.monto == Decimal("950.50")
    assert actualizado.descripcion == "Modificado"
