from datetime import date
from decimal import Decimal

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import formatear_moneda
from models.gasto import Gasto
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from repository.tarjeta_repo import TarjetaRepo
from services.calendario_tarjetas import (
    ETIQUETA_ESTADO,
    PAGADO,
    PENDIENTE,
    PROXIMO,
    VENCIDO,
    EventoVencimiento,
    eventos_vencimiento_mes_repo,
    total_tarjetas_sin_volcar_cent,
)
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.calendario_widget import COLOR_ESTADO, CalendarioGastosWidget
from ui.dialogo_gasto import DialogoGasto


class VistaCalendario(QWidget):
    """Pestaña mensual de calendario con mapa de calor y panel lateral de detalle."""

    def __init__(
        self,
        gasto_service: GastoService,
        resumen_service: ResumenService,
        categoria_repo: CategoriaRepo,
        miembro_repo: MiembroRepo,
        gasto_repo: GastoRepo,
        tarjeta_repo: TarjetaRepo | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.gasto_service = gasto_service
        self.resumen_service = resumen_service
        self.categoria_repo = categoria_repo
        self.miembro_repo = miembro_repo
        self.gasto_repo = gasto_repo
        self.tarjeta_repo = tarjeta_repo
        self.vencimientos_mes: list[EventoVencimiento] = []

        hoy = date.today()
        self.anio_actual = hoy.year
        self.mes_actual = hoy.month
        self.fecha_seleccionada = hoy
        self.gastos_del_dia_actuales: list[Gasto] = []

        self._construir_ui()
        self._conectar_eventos()
        self.recargar_calendario()

    def _construir_ui(self) -> None:
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(10, 10, 10, 10)
        layout_principal.setSpacing(12)

        # ----------------- PANEL IZQUIERDO: CALENDARIO -----------------
        panel_cal = QVBoxLayout()
        panel_cal.setSpacing(6)

        # Encabezado del calendario con métricas del mes
        frame_header = QFrame()
        frame_header.setFrameShape(QFrame.Shape.StyledPanel)
        layout_h = QHBoxLayout(frame_header)
        layout_h.setContentsMargins(8, 6, 8, 6)

        self.lbl_info_mes = QLabel("Totales del mes")
        self.lbl_info_mes.setStyleSheet("font-weight: bold; color: #34495e;")
        layout_h.addWidget(self.lbl_info_mes)

        layout_h.addStretch()

        self.lbl_total_mes = QLabel("Gastos: $ 0,00")
        self.lbl_total_mes.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #27ae60;"
        )
        layout_h.addWidget(self.lbl_total_mes)

        # Cuotas de tarjeta del mes que todavía no se pasaron a la Planilla
        self.lbl_tarjetas_mes = QLabel("")
        self.lbl_tarjetas_mes.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #2471a3; margin-left: 12px;"
        )
        layout_h.addWidget(self.lbl_tarjetas_mes)

        panel_cal.addWidget(frame_header)

        # Widget de Calendario con mapa de calor
        self.calendario = CalendarioGastosWidget(self)
        panel_cal.addWidget(self.calendario, stretch=1)

        # Leyenda de colores de los vencimientos de tarjeta
        if self.tarjeta_repo is not None:
            panel_cal.addLayout(self._crear_leyenda())

        layout_principal.addLayout(panel_cal, stretch=65)

        # ----------------- PANEL DERECHO: DETALLE DEL DÍA -----------------
        self.frame_detalle = QFrame()
        self.frame_detalle.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_detalle.setMinimumWidth(300)
        layout_det = QVBoxLayout(self.frame_detalle)
        layout_det.setContentsMargins(10, 10, 10, 10)
        layout_det.setSpacing(8)

        # Título del día seleccionado
        self.lbl_titulo_dia = QLabel("Gastos del día")
        font_tit = QFont()
        font_tit.setPointSize(11)
        font_tit.setBold(True)
        self.lbl_titulo_dia.setFont(font_tit)
        layout_det.addWidget(self.lbl_titulo_dia)

        # Lista de gastos del día
        self.lista_gastos = QListWidget()
        self.lista_gastos.setStyleSheet(
            "QListWidget::item { padding: 6px; border-bottom: 1px solid #ecf0f1; }"
        )
        self.lista_gastos.itemDoubleClicked.connect(
            self._editar_gasto_seleccionado
        )
        self.lista_gastos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lista_gastos.customContextMenuRequested.connect(self._mostrar_menu_contextual_dia)
        self.lista_gastos.keyPressEvent = self._lista_key_press
        layout_det.addWidget(self.lista_gastos, stretch=1)

        # Total del día seleccionado
        self.lbl_total_dia = QLabel("Total del día: $ 0,00")
        self.lbl_total_dia.setStyleSheet(
            "font-weight: bold; color: #2c3e50; font-size: 12px;"
        )
        layout_det.addWidget(self.lbl_total_dia)

        # Botones de acción del día
        layout_btns_dia = QHBoxLayout()
        layout_btns_dia.setSpacing(6)

        self.btn_agregar_dia = QPushButton("➕  Agregar")
        self.btn_agregar_dia.setProperty("class", "btn-cal")
        self.btn_agregar_dia.clicked.connect(self._abrir_alta_para_dia)
        layout_btns_dia.addWidget(self.btn_agregar_dia, stretch=1)

        self.btn_eliminar_dia = QPushButton("🗑️  Eliminar")
        self.btn_eliminar_dia.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; padding: 7px; border-radius: 4px;"
        )
        self.btn_eliminar_dia.clicked.connect(self._eliminar_gasto_seleccionado_dia)
        layout_btns_dia.addWidget(self.btn_eliminar_dia, stretch=1)

        layout_det.addLayout(layout_btns_dia)

        # Vencimientos de tarjeta del día seleccionado (oculto si no hay)
        self.lbl_titulo_venc = QLabel("💳 Vencimientos de tarjeta")
        self.lbl_titulo_venc.setFont(font_tit)
        layout_det.addWidget(self.lbl_titulo_venc)

        self.lista_vencimientos = QListWidget()
        self.lista_vencimientos.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.lista_vencimientos.setWordWrap(True)
        self.lista_vencimientos.setStyleSheet("QListWidget::item { padding: 3px 6px; }")
        layout_det.addWidget(self.lista_vencimientos, stretch=1)

        self.lbl_titulo_venc.setVisible(False)
        self.lista_vencimientos.setVisible(False)

        self.frame_detalle.setProperty("class", "panel-detalle")
        layout_principal.addWidget(self.frame_detalle, stretch=35)

    def _crear_leyenda(self) -> QHBoxLayout:
        leyenda = QHBoxLayout()
        leyenda.setSpacing(14)
        leyenda.addWidget(QLabel("Vencimientos de tarjeta:"))
        for estado in (PENDIENTE, PROXIMO, VENCIDO, PAGADO):
            chip = QLabel(f"  {ETIQUETA_ESTADO[estado]}  ")
            chip.setStyleSheet(
                f"background-color: {COLOR_ESTADO[estado]}; color: white;"
                " font-weight: bold; border-radius: 4px; padding: 2px 4px;"
            )
            leyenda.addWidget(chip)
        leyenda.addStretch()
        return leyenda

    def _conectar_eventos(self) -> None:
        # Clic en un día del calendario
        self.calendario.clicked.connect(self._al_seleccionar_dia)
        self.calendario.currentPageChanged.connect(self._al_cambiar_pagina)

        # Reactivo a cambios en los gastos
        self.gasto_service.gasto_cambiado.connect(self.recargar_calendario)

    def fijar_periodo(self, anio: int, mes: int) -> None:
        """Sincroniza el período del calendario con la barra superior de la app."""
        if self.anio_actual != anio or self.mes_actual != mes:
            self.anio_actual = anio
            self.mes_actual = mes
            self.calendario.setCurrentPage(anio, mes)
            # Seleccionar el primer día del mes
            self.fecha_seleccionada = date(anio, mes, 1)
            self.calendario.setSelectedDate(QDate(anio, mes, 1))
            self.recargar_calendario()

    def _al_cambiar_pagina(self, anio: int, mes: int) -> None:
        self.anio_actual = anio
        self.mes_actual = mes
        self.recargar_calendario()

    def _al_seleccionar_dia(self, qdate: QDate) -> None:
        self.fecha_seleccionada = date(qdate.year(), qdate.month(), qdate.day())
        self._actualizar_panel_lateral()

    def recargar_calendario(self) -> None:
        """Consulta los totales por día y actualiza el mapa de calor y el panel lateral."""
        totales = self.resumen_service.totales_por_dia(
            self.anio_actual, self.mes_actual
        )
        self.calendario.actualizar_totales(totales)

        total_mes = self.resumen_service.total_mes(
            self.anio_actual, self.mes_actual
        )
        self.lbl_total_mes.setText(f"Gastos: {formatear_moneda(total_mes)}")

        # Vencimientos de tarjeta (leídos de las tablas de tarjetas, sin duplicar datos)
        if self.tarjeta_repo is not None:
            self.vencimientos_mes = eventos_vencimiento_mes_repo(
                self.tarjeta_repo, self.anio_actual, self.mes_actual
            )
        else:
            self.vencimientos_mes = []
        self.calendario.actualizar_vencimientos(self.vencimientos_mes)

        # Lo ya pasado a la Planilla está dentro de "Gastos": no se suma dos veces
        sin_volcar = Decimal(total_tarjetas_sin_volcar_cent(self.vencimientos_mes)) / 100
        if sin_volcar > 0:
            self.lbl_tarjetas_mes.setText(
                f"+ 💳 Tarjetas: {formatear_moneda(sin_volcar)}"
                f"  =  Total real: {formatear_moneda(total_mes + sin_volcar)}"
            )
            self.lbl_tarjetas_mes.setToolTip(
                "Cuotas de tarjeta de este mes que todavía no se pasaron a la Planilla.\n"
                "Las que ya se pasaron figuran dentro de 'Gastos'."
            )
        else:
            self.lbl_tarjetas_mes.setText("")
            self.lbl_tarjetas_mes.setToolTip("")

        self._actualizar_panel_lateral()

    def _actualizar_panel_lateral(self) -> None:
        f = self.fecha_seleccionada
        self.lbl_titulo_dia.setText(f"Gastos del {f.day:02d}/{f.month:02d}/{f.year}")

        # Listar gastos de la fecha seleccionada
        self.gastos_del_dia_actuales = self.gasto_service.listar_por_fecha(f)
        self.lista_gastos.clear()

        categorias = {c.id: c for c in self.categoria_repo.listar(solo_activas=False)}

        total_dia = Decimal("0.00")
        for g in self.gastos_del_dia_actuales:
            total_dia += g.monto
            cat = categorias.get(g.categoria_id)
            nom_cat = cat.nombre if cat else "General"
            desc = f" - {g.descripcion}" if g.descripcion else ""
            texto = f"[{nom_cat}] {formatear_moneda(g.monto)}{desc}"

            item = QListWidgetItem(texto)
            if cat and cat.color:
                item.setForeground(QColor(cat.color))
            self.lista_gastos.addItem(item)

        if not self.gastos_del_dia_actuales:
            item_vacio = QListWidgetItem("No hay gastos registrados en este día.")
            item_vacio.setForeground(QColor("#7f8c8d"))
            self.lista_gastos.addItem(item_vacio)

        self.lbl_total_dia.setText(f"Total del día: {formatear_moneda(total_dia)}")
        self._actualizar_vencimientos_del_dia()

    def _actualizar_vencimientos_del_dia(self) -> None:
        """Muestra el detalle de los vencimientos de tarjeta del día elegido."""
        eventos = [e for e in self.vencimientos_mes if e.fecha == self.fecha_seleccionada]
        self.lista_vencimientos.clear()
        hay = bool(eventos)
        self.lbl_titulo_venc.setVisible(hay)
        self.lista_vencimientos.setVisible(hay)
        if not hay:
            return

        font_negrita = QFont()
        font_negrita.setBold(True)
        for ev in eventos:
            total = formatear_moneda(Decimal(ev.total_cent) / 100)
            cabecera = QListWidgetItem(
                f"{ev.tarjeta_nombre} — {total}  ({ETIQUETA_ESTADO[ev.estado]})"
            )
            cabecera.setFont(font_negrita)
            cabecera.setForeground(QColor(COLOR_ESTADO[ev.estado]))
            self.lista_vencimientos.addItem(cabecera)

            for c in ev.cuotas:
                monto = formatear_moneda(Decimal(c.monto_cent) / 100)
                marca = "  ✔ pagada" if c.pagada else ""
                item = QListWidgetItem(
                    f"    • {c.descripcion} — cuota {c.numero_cuota}/{c.total_cuotas}: {monto}{marca}"
                )
                if c.pagada:
                    item.setForeground(QColor(COLOR_ESTADO[PAGADO]))
                self.lista_vencimientos.addItem(item)

            if ev.estado != PAGADO and ev.pendiente_cent != ev.total_cent:
                falta = formatear_moneda(Decimal(ev.pendiente_cent) / 100)
                self.lista_vencimientos.addItem(QListWidgetItem(f"    Falta pagar: {falta}"))
            if ev.volcado_planilla:
                aviso = QListWidgetItem("    📥 Ya registrado en la Planilla como gasto")
                aviso.setForeground(QColor("#7f8c8d"))
                self.lista_vencimientos.addItem(aviso)

    def _abrir_alta_para_dia(self) -> None:
        dialogo = DialogoGasto(
            gasto_service=self.gasto_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            fecha_inicial=self.fecha_seleccionada,
            parent=self,
        )
        dialogo.exec()

    def _editar_gasto_seleccionado(self, item: QListWidgetItem) -> None:
        fila = self.lista_gastos.row(item)
        if 0 <= fila < len(self.gastos_del_dia_actuales):
            gasto = self.gastos_del_dia_actuales[fila]
            dialogo = DialogoGasto(
                gasto_service=self.gasto_service,
                categoria_repo=self.categoria_repo,
                miembro_repo=self.miembro_repo,
                gasto=gasto,
                parent=self,
            )
            dialogo.exec()

    def _eliminar_gasto_seleccionado_dia(self) -> None:
        fila = self.lista_gastos.currentRow()
        if 0 <= fila < len(self.gastos_del_dia_actuales):
            gasto = self.gastos_del_dia_actuales[fila]
            res = QMessageBox.question(
                self,
                "Confirmar eliminación",
                f"¿Estás seguro de que deseas eliminar este gasto de {formatear_moneda(gasto.monto)}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if res == QMessageBox.StandardButton.Yes:
                self.gasto_service.eliminar(gasto.id)
        else:
            QMessageBox.information(
                self,
                "Eliminar Gasto",
                "Seleccioná primero un gasto de la lista para eliminarlo.",
            )

    def _mostrar_menu_contextual_dia(self, pos) -> None:
        item = self.lista_gastos.itemAt(pos)
        if not item:
            return
        fila = self.lista_gastos.row(item)
        if not (0 <= fila < len(self.gastos_del_dia_actuales)):
            return

        menu = QMenu(self)
        accion_editar = menu.addAction("✏️  Editar gasto")
        accion_eliminar = menu.addAction("🗑️  Eliminar gasto")

        seleccionada = menu.exec(self.lista_gastos.mapToGlobal(pos))
        if seleccionada == accion_editar:
            self._editar_gasto_seleccionado(item)
        elif seleccionada == accion_eliminar:
            self.lista_gastos.setCurrentRow(fila)
            self._eliminar_gasto_seleccionado_dia()

    def _lista_key_press(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._eliminar_gasto_seleccionado_dia()
        else:
            QListWidget.keyPressEvent(self.lista_gastos, event)

