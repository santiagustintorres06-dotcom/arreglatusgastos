import calendar
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import formatear_moneda
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.vista_planilla import VistaPlanilla

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


class VentanaPrincipal(QMainWindow):
    """Ventana principal con pestañas (Planilla y Calendario) y selector de mes global."""

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

        self.setWindowTitle("Organizador de Gastos Familiares")
        self.resize(1000, 650)

        self._construir_ui()
        self._conectar_eventos()
        self._actualizar_vista_periodo()

    def _construir_ui(self) -> None:
        contenedor_central = QWidget()
        layout_principal = QVBoxLayout(contenedor_central)
        layout_principal.setContentsMargins(10, 8, 10, 8)
        layout_principal.setSpacing(6)

        # 1. Barra Superior con Selector de Mes Global
        barra_periodo = QHBoxLayout()
        barra_periodo.setSpacing(10)

        self.btn_mes_anterior = QPushButton("◀ Mes Anterior")
        self.btn_mes_anterior.clicked.connect(self._retroceder_mes)
        barra_periodo.addWidget(self.btn_mes_anterior)

        self.lbl_periodo = QLabel("")
        font_periodo = QFont()
        font_periodo.setPointSize(13)
        font_periodo.setBold(True)
        self.lbl_periodo.setFont(font_periodo)
        self.lbl_periodo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        barra_periodo.addWidget(self.lbl_periodo, stretch=1)

        self.btn_hoy = QPushButton("Mes Actual")
        self.btn_hoy.clicked.connect(self._ir_mes_actual)
        barra_periodo.addWidget(self.btn_hoy)

        self.btn_mes_siguiente = QPushButton("Mes Siguiente ▶")
        self.btn_mes_siguiente.clicked.connect(self._avanzar_mes)
        barra_periodo.addWidget(self.btn_mes_siguiente)

        layout_principal.addLayout(barra_periodo)

        # 2. Contenedor de Pestañas (Planilla y Calendario)
        self.tabs = QTabWidget()

        # Pestaña 1: Planilla
        self.vista_planilla = VistaPlanilla(
            gasto_service=self.gasto_service,
            resumen_service=self.resumen_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            parent=self,
        )
        self.tabs.addTab(self.vista_planilla, "📋 Vista Planilla")

        # Pestaña 2: Calendario (Placeholder para Etapa 3)
        self.tab_calendario_placeholder = QWidget()
        cal_layout = QVBoxLayout(self.tab_calendario_placeholder)
        lbl_cal = QLabel("Vista Calendario (se implementa en la Etapa 3)")
        lbl_cal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cal_layout.addWidget(lbl_cal)
        self.tabs.addTab(self.tab_calendario_placeholder, "📅 Vista Calendario")

        layout_principal.addWidget(self.tabs)
        self.setCentralWidget(contenedor_central)

        # 3. Barra de Estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status_total = QLabel("")
        self.lbl_status_total.setStyleSheet(
            "font-weight: bold; margin-right: 15px;"
        )
        self.status_bar.addPermanentWidget(self.lbl_status_total)

    def _conectar_eventos(self) -> None:
        self.gasto_service.gasto_cambiado.connect(self._actualizar_barra_estado)

    def _retroceder_mes(self) -> None:
        if self.mes_actual == 1:
            self.mes_actual = 12
            self.anio_actual -= 1
        else:
            self.mes_actual -= 1
        self._actualizar_vista_periodo()

    def _avanzar_mes(self) -> None:
        if self.mes_actual == 12:
            self.mes_actual = 1
            self.anio_actual += 1
        else:
            self.mes_actual += 1
        self._actualizar_vista_periodo()

    def _ir_mes_actual(self) -> None:
        hoy = date.today()
        self.anio_actual = hoy.year
        self.mes_actual = hoy.month
        self._actualizar_vista_periodo()

    def _actualizar_vista_periodo(self) -> None:
        nombre_mes = NOMBRES_MESES[self.mes_actual]
        self.lbl_periodo.setText(f"{nombre_mes} {self.anio_actual}")
        self.vista_planilla.fijar_periodo(self.anio_actual, self.mes_actual)
        self._actualizar_barra_estado()

    def _actualizar_barra_estado(self) -> None:
        total = self.resumen_service.total_mes(self.anio_actual, self.mes_actual)
        self.lbl_status_total.setText(
            f"Gasto Total del Mes: {formatear_moneda(total)}"
        )
