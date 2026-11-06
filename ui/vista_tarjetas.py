from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import formatear_moneda
from models.tarjeta import ConsumoTarjeta, Tarjeta
from repository.categoria_repo import CategoriaRepo
from repository.tarjeta_repo import TarjetaRepo
from services.gasto_service import GastoService
from services.tarjeta_service import (
    _ultimo_dia_mes,
    calcular_saldo_pendiente,
    proyectar_cuotas,
    resumen_mes_por_tarjeta,
)
from ui.dialogo_consumo import DialogoConsumo
from ui.dialogo_tarjeta import DialogoTarjeta


NOMBRES_MESES = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

COLS = [
    "Descripción",
    "Tarjeta",
    "Fecha compra",
    "Total",
    "Cuotas (Pag./Tot.)",
    "Próx. vencimiento",
    "Saldo pendiente",
    "Estado",
]
COL_DESC, COL_TARJETA, COL_FECHA, COL_TOTAL, COL_CUOTAS, COL_VENC, COL_SALDO, COL_ESTADO = range(8)

COLOR_ACTIVO = QColor("#ffffff")
COLOR_FINALIZADO = QColor("#eafaf1")
COLOR_CANCELADO = QColor("#f4f4f4")
COLOR_VENCE_HOY = QColor("#fef9e7")
COLOR_VENCIDO = QColor("#fdedec")

ESTADO_LABEL = {
    "activo": "✅ Activo",
    "finalizado": "☑️ Finalizado",
    "cancelado": "❌ Cancelado",
}


def _centavos_a_decimal(c: int) -> Decimal:
    return Decimal(c) / 100


class TableWidgetItemCustom(QTableWidgetItem):
    """Permite ordenamiento cronológico o numérico en QTableWidget."""

    def __init__(self, texto: str, valor_comparacion=None):
        super().__init__(texto)
        self.valor_comparacion = valor_comparacion

    def __lt__(self, other):
        if (
            isinstance(other, TableWidgetItemCustom)
            and self.valor_comparacion is not None
            and other.valor_comparacion is not None
        ):
            return self.valor_comparacion < other.valor_comparacion
        return super().__lt__(other)


