from datetime import date
from decimal import Decimal

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from config import formatear_moneda
from models.gasto import Gasto
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from services.export_service import ExportService
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.dialogo_gasto import DialogoGasto
from ui.modelo_tabla import ModeloTablaGastos
from ui.delegados import (
    EditorFechaDelegate,
    ComboCategoriaDelegate,
    ComboMedioPagoDelegate,
    ComboMiembroDelegate,
)


class VistaPlanilla(QWidget):
    """Pestaña tipo Excel donde se cargan, editan y filtran los gastos del mes seleccionado."""

    def __init__(
        self,
        gasto_service: GastoService,
        resumen_service: ResumenService,
        categoria_repo: CategoriaRepo,
        miembro_repo: MiembroRepo,
        gasto_repo: GastoRepo | None = None,
        export_service: ExportService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.gasto_service = gasto_service
        self.resumen_service = resumen_service
        self.categoria_repo = categoria_repo
        self.miembro_repo = miembro_repo
        self.gasto_repo = gasto_repo
        self.export_service = export_service or (
            ExportService(
                gasto_repo=gasto_repo,
                categoria_repo=categoria_repo,
                miembro_repo=miembro_repo,
                resumen_service=resumen_service,
            )
            if gasto_repo
            else None
        )

        self.anio_actual = date.today().year
        self.mes_actual = date.today().month

        self._construir_ui()
        self._conectar_eventos()
        self.recargar_catalogos()
        self.recargar_gastos()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Barra de Filtros y Acciones
        barra_filtros = QHBoxLayout()
        barra_filtros.setSpacing(10)

        barra_filtros.addWidget(QLabel("Filtrar por:"))

        # Filtro de Categoría
        self.cmb_filtro_cat = QComboBox()
        self.cmb_filtro_cat.addItem("Todas las categorías", None)
        barra_filtros.addWidget(self.cmb_filtro_cat)

        # Filtro de Miembro
        self.cmb_filtro_miembro = QComboBox()
        self.cmb_filtro_miembro.addItem("Todos los miembros", None)
        barra_filtros.addWidget(self.cmb_filtro_miembro)

        # Búsqueda libre por texto
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar en descripción...")
        self.txt_buscar.setClearButtonEnabled(True)
        barra_filtros.addWidget(self.txt_buscar)

        barra_filtros.addStretch()

        # Botón Agregar Gasto
        self.btn_nuevo = QPushButton("+ Agregar Gasto")
        self.btn_nuevo.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;"
        )
        self.btn_nuevo.clicked.connect(self._abrir_alta_gasto)
        barra_filtros.addWidget(self.btn_nuevo)

        # Botón Exportar
        self.btn_exportar = QPushButton("📥 Exportar...")
        self.btn_exportar.setStyleSheet(
            "background-color: #34495e; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;"
        )
        self.btn_exportar.clicked.connect(self._exportar_datos)
        barra_filtros.addWidget(self.btn_exportar)

        layout.addLayout(barra_filtros)

        # 2. Tabla Principal
        self.modelo = ModeloTablaGastos(self.gasto_service, self)
        self.tabla = QTableView()
        self.tabla.setModel(self.modelo)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tabla.doubleClicked.connect(self._editar_gasto_seleccionado)

        # Ajuste de cabeceras
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(
            ModeloTablaGastos.COL_FECHA, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            ModeloTablaGastos.COL_CATEGORIA,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            ModeloTablaGastos.COL_DESCRIPCION, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            ModeloTablaGastos.COL_MONTO, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            ModeloTablaGastos.COL_MEDIO_PAGO,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            ModeloTablaGastos.COL_PAGO, QHeaderView.ResizeMode.ResizeToContents
        )

        # Delegados personalizados para desplegables y selector de fecha inline
        self.tabla.setItemDelegateForColumn(
            ModeloTablaGastos.COL_FECHA, EditorFechaDelegate(self)
        )
        self.tabla.setItemDelegateForColumn(
            ModeloTablaGastos.COL_CATEGORIA,
            ComboCategoriaDelegate(
                lambda: self.categoria_repo.listar(solo_activas=True), self
            ),
        )
        self.tabla.setItemDelegateForColumn(
            ModeloTablaGastos.COL_MEDIO_PAGO, ComboMedioPagoDelegate(self)
        )
        self.tabla.setItemDelegateForColumn(
            ModeloTablaGastos.COL_PAGO,
            ComboMiembroDelegate(self.miembro_repo.listar, self),
        )

        layout.addWidget(self.tabla)

        # 3. Pie de Tabla con Totales y Subtotales
        pie_frame = QFrame()
        pie_frame.setFrameShape(QFrame.Shape.StyledPanel)
        pie_layout = QHBoxLayout(pie_frame)
        pie_layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_conteo = QLabel("0 gastos")
        pie_layout.addWidget(self.lbl_conteo)

        self.lbl_subtotales = QLabel("")
        self.lbl_subtotales.setStyleSheet("color: #555;")
        pie_layout.addWidget(self.lbl_subtotales)

        pie_layout.addStretch()

        self.lbl_total_mes = QLabel("Total: $ 0,00")
        self.lbl_total_mes.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #2c3e50;"
        )
        pie_layout.addWidget(self.lbl_total_mes)

        layout.addWidget(pie_frame)

    def _conectar_eventos(self) -> None:
        self.cmb_filtro_cat.currentIndexChanged.connect(self._aplicar_filtros)
        self.cmb_filtro_miembro.currentIndexChanged.connect(
            self._aplicar_filtros
        )
        self.txt_buscar.textChanged.connect(self._aplicar_filtros)

        # Reaccionar a cambios globales en los datos (sincronización reactiva)
        self.gasto_service.gasto_cambiado.connect(self.recargar_gastos)
        self.modelo.error_ocurrido.connect(self._mostrar_error)

    def fijar_periodo(self, anio: int, mes: int) -> None:
        """Actualiza el mes/año visualizado."""
        self.anio_actual = anio
        self.mes_actual = mes
        self.recargar_gastos()

    def recargar_catalogos(self) -> None:
        """Actualiza las opciones de categorías y miembros en los combos."""
        categorias = self.categoria_repo.listar(solo_activas=False)
        miembros = self.miembro_repo.listar()
        self.modelo.actualizar_catalogos(categorias, miembros)

        # Actualizar combo filtro de categorías
        cat_seleccionada = self.cmb_filtro_cat.currentData()
        self.cmb_filtro_cat.blockSignals(True)
        self.cmb_filtro_cat.clear()
        self.cmb_filtro_cat.addItem("Todas las categorías", None)
        for c in categorias:
            self.cmb_filtro_cat.addItem(c.nombre, c.id)
        idx_c = self.cmb_filtro_cat.findData(cat_seleccionada)
        if idx_c >= 0:
            self.cmb_filtro_cat.setCurrentIndex(idx_c)
        self.cmb_filtro_cat.blockSignals(False)

        # Actualizar combo filtro de miembros
        miembro_sel = self.cmb_filtro_miembro.currentData()
        self.cmb_filtro_miembro.blockSignals(True)
        self.cmb_filtro_miembro.clear()
        self.cmb_filtro_miembro.addItem("Todos los miembros", None)
        for m in miembros:
            self.cmb_filtro_miembro.addItem(m.nombre, m.id)
        idx_m = self.cmb_filtro_miembro.findData(miembro_sel)
        if idx_m >= 0:
            self.cmb_filtro_miembro.setCurrentIndex(idx_m)
        self.cmb_filtro_miembro.blockSignals(False)

    def recargar_gastos(self) -> None:
        """Consulta los gastos en la base de datos para el mes activo y actualiza la vista."""
        cat_id = self.cmb_filtro_cat.currentData()
        miembro_id = self.cmb_filtro_miembro.currentData()

        todos_los_gastos = self.gasto_service.listar_por_mes(
            self.anio_actual,
            self.mes_actual,
            categoria_id=cat_id,
            miembro_id=miembro_id,
        )

        texto_busqueda = self.txt_buscar.text().strip().lower()
        if texto_busqueda:
            todos_los_gastos = [
                g
                for g in todos_los_gastos
                if texto_busqueda in g.descripcion.lower()
            ]

        self.modelo.cargar_gastos(todos_los_gastos)
        self._actualizar_pie(todos_los_gastos)

    def _aplicar_filtros(self) -> None:
        self.recargar_gastos()

    def _actualizar_pie(self, gastos: list[Gasto]) -> None:
        total = sum((g.monto for g in gastos), Decimal("0.00"))
        self.lbl_conteo.setText(
            f"{len(gastos)} gasto{'s' if len(gastos) != 1 else ''}"
        )
        self.lbl_total_mes.setText(f"Total: {formatear_moneda(total)}")

    def _mostrar_error(self, mensaje: str) -> None:
        QMessageBox.warning(self, "Error de Validación", mensaje)

    def _abrir_alta_gasto(self) -> None:
        dialogo = DialogoGasto(
            gasto_service=self.gasto_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            fecha_inicial=date(self.anio_actual, self.mes_actual, 1),
            parent=self,
        )
        dialogo.exec()

    def _editar_gasto_seleccionado(self, index) -> None:
        gasto = self.modelo.obtener_gasto_en_fila(index.row())
        if not gasto:
            return
        dialogo = DialogoGasto(
            gasto_service=self.gasto_service,
            categoria_repo=self.categoria_repo,
            miembro_repo=self.miembro_repo,
            gasto=gasto,
            parent=self,
        )
        dialogo.exec()

    def _mostrar_menu_contextual(self, pos: QPoint) -> None:
        index = self.tabla.indexAt(pos)
        if not index.isValid():
            return
        gasto = self.modelo.obtener_gasto_en_fila(index.row())
        if not gasto:
            return

        menu = QMenu(self)
        accion_editar = menu.addAction("Editar gasto")
        accion_duplicar = menu.addAction("Duplicar gasto")
        accion_eliminar = menu.addAction("Eliminar gasto")

        seleccionada = menu.exec(self.tabla.viewport().mapToGlobal(pos))
        if seleccionada == accion_editar:
            self._editar_gasto_seleccionado(index)
        elif seleccionada == accion_duplicar:
            self._duplicar_gasto(gasto)
        elif seleccionada == accion_eliminar:
            self._eliminar_gasto(gasto)

    def _duplicar_gasto(self, gasto: Gasto) -> None:
        self.gasto_service.crear(
            fecha=gasto.fecha,
            monto=gasto.monto,
            categoria_id=gasto.categoria_id,
            descripcion=f"{gasto.descripcion} (copia)"
            if gasto.descripcion
            else "Copia",
            medio_pago=gasto.medio_pago,
            miembro_id=gasto.miembro_id,
        )

    def _eliminar_gasto(self, gasto: Gasto) -> None:
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar este gasto de {formatear_moneda(gasto.monto)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            self.gasto_service.eliminar(gasto.id)

    def _exportar_datos(self) -> None:
        if not self.export_service:
            QMessageBox.warning(
                self, "Exportación", "El servicio de exportación no está disponible."
            )
            return

        nombre_sugerido = f"Gastos_{self.anio_actual}_{self.mes_actual:02d}.xlsx"
        ruta_archivo, filtro = QFileDialog.getSaveFileName(
            self,
            "Exportar Gastos",
            nombre_sugerido,
            "Archivos de Excel (*.xlsx);;Archivos CSV (*.csv)",
        )
        if not ruta_archivo:
            return

        try:
            if ruta_archivo.endswith(".csv") or "CSV" in filtro:
                self.export_service.exportar_a_csv(
                    ruta_archivo, self.anio_actual, self.mes_actual
                )
            else:
                if not ruta_archivo.endswith(".xlsx"):
                    ruta_archivo += ".xlsx"
                self.export_service.exportar_a_excel(
                    ruta_archivo, self.anio_actual, self.mes_actual
                )

            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Los gastos fueron exportados correctamente a:\n{ruta_archivo}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error de Exportación",
                f"No se pudo completar la exportación:\n{e}",
            )
