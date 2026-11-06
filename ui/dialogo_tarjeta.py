from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from config import parsear_monto
from models.tarjeta import Tarjeta


class DialogoTarjeta(QDialog):
    """Formulario para crear o editar una tarjeta de crédito."""

    def __init__(self, tarjeta: Tarjeta | None = None, parent=None):
        super().__init__(parent)
        self._tarjeta = tarjeta
        self.setWindowTitle("Nueva Tarjeta" if tarjeta is None else "Editar Tarjeta")
        self.setMinimumWidth(360)
        self.setModal(True)
        self._construir_ui()
        if tarjeta:
            self._cargar_datos(tarjeta)

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: Visa Banco Galicia")
        self.txt_nombre.setMaxLength(60)
        form.addRow("Nombre de la tarjeta *:", self.txt_nombre)

        self.spin_cierre = QSpinBox()
        self.spin_cierre.setRange(1, 31)
        self.spin_cierre.setValue(15)
        self.spin_cierre.setToolTip("Día del mes en que cierra el resumen")
        form.addRow("Día de cierre *:", self.spin_cierre)

        self.spin_vencimiento = QSpinBox()
        self.spin_vencimiento.setRange(1, 31)
        self.spin_vencimiento.setValue(5)
        self.spin_vencimiento.setToolTip("Día del mes en que vence el pago")
        form.addRow("Día de vencimiento *:", self.spin_vencimiento)

        self.txt_limite = QLineEdit()
        self.txt_limite.setPlaceholderText("Dejar vacío si no tiene límite")
        form.addRow("Límite (opcional):", self.txt_limite)

        self.chk_activa = QCheckBox("Tarjeta activa")
        self.chk_activa.setChecked(True)
        form.addRow("", self.chk_activa)

        layout.addLayout(form)

        lbl_nota = QLabel("* Campos obligatorios")
        lbl_nota.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        layout.addWidget(lbl_nota)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Save).setText("💾 Guardar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self._validar_y_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _cargar_datos(self, t: Tarjeta) -> None:
        self.txt_nombre.setText(t.nombre)
        self.spin_cierre.setValue(t.dia_cierre)
        self.spin_vencimiento.setValue(t.dia_vencimiento)
        if t.limite_cent is not None:
            self.txt_limite.setText(str(Decimal(t.limite_cent) / 100))
        self.chk_activa.setChecked(t.activa)

    def _validar_y_aceptar(self) -> None:
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo requerido", "El nombre de la tarjeta es obligatorio.")
            self.txt_nombre.setFocus()
            return

        limite_cent: int | None = None
        texto_limite = self.txt_limite.text().strip()
        if texto_limite:
            try:
                limite_cent = int(parsear_monto(texto_limite) * 100)
            except ValueError:
                QMessageBox.warning(self, "Límite inválido", "El límite debe ser un número positivo.")
                self.txt_limite.setFocus()
                return

        self._resultado = Tarjeta(
            id=self._tarjeta.id if self._tarjeta else 0,
            nombre=nombre,
            dia_cierre=self.spin_cierre.value(),
            dia_vencimiento=self.spin_vencimiento.value(),
            limite_cent=limite_cent,
            activa=self.chk_activa.isChecked(),
        )
        self.accept()

    def resultado(self) -> Tarjeta | None:
        return getattr(self, "_resultado", None)
