"""Opciones simples del programa (se guardan en la base de datos)."""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from repository.preferencias_repo import DIAS_AVISO, MOSTRAR_AVISOS, PreferenciasRepo


class DialogoOpciones(QDialog):
    def __init__(self, prefs: PreferenciasRepo, parent=None):
        super().__init__(parent)
        self._prefs = prefs
        self.setWindowTitle("⚙️ Opciones")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        form = QFormLayout()

        self.spin_dias = QSpinBox()
        self.spin_dias.setRange(1, 30)
        self.spin_dias.setSuffix(" días antes")
        self.spin_dias.setValue(prefs.dias_aviso())
        form.addRow("Avisar vencimientos de tarjeta:", self.spin_dias)

        self.chk_avisos = QCheckBox("Mostrar el aviso de vencimientos arriba de la ventana")
        self.chk_avisos.setChecked(prefs.mostrar_avisos())
        form.addRow("", self.chk_avisos)
        layout.addLayout(form)

        nota = QLabel(
            "Con cuántos días de anticipación un vencimiento se marca en naranja "
            "(\"próximo a vencer\") y aparece en el aviso. Los vencidos sin pagar "
            "siempre se muestran en rojo."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(nota)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Save).setText("💾 Guardar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _guardar(self) -> None:
        self._prefs.guardar(DIAS_AVISO, str(self.spin_dias.value()))
        self._prefs.guardar(MOSTRAR_AVISOS, "1" if self.chk_avisos.isChecked() else "0")
        self.accept()
