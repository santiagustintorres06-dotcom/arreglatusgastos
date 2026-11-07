"""Ventana para ver y gestionar los resúmenes de cada tarjeta.

Cada tarjeta tiene su propio día de cierre y de vencimiento (ej. Visa Macro
cierra el 22 y Naranja el 28). Acá se ve, mes a mes, qué entra en cada
resumen, cuándo cierra, cuándo vence, cuánto es y si está pagado.
También se pueden corregir las fechas de un resumen puntual si el banco
movió el cierre ese mes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from config import formatear_moneda
from models.tarjeta import Tarjeta
from repository.tarjeta_repo import TarjetaRepo
from services.calendario_tarjetas import (
    ETIQUETA_ESTADO,
    PAGADO,
    estado_vencimiento,
)
from services.tarjeta_service import (
    ResumenTarjeta,
    _sumar_meses,
    deshacer_pago_resumen,
    fechas_resumen,
    pagar_resumen,
    resumenes_tarjeta,
    ultimo_resumen_con_cuotas,
)
from ui.calendario_widget import COLOR_ESTADO

NOMBRES_MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
    "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
COLS = ["Resumen de", "Cierra", "Vence", "Total", "Falta pagar", "Estado"]
COL_MES, COL_CIERRE, COL_VENCE, COL_TOTAL, COL_FALTA, COL_ESTADO = range(6)


def _moneda(cent: int) -> str:
    return formatear_moneda(Decimal(cent) / 100)


def texto_regla_tarjeta(t: Tarjeta) -> str:
    """Explicación en palabras de cuándo cierra y vence la tarjeta."""
    if t.dia_vencimiento > t.dia_cierre:
        cuando = "del mismo mes"
    else:
        cuando = "del mes siguiente"
    return f"Cierra el día {t.dia_cierre} de cada mes y vence el día {t.dia_vencimiento} {cuando}."


class DialogoFechasResumen(QDialog):
    """Permite corregir el cierre y vencimiento de un resumen puntual."""

    def __init__(self, tarjeta: Tarjeta, resumen: ResumenTarjeta, parent=None):
        super().__init__(parent)
        self._tarjeta = tarjeta
        self._resumen = resumen
        self.volver_a_habituales = False
        f = resumen.fechas
        self.setWindowTitle(f"Fechas del resumen de {NOMBRES_MESES[f.mes]} {f.anio}")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        habitual = fechas_resumen(tarjeta, f.anio, f.mes)
        lbl = QLabel(
            f"<b>{tarjeta.nombre}</b><br>"
            f"Fechas habituales: cierra el {habitual.cierre:%d/%m/%Y}, "
            f"vence el {habitual.vencimiento:%d/%m/%Y}.<br><br>"
            "Si el banco cambió las fechas este mes (figuran en el resumen impreso "
            "o en la app del banco), corregilas acá. Sólo afecta a este resumen."
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        form = QFormLayout()
        self.dt_cierre = QDateEdit(QDate(f.cierre.year, f.cierre.month, f.cierre.day))
        self.dt_cierre.setCalendarPopup(True)
        self.dt_cierre.setDisplayFormat("dd/MM/yyyy")
        self.dt_vence = QDateEdit(QDate(f.vencimiento.year, f.vencimiento.month, f.vencimiento.day))
        self.dt_vence.setCalendarPopup(True)
        self.dt_vence.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Fecha de cierre:", self.dt_cierre)
        form.addRow("Fecha de vencimiento:", self.dt_vence)
        layout.addLayout(form)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Save).setText("💾 Guardar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        btn_habitual = botones.addButton("↺ Volver a las habituales", QDialogButtonBox.ButtonRole.ResetRole)
        btn_habitual.setEnabled(f.ajustado)
        btn_habitual.clicked.connect(self._volver_habituales)
        botones.accepted.connect(self._validar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def fechas(self) -> tuple[date, date]:
        c, v = self.dt_cierre.date(), self.dt_vence.date()
        return date(c.year(), c.month(), c.day()), date(v.year(), v.month(), v.day())

    def _validar(self) -> None:
        cierre, vence = self.fechas()
        f = self._resumen.fechas
        if vence <= cierre:
            QMessageBox.warning(self, "Fechas inválidas", "El vencimiento tiene que ser posterior al cierre.")
            return
        # El cierre debe quedar cerca del mes del resumen para no mezclar meses
        desde = date(*_sumar_meses(f.anio, f.mes, -1), 15)
        hasta = date(*_sumar_meses(f.anio, f.mes, 1), 15)
        if not (desde <= cierre <= hasta):
            QMessageBox.warning(
                self,
                "Fecha de cierre fuera de rango",
                f"El cierre del resumen de {NOMBRES_MESES[f.mes]} tiene que estar entre el "
                f"{desde:%d/%m/%Y} y el {hasta:%d/%m/%Y}.",
            )
            return
        self.accept()

    def _volver_habituales(self) -> None:
        self.volver_a_habituales = True
        self.accept()


class DialogoResumenes(QDialog):
    """Resúmenes mes a mes de cada tarjeta."""

    def __init__(self, repo: TarjetaRepo, tarjeta_id: int | None = None, parent=None, hoy: date | None = None):
        super().__init__(parent)
        self._repo = repo
        self._hoy = hoy or date.today()
        self._resumenes: list[ResumenTarjeta] = []
        self.hubo_cambios = False
        self.setWindowTitle("🧾 Resúmenes de tarjeta")
        self.setModal(True)
        self.resize(860, 600)
        self._construir_ui()

        self._tarjetas = [t for t in repo.listar() if t.activa]
        for t in self._tarjetas:
            self.combo_tarjeta.addItem(f"💳 {t.nombre}", t.id)
        if tarjeta_id is not None:
            idx = self.combo_tarjeta.findData(tarjeta_id)
            if idx >= 0:
                self.combo_tarjeta.setCurrentIndex(idx)
        self.combo_tarjeta.currentIndexChanged.connect(self._recargar)
        self._recargar()

    # ------------------------------------------------------------------
    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        fila = QHBoxLayout()
        fila.addWidget(QLabel("Tarjeta:"))
        self.combo_tarjeta = QComboBox()
        self.combo_tarjeta.setMinimumWidth(220)
        fila.addWidget(self.combo_tarjeta)
        self.lbl_regla = QLabel("")
        self.lbl_regla.setStyleSheet("color: #34495e; margin-left: 10px;")
        fila.addWidget(self.lbl_regla, stretch=1)
        layout.addLayout(fila)

        self.tabla = QTableWidget(0, len(COLS))
        self.tabla.setHorizontalHeaderLabels(COLS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        cab = self.tabla.horizontalHeader()
        cab.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.itemSelectionChanged.connect(self._mostrar_detalle)
        layout.addWidget(self.tabla, stretch=3)

        self.lbl_detalle = QLabel("Detalle del resumen")
        f = QFont()
        f.setBold(True)
        self.lbl_detalle.setFont(f)
        layout.addWidget(self.lbl_detalle)
        self.lista_detalle = QListWidget()
        self.lista_detalle.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.lista_detalle, stretch=2)

        botones = QHBoxLayout()
        self.btn_pagar = QPushButton("✅ Marcar resumen pagado")
        self.btn_pagar.setProperty("class", "btn-primary")
        self.btn_pagar.setToolTip("Marca como pagadas todas las cuotas de este resumen")
        self.btn_pagar.clicked.connect(self._pagar)
        self.btn_deshacer = QPushButton("↩️ Deshacer pago")
        self.btn_deshacer.clicked.connect(self._deshacer)
        self.btn_fechas = QPushButton("📅 Cambiar fechas de este resumen")
        self.btn_fechas.setToolTip("Por si el banco corrió el cierre o el vencimiento este mes")
        self.btn_fechas.clicked.connect(self._cambiar_fechas)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setProperty("class", "btn-secondary")
        btn_cerrar.clicked.connect(self.accept)
        for b in (self.btn_pagar, self.btn_deshacer, self.btn_fechas):
            botones.addWidget(b)
        botones.addStretch()
        botones.addWidget(btn_cerrar)
        layout.addLayout(botones)

    # ------------------------------------------------------------------
    def _tarjeta(self) -> Tarjeta | None:
        tid = self.combo_tarjeta.currentData()
        return next((t for t in self._tarjetas if t.id == tid), None)

    def _rango(self, tarjeta: Tarjeta, consumos, ajustes) -> tuple[tuple[int, int], tuple[int, int]]:
        desde = _sumar_meses(self._hoy.year, self._hoy.month, -3)
        hasta = _sumar_meses(self._hoy.year, self._hoy.month, 3)
        ultimo = ultimo_resumen_con_cuotas(tarjeta, consumos, ajustes)
        if ultimo and ultimo > hasta:
            hasta = ultimo
        return desde, hasta

    def _recargar(self) -> None:
        tarjeta = self._tarjeta()
        seleccion = self._resumen_seleccionado()
        clave_sel = (seleccion.fechas.anio, seleccion.fechas.mes) if seleccion else None
        self.tabla.setRowCount(0)
        self._resumenes = []
        if tarjeta is None:
            self.lbl_regla.setText("No hay tarjetas activas. Cargalas en '🏦 Gestionar tarjetas'.")
            self._mostrar_detalle()
            return
        self.lbl_regla.setText(texto_regla_tarjeta(tarjeta))

        consumos = self._repo.listar_consumos(tarjeta_id=tarjeta.id)
        ajustes = self._repo.ajustes_por_tarjeta().get(tarjeta.id)
        desde, hasta = self._rango(tarjeta, consumos, ajustes)
        self._resumenes = resumenes_tarjeta(tarjeta, consumos, desde, hasta, ajustes)

        fila_actual = None
        for r in self._resumenes:
            f = r.fechas
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            if r.cuotas:
                estado = estado_vencimiento(f.vencimiento, r.pendiente_cent > 0, self._hoy)
                texto_estado = ETIQUETA_ESTADO[estado]
                color = QColor(COLOR_ESTADO[estado])
            else:
                texto_estado, color = "Sin consumos", QColor("#95a5a6")
            marca = "  ✏️" if f.ajustado else ""
            valores = [
                f"{NOMBRES_MESES[f.mes]} {f.anio}",
                f"{f.cierre:%d/%m/%Y}{marca}",
                f"{f.vencimiento:%d/%m/%Y}",
                _moneda(r.total_cent),
                _moneda(r.pendiente_cent),
                texto_estado,
            ]
            for col, texto in enumerate(valores):
                item = QTableWidgetItem(texto)
                alin = Qt.AlignmentFlag.AlignRight if col in (COL_TOTAL, COL_FALTA) else Qt.AlignmentFlag.AlignCenter
                item.setTextAlignment(alin | Qt.AlignmentFlag.AlignVCenter)
                if col == COL_ESTADO:
                    item.setForeground(color)
                    fnt = item.font()
                    fnt.setBold(True)
                    item.setFont(fnt)
                if f.ajustado and col == COL_CIERRE:
                    item.setToolTip("Fechas corregidas a mano para este resumen")
                self.tabla.setItem(fila, col, item)
            if clave_sel == (f.anio, f.mes):
                fila_actual = fila
            # Por defecto, seleccionar el próximo resumen que vence
            if fila_actual is None and clave_sel is None and f.vencimiento >= self._hoy:
                fila_actual = fila
        if fila_actual is not None:
            self.tabla.selectRow(fila_actual)
        self._mostrar_detalle()

    def _resumen_seleccionado(self) -> ResumenTarjeta | None:
        fila = self.tabla.currentRow()
        if 0 <= fila < len(self._resumenes) and self.tabla.selectedItems():
            return self._resumenes[fila]
        return None

    def _mostrar_detalle(self) -> None:
        r = self._resumen_seleccionado()
        self.lista_detalle.clear()
        self.btn_pagar.setEnabled(bool(r and r.pendiente_cent > 0))
        self.btn_deshacer.setEnabled(bool(r and any(c.pagada for c in r.cuotas)))
        self.btn_fechas.setEnabled(r is not None)
        if r is None:
            self.lbl_detalle.setText("Seleccioná un resumen para ver su detalle")
            return
        f = r.fechas
        self.lbl_detalle.setText(
            f"Resumen de {NOMBRES_MESES[f.mes]} {f.anio}: cierra el {f.cierre:%d/%m}, "
            f"vence el {f.vencimiento:%d/%m} — Total {_moneda(r.total_cent)}"
        )
        if not r.cuotas:
            self.lista_detalle.addItem("No hay consumos en este resumen.")
            return
        for c in r.cuotas:
            marca = "  ✔ pagada" if c.pagada else ""
            item = QListWidgetItem(
                f"• {c.descripcion} — cuota {c.numero_cuota}/{c.total_cuotas}: {_moneda(c.monto_cent)}{marca}"
            )
            if c.pagada:
                item.setForeground(QColor(COLOR_ESTADO[PAGADO]))
            self.lista_detalle.addItem(item)

    # ------------------------------------------------------------------
    def _pagar(self) -> None:
        r = self._resumen_seleccionado()
        if r is None or r.pendiente_cent == 0:
            return
        f = r.fechas
        resp = QMessageBox.question(
            self,
            "Marcar resumen pagado",
            f"¿Marcar como pagado el resumen de {NOMBRES_MESES[f.mes]} {f.anio} de {r.tarjeta_nombre}?\n\n"
            f"Monto: {_moneda(r.pendiente_cent)}\n\n"
            "Las cuotas anteriores de esos consumos también quedan como pagadas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            pagar_resumen(self._repo, r)
            self.hubo_cambios = True
            self._recargar()

    def _deshacer(self) -> None:
        r = self._resumen_seleccionado()
        if r is None:
            return
        f = r.fechas
        resp = QMessageBox.question(
            self,
            "Deshacer pago del resumen",
            f"¿Volver a dejar pendiente el resumen de {NOMBRES_MESES[f.mes]} {f.anio}?\n\n"
            "Los resúmenes posteriores de esos consumos también vuelven a quedar pendientes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            deshacer_pago_resumen(self._repo, r)
            self.hubo_cambios = True
            self._recargar()

    def _cambiar_fechas(self) -> None:
        r = self._resumen_seleccionado()
        tarjeta = self._tarjeta()
        if r is None or tarjeta is None:
            return
        dlg = DialogoFechasResumen(tarjeta, r, parent=self)
        if not dlg.exec():
            return
        f = r.fechas
        if dlg.volver_a_habituales:
            self._repo.borrar_ajuste_resumen(tarjeta.id, f.anio, f.mes)
        else:
            cierre, vence = dlg.fechas()
            habitual = fechas_resumen(tarjeta, f.anio, f.mes)
            if (cierre, vence) == (habitual.cierre, habitual.vencimiento):
                self._repo.borrar_ajuste_resumen(tarjeta.id, f.anio, f.mes)
            else:
                self._repo.guardar_ajuste_resumen(tarjeta.id, f.anio, f.mes, cierre, vence)
        self.hubo_cambios = True
        self._recargar()
