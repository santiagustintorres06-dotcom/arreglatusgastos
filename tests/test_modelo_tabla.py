from datetime import date
from decimal import Decimal
import pytest
from PySide6.QtCore import Qt

from models.gasto import Gasto
from repository.categoria_repo import CategoriaRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from ui.modelo_tabla import ModeloTablaGastos


def test_modelo_tabla_estructura_y_formato(
    qapp,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
    miembro_repo: MiembroRepo,
):
    modelo = ModeloTablaGastos(gasto_service)
    cats = categoria_repo.listar()
    modelo.actualizar_catalogos(cats, [])

    # Al inicio, tiene 0 gastos + 1 fila vacía
    assert modelo.rowCount() == 1
    assert modelo.columnCount() == 6
    assert modelo.headerData(0, Qt.Orientation.Horizontal) == "Fecha"
    assert modelo.headerData(3, Qt.Orientation.Horizontal) == "Monto"
    assert modelo.headerData(0, Qt.Orientation.Vertical) == "+"

    # Cargar 2 gastos
    super_cat = categoria_repo.obtener_por_nombre("Supermercado")
    g1 = gasto_service.crear("2026-10-10", "1250.50", super_cat.id, "Super")
    g2 = gasto_service.crear("2026-10-12", "500.00", super_cat.id, "Farmacia")

    modelo.cargar_gastos([g1, g2])
    assert modelo.rowCount() == 3  # 2 gastos + 1 fila vacía
    assert modelo.headerData(0, Qt.Orientation.Vertical) == "1"
    assert modelo.headerData(1, Qt.Orientation.Vertical) == "2"
    assert modelo.headerData(2, Qt.Orientation.Vertical) == "+"

    # Comprobar formateo de moneda en display role
    idx_monto = modelo.index(0, ModeloTablaGastos.COL_MONTO)
    assert "$" in modelo.data(idx_monto, Qt.ItemDataRole.DisplayRole)
    assert "1.250,50" in modelo.data(idx_monto, Qt.ItemDataRole.DisplayRole)


def test_modelo_tabla_edicion_inline(
    qapp,
    gasto_service: GastoService,
    categoria_repo: CategoriaRepo,
):
    modelo = ModeloTablaGastos(gasto_service)
    cats = categoria_repo.listar()
    modelo.actualizar_catalogos(cats, [])

    super_cat = categoria_repo.obtener_por_nombre("Supermercado")
    gasto = gasto_service.crear("2026-10-15", "1000.00", super_cat.id, "Inicial")
    modelo.cargar_gastos([gasto])

    # Editar descripción
    idx_desc = modelo.index(0, ModeloTablaGastos.COL_DESCRIPCION)
    ok = modelo.setData(idx_desc, "Cambiado", Qt.ItemDataRole.EditRole)
    assert ok is True
    assert modelo.data(idx_desc, Qt.ItemDataRole.DisplayRole) == "Cambiado"

    # Editar monto válido
    idx_monto = modelo.index(0, ModeloTablaGastos.COL_MONTO)
    ok_monto = modelo.setData(idx_monto, "1500,25", Qt.ItemDataRole.EditRole)
    assert ok_monto is True
    g_actualizado = gasto_service.obtener_por_id(gasto.id)
    assert g_actualizado.monto == Decimal("1500.25")

    # Editar con error (monto negativo)
    errores = []
    modelo.error_ocurrido.connect(errores.append)
    fallo = modelo.setData(idx_monto, "-50", Qt.ItemDataRole.EditRole)
    assert fallo is False
    assert len(errores) == 1
    assert "mayor a" in errores[0]
