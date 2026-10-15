from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QComboBox, QDateEdit, QStyledItemDelegate

from config import MEDIOS_DE_PAGO
from models.categoria import Categoria
from models.miembro import Miembro


class EditorFechaDelegate(QStyledItemDelegate):
    """Delegado para editar celdas de fecha con un selector visual QDateEdit con calendario desplegable."""

    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("dd/MM/yyyy")
        return editor

    def setEditorData(self, editor: QDateEdit, index):
        val = index.model().data(index, Qt.ItemDataRole.EditRole)
        if val:
            try:
                # Puede venir en ISO o dd/MM/yyyy
                if "/" in str(val):
                    p = str(val).split("/")
                    d = QDate(int(p[2]), int(p[1]), int(p[0]))
                else:
                    d_obj = date.fromisoformat(str(val))
                    d = QDate(d_obj.year, d_obj.month, d_obj.day)
                editor.setDate(d)
                return
            except (ValueError, IndexError):
                pass
        hoy = date.today()
        editor.setDate(QDate(hoy.year, hoy.month, hoy.day))

    def setModelData(self, editor: QDateEdit, model, index):
        qdate = editor.date()
        fecha_str = f"{qdate.day():02d}/{qdate.month():02d}/{qdate.year():04d}"
        model.setData(index, fecha_str, Qt.ItemDataRole.EditRole)


class ComboCategoriaDelegate(QStyledItemDelegate):
    """Delegado para editar la columna Categoría con un desplegable de categorías."""

    def __init__(self, obtener_categorias_cb, parent=None):
        super().__init__(parent)
        self.obtener_categorias = obtener_categorias_cb

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        categorias: list[Categoria] = self.obtener_categorias()
        for cat in categorias:
            editor.addItem(cat.nombre, cat.id)
        return editor

    def setEditorData(self, editor: QComboBox, index):
        texto_actual = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        idx = editor.findText(texto_actual or "")
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model, index):
        nombre_cat = editor.currentText()
        if nombre_cat:
            model.setData(index, nombre_cat, Qt.ItemDataRole.EditRole)


class ComboMedioPagoDelegate(QStyledItemDelegate):
    """Delegado para editar la columna Medio de Pago con opciones fijas."""

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItem("")  # Vacío permitido
        for medio in MEDIOS_DE_PAGO:
            editor.addItem(medio)
        return editor

    def setEditorData(self, editor: QComboBox, index):
        texto_actual = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        idx = editor.findText(texto_actual or "")
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)


class ComboMiembroDelegate(QStyledItemDelegate):
    """Delegado para editar la columna Pagó con lista de miembros familiares."""

    def __init__(self, obtener_miembros_cb, parent=None):
        super().__init__(parent)
        self.obtener_miembros = obtener_miembros_cb

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItem("", None)
        miembros: list[Miembro] = self.obtener_miembros()
        for m in miembros:
            editor.addItem(m.nombre, m.id)
        return editor

    def setEditorData(self, editor: QComboBox, index):
        texto_actual = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        idx = editor.findText(texto_actual or "")
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)


class ComboCuotasDelegate(QStyledItemDelegate):
    """Delegado para editar la columna Cuotas con opciones de cuotas comunes o personalizadas."""

    OPCIONES = [
        "",
        "1 cuota",
        "2 cuotas",
        "3 cuotas",
        "6 cuotas",
        "9 cuotas",
        "12 cuotas",
        "18 cuotas",
        "24 cuotas",
    ]

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.setEditable(True)
        for op in self.OPCIONES:
            editor.addItem(op)
        return editor

    def setEditorData(self, editor: QComboBox, index):
        val = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        idx = editor.findText(val or "")
        if idx >= 0:
            editor.setCurrentIndex(idx)
        else:
            editor.setEditText(val or "")

    def setModelData(self, editor: QComboBox, model, index):
        model.setData(index, editor.currentText().strip(), Qt.ItemDataRole.EditRole)

