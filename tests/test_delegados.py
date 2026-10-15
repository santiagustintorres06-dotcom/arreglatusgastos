from datetime import date
import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QComboBox, QDateEdit

from models.categoria import Categoria
from models.miembro import Miembro
from repository.categoria_repo import CategoriaRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from ui.delegados import (
    ComboCategoriaDelegate,
    ComboMedioPagoDelegate,
    ComboMiembroDelegate,
    EditorFechaDelegate,
)
from ui.modelo_tabla import ModeloTablaGastos


def test_delegado_fecha(qapp, gasto_service: GastoService):
    modelo = ModeloTablaGastos(gasto_service)
    delegate = EditorFechaDelegate()

    editor = delegate.createEditor(None, None, None)
    assert isinstance(editor, QDateEdit)
    assert editor.calendarPopup() is True

    # Simular setModelData
    editor.setDate(QDate(2026, 10, 20))
    idx = modelo.index(0, ModeloTablaGastos.COL_FECHA)
    delegate.setModelData(editor, modelo, idx)
    assert modelo.data(idx, Qt.ItemDataRole.DisplayRole) == "20/10/2026"


def test_delegado_categoria(
    qapp, gasto_service: GastoService, categoria_repo: CategoriaRepo
):
    cats = categoria_repo.listar()
    modelo = ModeloTablaGastos(gasto_service)
    modelo.actualizar_catalogos(cats, [])

    delegate = ComboCategoriaDelegate(lambda: cats)
    editor = delegate.createEditor(None, None, None)
    assert isinstance(editor, QComboBox)
    assert editor.count() == len(cats)

    # Seleccionar y guardar en modelo
    editor.setCurrentIndex(0)
    idx = modelo.index(0, ModeloTablaGastos.COL_CATEGORIA)
    delegate.setModelData(editor, modelo, idx)
    assert modelo.data(idx, Qt.ItemDataRole.DisplayRole) == editor.currentText()


def test_delegado_medio_pago(qapp, gasto_service: GastoService):
    modelo = ModeloTablaGastos(gasto_service)
    delegate = ComboMedioPagoDelegate()

    editor = delegate.createEditor(None, None, None)
    assert isinstance(editor, QComboBox)
    assert editor.count() >= 4

    editor.setCurrentText("Transferencia")
    idx = modelo.index(0, ModeloTablaGastos.COL_MEDIO_PAGO)
    delegate.setModelData(editor, modelo, idx)
    assert (
        modelo.data(idx, Qt.ItemDataRole.DisplayRole) == "Transferencia"
    )


def test_delegado_miembro(
    qapp, gasto_service: GastoService, miembro_repo: MiembroRepo
):
    m1 = miembro_repo.crear(Miembro(id=None, nombre="Lucía"))
    miembros = miembro_repo.listar()

    modelo = ModeloTablaGastos(gasto_service)
    modelo.actualizar_catalogos([], miembros)

    delegate = ComboMiembroDelegate(lambda: miembros)
    editor = delegate.createEditor(None, None, None)
    assert isinstance(editor, QComboBox)
    assert editor.count() == len(miembros) + 1  # Incluye opción vacía

    editor.setCurrentText("Lucía")
    idx = modelo.index(0, ModeloTablaGastos.COL_PAGO)
    delegate.setModelData(editor, modelo, idx)
    assert modelo.data(idx, Qt.ItemDataRole.DisplayRole) == "Lucía"
