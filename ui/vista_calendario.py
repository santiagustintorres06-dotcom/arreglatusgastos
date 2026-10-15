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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import formatear_moneda
from models.gasto import Gasto
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.calendario_widget import CalendarioGastosWidget
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
        parent=None,
    ):
        super().__init__(parent)
        self.gasto_service = gasto_service
        self.resumen_service = resumen_service
        self.categoria_repo = categoria_repo
        self.miembro_repo = miembro_repo
        self.gasto_repo = gasto_repo

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

        self.lbl_total_mes = QLabel("Total: $ 0,00")
        self.lbl_total_mes.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #27ae60;"
        )
        layout_h.addWidget(self.lbl_total_mes)

        panel_cal.addWidget(frame_header)

        # Widget de Calendario con mapa de calor
        self.calendario = CalendarioGastosWidget(self)
        panel_cal.addWidget(self.calendario, stretch=1)

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
        layout_det.addWidget(self.lista_gastos, stretch=1)

        # Total del día seleccionado
        self.lbl_total_dia = QLabel("Total del día: $ 0,00")
        self.lbl_total_dia.setStyleSheet(
            "font-weight: bold; color: #2c3e50; font-size: 12px;"
        )
        layout_det.addWidget(self.lbl_total_dia)

        # Botón Agregar gasto en este día
        self.btn_agregar_dia = QPushButton("➕  Agregar gasto en este día")
        self.btn_agregar_dia.setProperty("class", "btn-cal")
        self.btn_agregar_dia.clicked.connect(self._abrir_alta_para_dia)
        layout_det.addWidget(self.btn_agregar_dia)

        self.frame_detalle.setProperty("class", "panel-detalle")
        layout_principal.addWidget(self.frame_detalle, stretch=35)

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
        self.lbl_total_mes.setText(f"Total: {formatear_moneda(total_mes)}")

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
