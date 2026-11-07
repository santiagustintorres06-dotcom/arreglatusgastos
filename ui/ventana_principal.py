from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import formatear_moneda
from paths import DATA_DIR, ruta_manual
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from repository.preferencias_repo import PreferenciasRepo
from repository.tarjeta_repo import TarjetaRepo
from services.alertas import alertas_vencimientos, texto_alerta
from services.calendario_tarjetas import (
    VENCIDO,
    eventos_vencimiento_mes_repo,
    total_tarjetas_sin_volcar_cent,
)
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

TAB_PLANILLA, TAB_CALENDARIO, TAB_TARJETAS = range(3)


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
        preferencias_repo: PreferenciasRepo | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.gasto_service = gasto_service
        self.resumen_service = resumen_service
        self.categoria_repo = categoria_repo
        self.miembro_repo = miembro_repo
        self.gasto_repo = gasto_repo
        self.tarjeta_repo = tarjeta_repo
        # Las preferencias viven en la misma base que las tarjetas
        self.prefs = preferencias_repo or PreferenciasRepo(tarjeta_repo._conn)
        self.aviso_cerrado = False

        hoy = date.today()
        self.anio_actual = hoy.year
        self.mes_actual = hoy.month

        self.setWindowTitle("Organizador de Gastos Familiares")
        self.resize(1150, 720)
        self.setMinimumSize(900, 580)

        self._construir_ui()
        self._conectar_eventos()
        self._conectar_atajos()
        self._aplicar_preferencias()
        self._actualizar_vista_periodo()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

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
        barra_periodo.setSpacing(10)

        self.btn_mes_anterior = QPushButton("◀  Mes anterior")
        self.btn_mes_anterior.setProperty("class", "btn-nav")
        self.btn_mes_anterior.setToolTip("Ir al mes anterior (Alt + ←)")
        self.btn_mes_anterior.clicked.connect(self._retroceder_mes)
        barra_periodo.addWidget(self.btn_mes_anterior)

        self.lbl_periodo = QLabel("")
        self.lbl_periodo.setProperty("class", "lbl-periodo")
        self.lbl_periodo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        barra_periodo.addWidget(self.lbl_periodo, stretch=1)

        self.btn_hoy = QPushButton("Mes actual")
        self.btn_hoy.setProperty("class", "btn-hoy")
        self.btn_hoy.setToolTip("Volver al mes de hoy")
        self.btn_hoy.clicked.connect(self._ir_mes_actual)
        barra_periodo.addWidget(self.btn_hoy)

        self.btn_mes_siguiente = QPushButton("Mes siguiente  ▶")
        self.btn_mes_siguiente.setProperty("class", "btn-nav")
        self.btn_mes_siguiente.setToolTip("Ir al mes siguiente (Alt + →)")
        self.btn_mes_siguiente.clicked.connect(self._avanzar_mes)
        barra_periodo.addWidget(self.btn_mes_siguiente)

        self.btn_opciones = QPushButton("⚙️")
        self.btn_opciones.setProperty("class", "btn-icono")
        self.btn_opciones.setToolTip("Opciones (días de aviso de vencimientos)")
        self.btn_opciones.clicked.connect(self._abrir_opciones)
        barra_periodo.addWidget(self.btn_opciones)

        self.btn_ayuda = QPushButton("❓ Ayuda")
        self.btn_ayuda.setProperty("class", "btn-icono")
        self.btn_ayuda.setToolTip("Abrir el manual de uso (F1)")
        self.btn_ayuda.clicked.connect(self.abrir_manual)
        barra_periodo.addWidget(self.btn_ayuda)

        layout_principal.addWidget(frame_periodo)

        # 2. Aviso de vencimientos (visible pero no molesto: se puede cerrar)
        self.frame_aviso = QFrame()
        self.frame_aviso.setProperty("class", "aviso")
        fila_aviso = QHBoxLayout(self.frame_aviso)
        fila_aviso.setContentsMargins(12, 6, 8, 6)
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setWordWrap(True)
        self.lbl_aviso.setProperty("class", "lbl-aviso")
        fila_aviso.addWidget(self.lbl_aviso, stretch=1)
        btn_ver = QPushButton("🧾 Ver resúmenes")
        btn_ver.clicked.connect(self._ver_resumenes_desde_aviso)
        fila_aviso.addWidget(btn_ver)
        btn_cerrar_aviso = QPushButton("✕")
        btn_cerrar_aviso.setProperty("class", "btn-icono")
        btn_cerrar_aviso.setToolTip("Ocultar el aviso hasta la próxima vez que se abra el programa")
        btn_cerrar_aviso.clicked.connect(self._cerrar_aviso)
        fila_aviso.addWidget(btn_cerrar_aviso)
        self.frame_aviso.setVisible(False)
        layout_principal.addWidget(self.frame_aviso)

        # 3. Contenedor de Pestañas
        self.tabs = QTabWidget()

        self.vista_planilla = VistaPlanilla(
            gasto_service=self.gasto_service,
            resumen_service=self.resumen_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            gasto_repo=self.gasto_repo,
            tarjeta_repo=self.tarjeta_repo,
            parent=self,
        )
        self.tabs.addTab(self.vista_planilla, "📋 Planilla")

        self.vista_calendario = VistaCalendario(
            gasto_service=self.gasto_service,
            resumen_service=self.resumen_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            gasto_repo=self.gasto_repo,
            tarjeta_repo=self.tarjeta_repo,
            parent=self,
        )
        self.tabs.addTab(self.vista_calendario, "📅 Calendario")

        self.vista_tarjetas = VistaTarjetas(
            tarjeta_repo=self.tarjeta_repo,
            gasto_service=self.gasto_service,
            categoria_repo=self.categoria_repo,
            parent=self,
        )
        self.tabs.addTab(self.vista_tarjetas, "💳 Tarjetas / Cuotas")
        for i, ayuda in enumerate(
            ["Gastos del mes (Ctrl+1)", "Calendario con gastos y vencimientos (Ctrl+2)", "Tarjetas y cuotas (Ctrl+3)"]
        ):
            self.tabs.setTabToolTip(i, ayuda)

        layout_principal.addWidget(self.tabs)
        self.setCentralWidget(contenedor_central)

        # 4. Barra de Estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        # Dónde se guardan los datos (ayuda a detectar si se abre otra copia)
        self.btn_carpeta_datos = QPushButton(f"📁 Datos en: {DATA_DIR}")
        self.btn_carpeta_datos.setFlat(True)
        self.btn_carpeta_datos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_carpeta_datos.setProperty("class", "btn-link-status")
        self.btn_carpeta_datos.setToolTip("Abrir la carpeta donde se guardan los datos y respaldos")
        self.btn_carpeta_datos.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))
        )
        self.status_bar.addWidget(self.btn_carpeta_datos)

        # Resumen unificado del mes: Planilla + tarjetas no pasadas = total real
        self.lbl_status_total = QLabel("")
        self.lbl_status_total.setProperty("class", "lbl-status-total")
        self.status_bar.addPermanentWidget(self.lbl_status_total)

    def _conectar_eventos(self) -> None:
        self.gasto_service.gasto_cambiado.connect(self._actualizar_barra_estado)
        # Cambios en tarjetas/cuotas → el Calendario, el total y el aviso se actualizan solos
        self.vista_tarjetas.datos_cambiados.connect(self.vista_calendario.recargar_calendario)
        self.vista_tarjetas.datos_cambiados.connect(self._actualizar_barra_estado)
        self.vista_tarjetas.datos_cambiados.connect(self.actualizar_aviso)

    def _conectar_atajos(self) -> None:
        """Atajos de teclado básicos (se listan en el manual, F1)."""
        atajos = [
            ("Ctrl+N", self._nuevo_segun_pestania),
            ("Ctrl+1", lambda: self.tabs.setCurrentIndex(TAB_PLANILLA)),
            ("Ctrl+2", lambda: self.tabs.setCurrentIndex(TAB_CALENDARIO)),
            ("Ctrl+3", lambda: self.tabs.setCurrentIndex(TAB_TARJETAS)),
            ("Alt+Left", self._retroceder_mes),
            ("Alt+Right", self._avanzar_mes),
            ("F1", self.abrir_manual),
        ]
        self._atajos = []
        for tecla, accion in atajos:
            sc = QShortcut(QKeySequence(tecla), self)
            sc.activated.connect(accion)
            self._atajos.append(sc)

    def closeEvent(self, event) -> None:
        # Guardar la celda que se esté escribiendo en la planilla antes de cerrar
        self.vista_planilla.confirmar_edicion_pendiente()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _nuevo_segun_pestania(self) -> None:
        """Ctrl+N: nuevo gasto, nuevo gasto del día o nuevo consumo según la pestaña."""
        actual = self.tabs.currentIndex()
        if actual == TAB_PLANILLA:
            self.vista_planilla._abrir_alta_gasto()
        elif actual == TAB_CALENDARIO:
            self.vista_calendario._abrir_alta_para_dia()
        else:
            self.vista_tarjetas._nuevo_consumo()

    def abrir_manual(self) -> None:
        ruta = ruta_manual()
        if ruta.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))
        else:
            QMessageBox.information(
                self,
                "Manual",
                f"No se encontró el manual en:\n{ruta}\n\n"
                "Debería estar junto al programa (MANUAL.html).",
            )

    def _abrir_opciones(self) -> None:
        from ui.dialogo_opciones import DialogoOpciones

        if DialogoOpciones(self.prefs, parent=self).exec():
            self.aviso_cerrado = False
            self._aplicar_preferencias()
            self.vista_calendario.recargar_calendario()
            self.vista_tarjetas.recargar()

    def _aplicar_preferencias(self) -> None:
        dias = self.prefs.dias_aviso()
        self.vista_calendario.dias_aviso = dias
        self.vista_tarjetas.dias_aviso = dias
        self.actualizar_aviso()

    def _ver_resumenes_desde_aviso(self) -> None:
        self.tabs.setCurrentIndex(TAB_TARJETAS)
        self.vista_tarjetas._abrir_resumenes()

    def _cerrar_aviso(self) -> None:
        self.aviso_cerrado = True
        self.frame_aviso.setVisible(False)

    def actualizar_aviso(self) -> None:
        """Muestra arriba los vencimientos próximos o vencidos sin pagar."""
        if self.aviso_cerrado or not self.prefs.mostrar_avisos():
            self.frame_aviso.setVisible(False)
            return
        hoy = date.today()
        alertas = alertas_vencimientos(self.tarjeta_repo, hoy=hoy, dias_aviso=self.prefs.dias_aviso())
        if not alertas:
            self.frame_aviso.setVisible(False)
            return
        hay_vencidos = any(a.estado == VENCIDO for a in alertas)
        self.frame_aviso.setProperty("nivel", "vencido" if hay_vencidos else "proximo")
        self.frame_aviso.style().unpolish(self.frame_aviso)
        self.frame_aviso.style().polish(self.frame_aviso)
        lineas = [texto_alerta(a, hoy) for a in alertas[:4]]
        if len(alertas) > 4:
            lineas.append(f"… y {len(alertas) - 4} más")
        self.lbl_aviso.setText("\n".join(lineas))
        self.frame_aviso.setVisible(True)

    # ------------------------------------------------------------------
    # Navegación de meses
    # ------------------------------------------------------------------

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
        """Total real que sale de la casa en el mes: Planilla + tarjetas no pasadas."""
        total_planilla = self.resumen_service.total_mes(self.anio_actual, self.mes_actual)
        eventos = eventos_vencimiento_mes_repo(self.tarjeta_repo, self.anio_actual, self.mes_actual)
        tarjetas = Decimal(total_tarjetas_sin_volcar_cent(eventos)) / 100
        if tarjetas > 0:
            self.lbl_status_total.setText(
                f"Planilla: {formatear_moneda(total_planilla)}   +   "
                f"💳 Tarjetas: {formatear_moneda(tarjetas)}   =   "
                f"Total real del mes: {formatear_moneda(total_planilla + tarjetas)}"
            )
        else:
            self.lbl_status_total.setText(f"Total real del mes: {formatear_moneda(total_planilla)}")