class VistaTarjetas(QWidget):
    """Pestaña de Tarjetas y Cuotas."""

    def __init__(
        self,
        tarjeta_repo: TarjetaRepo,
        gasto_service: GastoService | None = None,
        categoria_repo: CategoriaRepo | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._repo = tarjeta_repo
        self._gasto_service = gasto_service
        self._categoria_repo = categoria_repo

        self._anio = date.today().year
        self._mes = date.today().month
        self._consumos_cargados: list[ConsumoTarjeta] = []
        self._tarjetas_map: dict[int, Tarjeta] = {}
        self._ultimo_id_deshecho: int | None = None

        self._construir_ui()
        self._conectar_atajos()
        self._recargar()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self._crear_panel_resumen())
        layout.addWidget(self._crear_barra_filtros())
        layout.addWidget(self._crear_tabla(), stretch=1)
        layout.addWidget(self._crear_barra_acciones())

    def _crear_panel_resumen(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background: white; border: 1px solid #bdc3c7; border-radius: 6px; }"
        )
        hl = QHBoxLayout(frame)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(20)

        def _card(titulo: str, valor: str = "—", color: str = "#2c3e50") -> tuple[QWidget, QLabel, QLabel]:
            w = QWidget()
            vl = QVBoxLayout(w)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(2)
            lbl_t = QLabel(titulo)
            lbl_t.setStyleSheet("color: #7f8c8d; font-size: 9pt; font-weight: 600;")
            lbl_v = QLabel(valor)
            lbl_v.setStyleSheet(f"color: {color}; font-size: 13pt; font-weight: 700;")
            lbl_sub = QLabel("")
            lbl_sub.setStyleSheet("color: #7f8c8d; font-size: 8.5pt;")
            vl.addWidget(lbl_t)
            vl.addWidget(lbl_v)
            vl.addWidget(lbl_sub)
            return w, lbl_v, lbl_sub

        self._card_mes_w, self._lbl_mes_valor, self._lbl_mes_sub = _card("💳 A pagar este mes", color="#2980b9")
        self._card_deuda_w, self._lbl_deuda_valor, self._lbl_deuda_sub = _card("📊 Deuda total pendiente", color="#e74c3c")
        self._card_limite_w, self._lbl_limite_valor, self._lbl_limite_sub = _card("🏦 Límite disponible", color="#27ae60")

        hl.addWidget(self._card_mes_w)
        hl.addWidget(self._sep())
        hl.addWidget(self._card_deuda_w)
        hl.addWidget(self._sep())
        hl.addWidget(self._card_limite_w)
        hl.addStretch()

        self.btn_pasar_planilla = QPushButton("📥 Pasar a gastos del mes")
        self.btn_pasar_planilla.setProperty("class", "btn-secondary")
        self.btn_pasar_planilla.setToolTip(
            "Registra los totales a pagar de las tarjetas como gastos en la Planilla del mes actual."
        )
        self.btn_pasar_planilla.clicked.connect(self._pasar_a_planilla)
        hl.addWidget(self.btn_pasar_planilla)

        return frame

    def _sep(self) -> QFrame:
        s = QFrame()
        s.setFrameShape(QFrame.Shape.VLine)
        s.setStyleSheet("color: #bdc3c7;")
        return s

    def _crear_barra_filtros(self) -> QWidget:
        w = QWidget()
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        self.combo_filtro_tarjeta = QComboBox()
        self.combo_filtro_tarjeta.addItem("Todas las tarjetas", None)
        self.combo_filtro_tarjeta.currentIndexChanged.connect(self._aplicar_filtros)
        hl.addWidget(QLabel("Tarjeta:"))
        hl.addWidget(self.combo_filtro_tarjeta)

        self.combo_filtro_estado = QComboBox()
        self.combo_filtro_estado.addItem("Todos los estados", None)
        self.combo_filtro_estado.addItem("✅ Activos", "activo")
        self.combo_filtro_estado.addItem("☑️ Finalizados", "finalizado")
        self.combo_filtro_estado.addItem("❌ Cancelados", "cancelado")
        self.combo_filtro_estado.currentIndexChanged.connect(self._aplicar_filtros)
        hl.addWidget(QLabel("Estado:"))
        hl.addWidget(self.combo_filtro_estado)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar por descripción...")
        self.txt_buscar.textChanged.connect(self._aplicar_filtros)
        hl.addWidget(self.txt_buscar, stretch=1)

        self.btn_gestionar = QPushButton("🏦 Gestionar tarjetas")
        self.btn_gestionar.setToolTip("Agregar, editar o desactivar tarjetas")
        self.btn_gestionar.clicked.connect(self._gestionar_tarjetas)
        hl.addWidget(self.btn_gestionar)

        return w

    def _crear_tabla(self) -> QTableWidget:
        self.tabla = QTableWidget(0, len(COLS))
        self.tabla.setHorizontalHeaderLabels(COLS)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSortingEnabled(True)
        self.tabla.verticalHeader().setVisible(False)

        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(COL_DESC, QHeaderView.ResizeMode.Stretch)
        for col in [
            COL_TARJETA,
            COL_FECHA,
            COL_TOTAL,
            COL_CUOTAS,
            COL_VENC,
            COL_SALDO,
            COL_ESTADO,
        ]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.tabla.itemDoubleClicked.connect(self._editar_seleccionado)
        return self.tabla

    def _crear_barra_acciones(self) -> QWidget:
        w = QWidget()
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        self.btn_nuevo = QPushButton("➕ Nuevo consumo")
        self.btn_nuevo.setProperty("class", "btn-primary")
        self.btn_nuevo.setToolTip("Cargar un nuevo consumo (Ctrl+N)")
        self.btn_nuevo.clicked.connect(self._nuevo_consumo)

        self.btn_pagar_cuota = QPushButton("✅ Marcar cuota pagada")
        self.btn_pagar_cuota.setToolTip("Registra el pago de 1 cuota en el consumo seleccionado")
        self.btn_pagar_cuota.clicked.connect(self._marcar_cuota_pagada)

        self.btn_deshacer = QPushButton("↩️ Deshacer pago")
        self.btn_deshacer.setToolTip("Restaura 1 cuota previamente marcada como pagada")
        self.btn_deshacer.clicked.connect(self._deshacer_cuota)

        self.btn_adelantar = QPushButton("⏩ Adelantar / liquidar cuotas")
        self.btn_adelantar.setToolTip("Marca todas las cuotas restantes como pagadas y finaliza el consumo")
        self.btn_adelantar.clicked.connect(self._adelantar_cuotas)

        self.btn_cancelar = QPushButton("❌ Cancelar consumo")
        self.btn_cancelar.setToolTip("Marca el consumo como cancelado (conserva historial)")
        self.btn_cancelar.clicked.connect(self._cancelar_consumo)

        self.btn_editar = QPushButton("✏️ Editar")
        self.btn_editar.setToolTip("Editar datos del consumo seleccionado")
        self.btn_editar.clicked.connect(self._editar_seleccionado)

        for b in [
            self.btn_nuevo,
            self.btn_pagar_cuota,
            self.btn_deshacer,
            self.btn_adelantar,
            self.btn_cancelar,
            self.btn_editar,
        ]:
            hl.addWidget(b)
        hl.addStretch()

        return w

    # ------------------------------------------------------------------
    # Período
    # ------------------------------------------------------------------

    def fijar_periodo(self, anio: int, mes: int) -> None:
        self._anio = anio
        self._mes = mes
        self._actualizar_resumen()

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _recargar(self) -> None:
        tarjetas = self._repo.listar()
        self._tarjetas_map = {t.id: t for t in tarjetas}

        self.combo_filtro_tarjeta.blockSignals(True)
        tarjeta_actual_id = self.combo_filtro_tarjeta.currentData()
        self.combo_filtro_tarjeta.clear()
        self.combo_filtro_tarjeta.addItem("Todas las tarjetas", None)
        for t in tarjetas:
            self.combo_filtro_tarjeta.addItem(t.nombre, t.id)
        if tarjeta_actual_id is not None:
            for i in range(self.combo_filtro_tarjeta.count()):
                if self.combo_filtro_tarjeta.itemData(i) == tarjeta_actual_id:
                    self.combo_filtro_tarjeta.setCurrentIndex(i)
                    break
        self.combo_filtro_tarjeta.blockSignals(False)

        self._consumos_cargados = self._repo.listar_consumos()
        self._aplicar_filtros()
        self._actualizar_resumen()

    def _aplicar_filtros(self) -> None:
        tarjeta_id = self.combo_filtro_tarjeta.currentData()
        estado_filtro = self.combo_filtro_estado.currentData()
        busqueda = self.txt_buscar.text().strip().lower()

        filtrados = []
        for c in self._consumos_cargados:
            if tarjeta_id is not None and c.tarjeta_id != tarjeta_id:
                continue
            if estado_filtro is not None and c.estado != estado_filtro:
                continue
            if busqueda and busqueda not in c.descripcion.lower():
                continue
            filtrados.append(c)

        self._poblar_tabla(filtrados)
        self._actualizar_resumen()

    def _poblar_tabla(self, consumos: list[ConsumoTarjeta]) -> None:
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)
        hoy = date.today()

        for consumo in consumos:
            tarjeta = self._tarjetas_map.get(consumo.tarjeta_id)
            nombre_tarjeta = tarjeta.nombre if tarjeta else "—"

            proxima_venc: date | None = None
            if consumo.estado == "activo" and tarjeta:
                proyectadas = proyectar_cuotas(consumo, tarjeta)
                sin_pagar = [ic for ic in proyectadas if not ic.pagada]
                if sin_pagar:
                    ic = sin_pagar[0]
                    proxima_venc = date(ic.anio, ic.mes, ic.dia_vencimiento)

            row = self.tabla.rowCount()
            self.tabla.insertRow(row)

            # Formatos con ordenamiento natural
            venc_txt = proxima_venc.strftime("%d/%m/%Y") if proxima_venc else "—"
            venc_cmp = proxima_venc if proxima_venc else date(9999, 12, 31)

            saldo_pend = calcular_saldo_pendiente(consumo)
            cuotas_txt = (
                f"{consumo.cuotas_pagadas}/{consumo.cantidad_cuotas} "
                f"({consumo.cuotas_restantes} rest.)"
            )

            items = [
                (COL_DESC, TableWidgetItemCustom(consumo.descripcion, consumo.descripcion.lower()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                (COL_TARJETA, TableWidgetItemCustom(nombre_tarjeta, nombre_tarjeta.lower()), Qt.AlignmentFlag.AlignCenter),
                (COL_FECHA, TableWidgetItemCustom(consumo.fecha_compra, consumo.fecha_compra), Qt.AlignmentFlag.AlignCenter),
                (COL_TOTAL, TableWidgetItemCustom(formatear_moneda(_centavos_a_decimal(consumo.monto_total_cent)), consumo.monto_total_cent), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                (COL_CUOTAS, TableWidgetItemCustom(cuotas_txt, consumo.cuotas_restantes), Qt.AlignmentFlag.AlignCenter),
                (COL_VENC, TableWidgetItemCustom(venc_txt, venc_cmp), Qt.AlignmentFlag.AlignCenter),
                (COL_SALDO, TableWidgetItemCustom(formatear_moneda(_centavos_a_decimal(saldo_pend)), saldo_pend), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                (COL_ESTADO, TableWidgetItemCustom(ESTADO_LABEL.get(consumo.estado, consumo.estado), consumo.estado), Qt.AlignmentFlag.AlignCenter),
            ]

            for col, item, alin in items:
                item.setTextAlignment(alin)
                item.setData(Qt.ItemDataRole.UserRole, consumo.id)
                self.tabla.setItem(row, col, item)

            color_fila = self._color_fila(consumo.estado, proxima_venc, hoy)
            for col in range(len(COLS)):
                it = self.tabla.item(row, col)
                if it:
                    it.setBackground(color_fila)

        self.tabla.setSortingEnabled(True)
        self.tabla.sortByColumn(COL_VENC, Qt.SortOrder.AscendingOrder)

    def _color_fila(self, estado: str, venc: date | None, hoy: date) -> QColor:
        if estado == "cancelado":
            return COLOR_CANCELADO
        if estado == "finalizado":
            return COLOR_FINALIZADO
        if venc is None:
            return COLOR_ACTIVO
        delta = (venc - hoy).days
        if delta < 0:
            return COLOR_VENCIDO
        if delta <= 5:
            return COLOR_VENCE_HOY
        return COLOR_ACTIVO

    def _actualizar_resumen(self) -> None:
        resumenes = resumen_mes_por_tarjeta(self._repo, self._anio, self._mes)
        tarjeta_filtro_id = self.combo_filtro_tarjeta.currentData()

        if tarjeta_filtro_id is not None:
            resumenes_filtrados = [r for r in resumenes if r.tarjeta_id == tarjeta_filtro_id]
            total_mes = sum(r.total_cent for r in resumenes_filtrados)
            t_obj = self._tarjetas_map.get(tarjeta_filtro_id)
            sub_texto = f"Filtro: {t_obj.nombre if t_obj else ''}"
        else:
            total_mes = sum(r.total_cent for r in resumenes)
            if resumenes:
                partes = [
                    f"{r.tarjeta_nombre}: {formatear_moneda(_centavos_a_decimal(r.total_cent))}"
                    for r in resumenes
                ]
                sub_texto = "  ·  ".join(partes[:2])
                if len(partes) > 2:
                    sub_texto += f" (+{len(partes) - 2} más)"
            else:
                sub_texto = "Sin cuotas este mes"

        self._lbl_mes_valor.setText(formatear_moneda(_centavos_a_decimal(total_mes)))
        self._lbl_mes_sub.setText(sub_texto)
        if resumenes:
            tooltip_mes = "\n".join(
                f"• {r.tarjeta_nombre}: {formatear_moneda(_centavos_a_decimal(r.total_cent))}"
                for r in resumenes
            )
            self._card_mes_w.setToolTip(f"Detalle {NOMBRES_MESES[self._mes]} {self._anio}:\n{tooltip_mes}")
        else:
            self._card_mes_w.setToolTip("")

        # Deuda total pendiente (todos los consumos activos)
        activos = self._repo.listar_consumos(estado="activo")
        if tarjeta_filtro_id is not None:
            activos = [c for c in activos if c.tarjeta_id == tarjeta_filtro_id]
        deuda_total = sum(calcular_saldo_pendiente(c) for c in activos)
        self._lbl_deuda_valor.setText(formatear_moneda(_centavos_a_decimal(deuda_total)))
        self._lbl_deuda_sub.setText(f"{len(activos)} consumo(s) activo(s)")

        # Límite disponible
        tarjetas_activas = self._repo.listar(solo_activas=True)
        if tarjeta_filtro_id is not None:
            tarjetas_activas = [t for t in tarjetas_activas if t.id == tarjeta_filtro_id]

        tarjetas_con_limite = [t for t in tarjetas_activas if t.limite_cent is not None]
        if tarjetas_con_limite:
            limite_total = sum(t.limite_cent for t in tarjetas_con_limite if t.limite_cent is not None)
            disponible = max(0, limite_total - deuda_total)
            self._lbl_limite_valor.setText(formatear_moneda(_centavos_a_decimal(disponible)))
            self._lbl_limite_sub.setText(f"Límite total: {formatear_moneda(_centavos_a_decimal(limite_total))}")
        else:
            self._lbl_limite_valor.setText("Sin límite")
            self._lbl_limite_sub.setText("No configurado")

        # Estado del botón Pasar a Planilla
        pendientes_volcar = [r for r in resumenes if not r.ya_volcado_planilla and r.total_cent > 0]
        if not resumenes:
            self.btn_pasar_planilla.setEnabled(False)
            self.btn_pasar_planilla.setText("📥 Sin gastos para pasar")
        elif not pendientes_volcar:
            self.btn_pasar_planilla.setEnabled(False)
            self.btn_pasar_planilla.setText("✅ Volcado en Planilla")
        else:
            self.btn_pasar_planilla.setEnabled(True)
            self.btn_pasar_planilla.setText("📥 Pasar a gastos del mes")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _consumo_seleccionado(self) -> ConsumoTarjeta | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        item = self.tabla.item(fila, COL_DESC)
        if item is None:
            return None
        consumo_id = item.data(Qt.ItemDataRole.UserRole)
        return self._repo.obtener_consumo(consumo_id)

    def _nuevo_consumo(self) -> None:
        tarjetas_activas = [t for t in self._tarjetas_map.values() if t.activa]
        if not tarjetas_activas:
            QMessageBox.information(
                self,
                "Sin tarjetas",
                "Primero agregá una tarjeta usando el botón '🏦 Gestionar tarjetas'.",
            )
            return
        dlg = DialogoConsumo(tarjetas_activas, parent=self)
        if dlg.exec():
            c = dlg.resultado()
            if c:
                self._repo.crear_consumo(c)
                self._recargar()

    def _editar_seleccionado(self) -> None:
        consumo = self._consumo_seleccionado()
        if consumo is None:
            QMessageBox.information(self, "Sin selección", "Seleccioná un consumo para editar.")
            return
        if consumo.estado == "cancelado":
            QMessageBox.information(self, "No editable", "No se puede editar un consumo cancelado.")
            return
        tarjetas_activas = [t for t in self._tarjetas_map.values() if t.activa]
        dlg = DialogoConsumo(tarjetas_activas, consumo=consumo, parent=self)
        if dlg.exec():
            c = dlg.resultado()
            if c:
                self._repo.actualizar_consumo(c)
                self._recargar()

    def _marcar_cuota_pagada(self) -> None:
        consumo = self._consumo_seleccionado()
        if consumo is None:
            QMessageBox.information(self, "Sin selección", "Seleccioná un consumo de la lista.")
            return
        if consumo.estado != "activo":
            QMessageBox.information(
                self,
                "No disponible",
                "Solo se pueden registrar pagos en consumos activos.",
            )
            return
        if consumo.cuotas_restantes == 0:
            QMessageBox.information(
                self,
                "Sin cuotas pendientes",
                "Este consumo ya tiene todas sus cuotas pagadas.",
            )
            return

        self._repo.marcar_cuota_pagada(consumo.id)
        self._ultimo_id_deshecho = consumo.id
        self._recargar()

    def _deshacer_cuota(self) -> None:
        consumo = self._consumo_seleccionado()
        if consumo is None and self._ultimo_id_deshecho is not None:
            consumo = self._repo.obtener_consumo(self._ultimo_id_deshecho)
        if consumo is None:
            QMessageBox.information(
                self, "Sin selección", "Seleccioná un consumo para deshacer el último pago."
            )
            return
        if consumo.cuotas_pagadas == 0:
            QMessageBox.information(
                self, "Sin pagos", "Este consumo no tiene cuotas pagadas para deshacer."
            )
            return

        resp = QMessageBox.question(
            self,
            "Deshacer pago",
            f"¿Deshacer el último pago de '{consumo.descripcion}'?\n\n"
            f"Cuotas pagadas pasarán de {consumo.cuotas_pagadas} a {consumo.cuotas_pagadas - 1}.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._repo.deshacer_ultima_cuota(consumo.id)
            self._recargar()

    def _adelantar_cuotas(self) -> None:
        consumo = self._consumo_seleccionado()
        if consumo is None:
            QMessageBox.information(
                self, "Sin selección", "Seleccioná un consumo para adelantar o liquidar."
            )
            return
        if consumo.estado != "activo":
            QMessageBox.information(
                self, "No disponible", "Solo se pueden liquidar cuotas de consumos activos."
            )
            return
        if consumo.cuotas_restantes == 0:
            QMessageBox.information(
                self, "Sin cuotas pendientes", "Este consumo ya no tiene cuotas por pagar."
            )
            return

        saldo = formatear_moneda(_centavos_a_decimal(calcular_saldo_pendiente(consumo)))
        resp = QMessageBox.question(
            self,
            "Adelantar y liquidar cuotas",
            f"¿Desea adelantar y liquidar todas las cuotas restantes ({consumo.cuotas_restantes}) de '{consumo.descripcion}'?\n\n"
            f"Saldo a cancelar: {saldo}\n"
            "El consumo se marcará como finalizado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._repo.adelantar_cuotas_restantes(consumo.id)
            self._recargar()

    def _cancelar_consumo(self) -> None:
        consumo = self._consumo_seleccionado()
        if consumo is None:
            QMessageBox.information(
                self, "Sin selección", "Seleccioná un consumo para cancelar."
            )
            return
        if consumo.estado == "cancelado":
            QMessageBox.information(
                self, "Ya cancelado", "Este consumo ya se encuentra cancelado."
            )
            return

        saldo = formatear_moneda(_centavos_a_decimal(calcular_saldo_pendiente(consumo)))
        resp = QMessageBox.question(
            self,
            "Cancelar consumo",
            f"¿Cancelar el consumo '{consumo.descripcion}'?\n\n"
            f"Saldo pendiente cancelado: {saldo}\n"
            "El consumo se guardará como cancelado para consulta histórica.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._repo.cancelar_consumo(consumo.id)
            self._recargar()

    def _pasar_a_planilla(self) -> None:
        if self._gasto_service is None or self._categoria_repo is None:
            QMessageBox.warning(
                self, "Servicio no conectado", "El servicio de gastos no está disponible."
            )
            return

        resumenes = resumen_mes_por_tarjeta(self._repo, self._anio, self._mes)
        if not resumenes:
            QMessageBox.information(
                self,
                "Sin cuotas",
                f"No hay cuotas a pagar en {NOMBRES_MESES[self._mes]} {self._anio}.",
            )
            return

        pendientes = [r for r in resumenes if not r.ya_volcado_planilla and r.total_cent > 0]
        if not pendientes:
            QMessageBox.information(
                self,
                "Ya registrado",
                f"Todos los consumos de tarjeta de {NOMBRES_MESES[self._mes]} {self._anio} ya fueron registrados en la Planilla.",
            )
            return

        detalle_lineas = [
            f"• {r.tarjeta_nombre}: {formatear_moneda(_centavos_a_decimal(r.total_cent))}"
            for r in pendientes
        ]
        total_a_pasar = sum(r.total_cent for r in pendientes)
        nombre_mes = NOMBRES_MESES[self._mes]

        mensaje = (
            f"¿Desea registrar los gastos de tarjeta en la Planilla para {nombre_mes} {self._anio}?\n\n"
            + "\n".join(detalle_lineas)
            + f"\n\nTotal a registrar: {formatear_moneda(_centavos_a_decimal(total_a_pasar))}"
        )

        resp = QMessageBox.question(
            self,
            "Pasar a gastos del mes",
            mensaje,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        cat = (
            self._categoria_repo.obtener_por_nombre("Servicios")
            or self._categoria_repo.obtener_por_nombre("Otros")
        )
        if cat is None:
            cats = self._categoria_repo.listar(solo_activas=True)
            cat = cats[0] if cats else None

        if cat is None:
            QMessageBox.warning(
                self,
                "Error",
                "No se encontró una categoría activa para registrar el gasto.",
            )
            return

        for r in pendientes:
            tarjeta = self._tarjetas_map.get(r.tarjeta_id)
            dia_venc = tarjeta.dia_vencimiento if tarjeta else 10
            dia_efectivo = min(dia_venc, _ultimo_dia_mes(self._anio, self._mes))
            fecha_str = f"{self._anio}-{self._mes:02d}-{dia_efectivo:02d}"
            monto_str = str(_centavos_a_decimal(r.total_cent))

            gasto = self._gasto_service.crear(
                fecha=fecha_str,
                monto=monto_str,
                categoria_id=cat.id,
                descripcion=f"Resumen Tarjeta {r.tarjeta_nombre} ({nombre_mes} {self._anio})",
                medio_pago="Crédito",
                cuotas="",
            )
            self._repo.registrar_mes_volcado_planilla(
                tarjeta_id=r.tarjeta_id,
                anio=self._anio,
                mes=self._mes,
                gasto_id=gasto.id,
                total_cent=r.total_cent,
            )

        QMessageBox.information(
            self,
            "Gastos registrados",
            f"Se registraron exitosamente {len(pendientes)} resumen(es) de tarjeta en la Planilla.",
        )
        self._recargar()

    def _gestionar_tarjetas(self) -> None:
        from ui.dialogo_gestion_tarjetas import DialogoGestionTarjetas

        dlg = DialogoGestionTarjetas(self._repo, parent=self)
        dlg.exec()
        self._recargar()

    # ------------------------------------------------------------------
    # Atajos de teclado
    # ------------------------------------------------------------------

    def _conectar_atajos(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._nuevo_consumo)
        QShortcut(QKeySequence("Return"), self, activated=self._editar_seleccionado)
