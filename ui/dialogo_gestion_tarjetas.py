from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from config import formatear_moneda
from decimal import Decimal
from repository.tarjeta_repo import TarjetaRepo
from ui.dialogo_tarjeta import DialogoTarjeta


class DialogoGestionTarjetas(QDialog):
    """Panel para ver, crear, editar y desactivar tarjetas."""

    def __init__(self, repo: TarjetaRepo, parent=None):
        super().__init__(parent)
        self._repo = repo
        self.setWindowTitle("Gestionar Tarjetas")
        self.setMinimumSize(620, 360)
        self.setModal(True)
        self._construir_ui()
        self._recargar()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 12, 14, 12)

        COLS = ["Nombre", "Día cierre", "Día vencimiento", "Límite", "Estado"]
        self.tabla = QTableWidget(0, len(COLS))
        self.tabla.setHorizontalHeaderLabels(COLS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, len(COLS)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.itemDoubleClicked.connect(self._editar)
        layout.addWidget(self.tabla)

        barra = QHBoxLayout()
        self.btn_nueva = QPushButton("➕ Nueva tarjeta")
        self.btn_nueva.setProperty("class", "btn-primary")
        self.btn_nueva.clicked.connect(self._nueva)

        self.btn_editar = QPushButton("✏️ Editar")
        self.btn_editar.clicked.connect(self._editar)

        self.btn_desactivar = QPushButton("🚫 Desactivar")
        self.btn_desactivar.clicked.connect(self._desactivar)

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.clicked.connect(self.accept)

        for b in [self.btn_nueva, self.btn_editar, self.btn_desactivar]:
            barra.addWidget(b)
        barra.addStretch()
        barra.addWidget(self.btn_cerrar)
        layout.addLayout(barra)

    def _recargar(self) -> None:
        self.tabla.setRowCount(0)
        tarjetas = self._repo.listar()
        for t in tarjetas:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)

            limite_txt = (
                formatear_moneda(Decimal(t.limite_cent) / 100)
                if t.limite_cent is not None else "Sin límite"
            )
            estado_txt = "✅ Activa" if t.activa else "🚫 Inactiva"

            datos = [t.nombre, str(t.dia_cierre), str(t.dia_vencimiento), limite_txt, estado_txt]
            for col, texto in enumerate(datos):
                item = QTableWidgetItem(texto)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setData(Qt.ItemDataRole.UserRole, t.id)
                self.tabla.setItem(row, col, item)

    def _tarjeta_seleccionada_id(self) -> int | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        item = self.tabla.item(fila, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _nueva(self) -> None:
        dlg = DialogoTarjeta(parent=self)
        if dlg.exec():
            t = dlg.resultado()
            if t:
                self._repo.crear(t)
                self._recargar()

    def _editar(self) -> None:
        tid = self._tarjeta_seleccionada_id()
        if tid is None:
            QMessageBox.information(self, "Sin selección", "Seleccioná una tarjeta para editar.")
            return
        t = self._repo.obtener(tid)
        if t is None:
            return
        dlg = DialogoTarjeta(tarjeta=t, parent=self)
        if dlg.exec():
            actualizada = dlg.resultado()
            if actualizada:
                self._repo.actualizar(actualizada)
                self._recargar()

    def _desactivar(self) -> None:
        tid = self._tarjeta_seleccionada_id()
        if tid is None:
            QMessageBox.information(self, "Sin selección", "Seleccioná una tarjeta para desactivar.")
            return
        t = self._repo.obtener(tid)
        if t is None:
            return
        if not t.activa:
            QMessageBox.information(self, "Ya inactiva", "Esta tarjeta ya está desactivada.")
            return
        resp = QMessageBox.question(
            self, "Desactivar tarjeta",
            f"¿Desactivar la tarjeta '{t.nombre}'?\n"
            "No se borrarán los consumos existentes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._repo.desactivar(tid)
            self._recargar()
