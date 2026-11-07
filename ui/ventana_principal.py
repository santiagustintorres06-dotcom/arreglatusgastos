import calendar
from datetime import date

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
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
from paths import DATA_DIR
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from repository.tarjeta_repo import TarjetaRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.vista_calendario import VistaCalendario
from ui.vista_planilla import VistaPlanilla
from ui.vista_tarjetas import VistaTarjetas

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
    """Ventana principal con pestañas (Planilla, Calendario y Tarjetas) y selector de mes global."""

    def __init__(
        self,
        gasto_service: GastoService,
        resumen_service: ResumenService,
        categoria_repo: CategoriaRepo,
        miembro_repo: MiembroRepo,
        gasto_repo: GastoRepo,
        tarjeta_repo: TarjetaRepo,
        parent=None,
    ):
        super().__init__(parent)
        self.gasto_service = gasto_service
        self.resumen_service = resumen_service
        self.categoria_repo = categoria_repo
        self.miembro_repo = miembro_repo
        self.gasto_repo = gasto_repo
        self.tarjeta_repo = tarjeta_repo

        hoy = date.today()
        self.anio_actual = hoy.year
        self.mes_actual = hoy.month

        self.setWindowTitle("Organizador de Gastos Familiares")
        self.resize(1100, 680)

        self._construir_ui()
        self._conectar_eventos()
        self._actualizar_vista_periodo()

    def _construir_ui(self) -> None:
        contenedor_central = QWidget()
        layout_principal = QVBoxLayout(contenedor_central)
        layout_principal.setContentsMargins(10, 8, 10, 8)
        layout_principal.setSpacing(6)

        # 1. Barra Superior con Selector de Mes Global
        frame_periodo = QFrame()
        frame_periodo.setProperty("class", "barra-periodo")
        frame_periodo.setFixedHeight(52)
        barra_periodo = QHBoxLayout(frame_periodo)
        barra_periodo.setContentsMargins(8, 4, 8, 4)
        barra_periodo.setSpacing(12)

        self.btn_mes_anterior = QPushButton("◀  Mes Anterior")
        self.btn_mes_anterior.setProperty("class", "btn-nav")
        self.btn_mes_anterior.clicked.connect(self._retroceder_mes)
        barra_periodo.addWidget(self.btn_mes_anterior)

        self.lbl_periodo = QLabel("")
        self.lbl_periodo.setProperty("class", "lbl-periodo")
        self.lbl_periodo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        barra_periodo.addWidget(self.lbl_periodo, stretch=1)

        self.btn_hoy = QPushButton("Mes Actual")
        self.btn_hoy.setProperty("class", "btn-hoy")
        self.btn_hoy.setToolTip("Ir al mes de hoy")
        self.btn_hoy.clicked.connect(self._ir_mes_actual)
        barra_periodo.addWidget(self.btn_hoy)

        self.btn_mes_siguiente = QPushButton("Mes Siguiente  ▶")
        self.btn_mes_siguiente.setProperty("class", "btn-nav")
        self.btn_mes_siguiente.clicked.connect(self._avanzar_mes)
        barra_periodo.addWidget(self.btn_mes_siguiente)

        layout_principal.addWidget(frame_periodo)

        # 2. Contenedor de Pestañas
        self.tabs = QTabWidget()

        # Pestaña 1: Planilla
        self.vista_planilla = VistaPlanilla(
            gasto_service=self.gasto_service,
            resumen_service=self.resumen_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            gasto_repo=self.gasto_repo,
            parent=self,
        )
        self.tabs.addTab(self.vista_planilla, "📋 Vista Planilla")

        # Pestaña 2: Calendario
        self.vista_calendario = VistaCalendario(
            gasto_service=self.gasto_service,
            resumen_service=self.resumen_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            gasto_repo=self.gasto_repo,
            tarjeta_repo=self.tarjeta_repo,
            parent=self,
        )
        self.tabs.addTab(self.vista_calendario, "📅 Vista Calendario")

        # Pestaña 3: Tarjetas y Cuotas
        self.vista_tarjetas = VistaTarjetas(
            tarjeta_repo=self.tarjeta_repo,
            gasto_service=self.gasto_service,
            categoria_repo=self.categoria_repo,
            parent=self,
        )
        self.tabs.addTab(self.vista_tarjetas, "💳 Tarjetas / Cuotas")

        layout_principal.addWidget(self.tabs)
        self.setCentralWidget(contenedor_central)

        # 3. Barra de Estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        # Dónde se guardan los datos (ayuda a detectar si se abre otra copia)
        self.btn_carpeta_datos = QPushButton(f"📁 Datos en: {DATA_DIR}")
        self.btn_carpeta_datos.setFlat(True)
        self.btn_carpeta_datos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_carpeta_datos.setStyleSheet(
            "QPushButton { color: #ecf0f1; background: transparent; border: none; padding: 0 6px; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        self.btn_carpeta_datos.setToolTip("Abrir la carpeta donde se guardan los datos y respaldos")
        self.btn_carpeta_datos.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))
        )
        self.status_bar.addWidget(self.btn_carpeta_datos)

        self.lbl_status_total = QLabel("")
        self.lbl_status_total.setStyleSheet(
            "font-weight: bold; margin-right: 15px;"
        )
        self.status_bar.addPermanentWidget(self.lbl_status_total)

    def _conectar_eventos(self) -> None:
        self.gasto_service.gasto_cambiado.connect(self._actualizar_barra_estado)
        # Cambios en tarjetas/cuotas → el Calendario se redibuja solo
        self.vista_tarjetas.datos_cambiados.connect(self.vista_calendario.recargar_calendario)

    def closeEvent(self, event) -> None:
        # Guardar la celda que se esté escribiendo en la planilla antes de cerrar
        self.vista_planilla.confirmar_edicion_pendiente()
        super().closeEvent(event)

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
        self.vista_calendario.fijar_periodo(self.anio_actual, self.mes_actual)
        self.vista_tarjetas.fijar_periodo(self.anio_actual, self.mes_actual)
        self._actualizar_barra_estado()

    def _actualizar_barra_estado(self) -> None:
        total = self.resumen_service.total_mes(self.anio_actual, self.mes_actual)
        self.lbl_status_total.setText(
            f"Gasto Total del Mes: {formatear_moneda(total)}"
        )
