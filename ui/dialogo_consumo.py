from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import formatear_moneda, parsear_monto
from models.tarjeta import ConsumoTarjeta, Tarjeta
from services.tarjeta_service import fecha_vencimiento_cuota, mes_primera_cuota


class DialogoConsumo(QDialog):
    """Formulario para registrar un nuevo consumo con tarjeta."""

    def __init__(self, tarjetas: list[Tarjeta], consumo: ConsumoTarjeta | None = None, parent=None):
        super().__init__(parent)
        self._tarjetas = tarjetas
        self._consumo = consumo
        self.setWindowTitle("Nuevo Consumo" if consumo is None else "Editar Consumo")
        self.setMinimumWidth(430)
        self.setModal(True)
        self._construir_ui()
        if consumo:
            self._cargar_datos(consumo)
        self._actualizar_preview()

    # ------------------------------------------------------------------
    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(10)

        # Tarjeta
        from PySide6.QtWidgets import QComboBox
        self.combo_tarjeta = QComboBox()
        for t in self._tarjetas:
            self.combo_tarjeta.addItem(t.nombre, t.id)
        self.combo_tarjeta.currentIndexChanged.connect(self._actualizar_preview)
        form.addRow("Tarjeta *:", self.combo_tarjeta)

        # Descripción
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Ej: Supermercado Día")
        self.txt_desc.setMaxLength(200)
        form.addRow("Descripción *:", self.txt_desc)

        # Fecha de compra
        self.dt_fecha = QDateEdit()
        self.dt_fecha.setCalendarPopup(True)
        self.dt_fecha.setDate(QDate.currentDate())
        self.dt_fecha.setDisplayFormat("dd/MM/yyyy")
        self.dt_fecha.dateChanged.connect(self._actualizar_preview)
        form.addRow("Fecha de compra *:", self.dt_fecha)

        # Cantidad de cuotas
        self.spin_cuotas = QSpinBox()
        self.spin_cuotas.setRange(1, 60)
        self.spin_cuotas.setValue(1)
        self.spin_cuotas.setToolTip("1 = pago único")
        self.spin_cuotas.valueChanged.connect(self._on_cuotas_changed)
        form.addRow("Cantidad de cuotas *:", self.spin_cuotas)

        # Radio: ingresar total O cuota
        self._radio_total = QRadioButton("Monto total")
        self._radio_cuota = QRadioButton("Monto por cuota")
        self._radio_total.setChecked(True)
        grupo_radio = QButtonGroup(self)
        grupo_radio.addButton(self._radio_total)
        grupo_radio.addButton(self._radio_cuota)
        self._radio_total.toggled.connect(self._on_modo_monto_changed)

        row_radio = QWidget()
        hl = QHBoxLayout(row_radio)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(self._radio_total)
        hl.addWidget(self._radio_cuota)
        hl.addStretch()
        form.addRow("Forma de ingreso:", row_radio)

        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Ej: 15000 o 15000,50")
        self.txt_monto.textChanged.connect(self._actualizar_preview)
        form.addRow("Monto *:", self.txt_monto)

        # Precio de contado (opcional, para compras con interés)
        self.txt_contado = QLineEdit()
        self.txt_contado.setPlaceholderText("Solo si difiere del total (interés)")
        form.addRow("Precio de contado (opc.):", self.txt_contado)

        layout.addLayout(form)

        # Preview de primera cuota
        self.lbl_preview = QLabel("")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet(
            "background: #eaf4fb; border: 1px solid #aed6f1; border-radius: 5px;"
            "padding: 8px; font-weight: 600; color: #1a5276;"
        )
        layout.addWidget(self.lbl_preview)

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

    # ------------------------------------------------------------------
    def _tarjeta_seleccionada(self) -> Tarjeta | None:
        t_id = self.combo_tarjeta.currentData()
        for t in self._tarjetas:
            if t.id == t_id:
                return t
        return None

    def _actualizar_preview(self) -> None:
        tarjeta = self._tarjeta_seleccionada()
        if tarjeta is None:
            self.lbl_preview.setText("Seleccioná una tarjeta para ver el vencimiento.")
            return

        qd = self.dt_fecha.date()
        try:
            fecha_compra = date(qd.year(), qd.month(), qd.day())
        except Exception:
            self.lbl_preview.setText("")
            return

        anio_prim, mes_prim = mes_primera_cuota(fecha_compra, tarjeta.dia_cierre)
        fecha_venc = fecha_vencimiento_cuota(anio_prim, mes_prim, 1, tarjeta.dia_vencimiento)

        n = self.spin_cuotas.value()
        texto_cuotas = f"{n} cuota{'s' if n > 1 else''}  ·  " if n > 1 else "Pago único  ·  "

        try:
            monto_txt = self.txt_monto.text().strip()
            if monto_txt:
                monto = parsear_monto(monto_txt)
                if self._radio_cuota.isChecked():
                    cuota_cent = int(monto * 100)
                    total_cent = cuota_cent * n
                else:
                    total_cent = int(monto * 100)
                    cuota_cent = total_cent // n
                texto_cuota = f"Cuota: {formatear_moneda(Decimal(cuota_cent) / 100)}"
            else:
                texto_cuota = ""
        except ValueError:
            texto_cuota = ""

        self.lbl_preview.setText(
            f"{texto_cuotas}Primera cuota: vence el {fecha_venc.strftime('%d/%m/%Y')}  {texto_cuota}"
        )

    def _on_cuotas_changed(self) -> None:
        self._actualizar_preview()

    def _on_modo_monto_changed(self) -> None:
        if self._radio_total.isChecked():
            self.txt_monto.setPlaceholderText("Monto total de la compra")
        else:
            self.txt_monto.setPlaceholderText("Monto de cada cuota")
        self._actualizar_preview()

    def _cargar_datos(self, c: ConsumoTarjeta) -> None:
        for i in range(self.combo_tarjeta.count()):
            if self.combo_tarjeta.itemData(i) == c.tarjeta_id:
                self.combo_tarjeta.setCurrentIndex(i)
                break
        self.txt_desc.setText(c.descripcion)
        fd = date.fromisoformat(c.fecha_compra)
        self.dt_fecha.setDate(QDate(fd.year, fd.month, fd.day))
        self.spin_cuotas.setValue(c.cantidad_cuotas)
        self._radio_total.setChecked(True)
        self.txt_monto.setText(str(Decimal(c.monto_total_cent) / 100))
        if c.precio_contado_cent:
            self.txt_contado.setText(str(Decimal(c.precio_contado_cent) / 100))

    # ------------------------------------------------------------------
    def _validar_y_aceptar(self) -> None:
        tarjeta = self._tarjeta_seleccionada()
        if tarjeta is None:
            QMessageBox.warning(self, "Campo requerido", "Seleccioná una tarjeta.")
            return

        desc = self.txt_desc.text().strip()
        if not desc:
            QMessageBox.warning(self, "Campo requerido", "La descripción es obligatoria.")
            self.txt_desc.setFocus()
            return

        try:
            monto = parsear_monto(self.txt_monto.text())
        except ValueError as e:
            QMessageBox.warning(self, "Monto inválido", str(e))
            self.txt_monto.setFocus()
            return

        n = self.spin_cuotas.value()
        if self._radio_cuota.isChecked():
            cuota_cent = int(monto * 100)
            total_cent = cuota_cent * n
        else:
            total_cent = int(monto * 100)
            cuota_cent = total_cent // n

        if cuota_cent <= 0:
            QMessageBox.warning(self, "Monto inválido", "El monto de cada cuota debe ser mayor a cero.")
            return

        contado_cent: int | None = None
        txt_cont = self.txt_contado.text().strip()
        if txt_cont:
            try:
                contado_cent = int(parsear_monto(txt_cont) * 100)
            except ValueError:
                QMessageBox.warning(self, "Precio de contado inválido", "Ingresá un número válido o dejá el campo vacío.")
                self.txt_contado.setFocus()
                return

        qd = self.dt_fecha.date()
        fecha_compra = f"{qd.year()}-{qd.month():02d}-{qd.day():02d}"

        self._resultado = ConsumoTarjeta(
            id=self._consumo.id if self._consumo else 0,
            tarjeta_id=tarjeta.id,
            fecha_compra=fecha_compra,
            descripcion=desc,
            monto_total_cent=total_cent,
            monto_cuota_cent=cuota_cent,
            cantidad_cuotas=n,
            cuotas_pagadas=self._consumo.cuotas_pagadas if self._consumo else 0,
            precio_contado_cent=contado_cent,
            estado=self._consumo.estado if self._consumo else "activo",
        )
        self.accept()

    def resultado(self) -> ConsumoTarjeta | None:
        return getattr(self, "_resultado", None)
