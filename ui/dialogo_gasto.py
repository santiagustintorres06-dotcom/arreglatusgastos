from datetime import date
from decimal import Decimal

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from config import MEDIOS_DE_PAGO
from models.gasto import Gasto
from repository.categoria_repo import CategoriaRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService, ServiceError


class DialogoGasto(QDialog):
    """Formulario modal para el alta y edición de gastos."""

    def __init__(
        self,
        gasto_service: GastoService,
        categoria_repo: CategoriaRepo,
        miembro_repo: MiembroRepo,
        gasto: Gasto | None = None,
        fecha_inicial: date | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.gasto_service = gasto_service
        self.categoria_repo = categoria_repo
        self.miembro_repo = miembro_repo
        self.gasto_edicion = gasto

        self.setWindowTitle("Editar Gasto" if gasto else "Nuevo Gasto")
        self.setMinimumWidth(380)
        self.setModal(True)

        self._construir_ui(fecha_inicial)
        self._cargar_datos()

    def _construir_ui(self, fecha_inicial: date | None) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setSpacing(10)

        # 1. Selector de Fecha
        self.dt_fecha = QDateEdit()
        self.dt_fecha.setCalendarPopup(True)
        self.dt_fecha.setDisplayFormat("dd/MM/yyyy")
        if fecha_inicial:
            self.dt_fecha.setDate(
                QDate(fecha_inicial.year, fecha_inicial.month, fecha_inicial.day)
            )
        else:
            hoy = date.today()
            self.dt_fecha.setDate(QDate(hoy.year, hoy.month, hoy.day))
        form_layout.addRow("Fecha:", self.dt_fecha)

        # 2. Selector de Categoría
        self.cmb_categoria = QComboBox()
        form_layout.addRow("Categoría:", self.cmb_categoria)

        # 3. Campo de Monto
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Ej: 1250,50 o 1250.50")
        form_layout.addRow("Monto ($):", self.txt_monto)

        # 4. Campo de Descripción
        self.txt_descripcion = QLineEdit()
        self.txt_descripcion.setPlaceholderText("Descripción breve del gasto")
        form_layout.addRow("Descripción:", self.txt_descripcion)

        # 5. Selector de Medio de Pago
        self.cmb_medio_pago = QComboBox()
        self.cmb_medio_pago.addItem("")  # Opción en blanco
        for medio in MEDIOS_DE_PAGO:
            self.cmb_medio_pago.addItem(medio)
        form_layout.addRow("Medio de Pago:", self.cmb_medio_pago)

        # 6. Selector de Miembro que pagó
        self.cmb_miembro = QComboBox()
        form_layout.addRow("Quién Pagó:", self.cmb_miembro)

        layout.addLayout(form_layout)

        # Etiqueta de Error (roja)
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        # Botones de Acción
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancelar)

        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setDefault(True)
        self.btn_guardar.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 6px 14px;"
        )
        self.btn_guardar.clicked.connect(self._guardar)
        btn_layout.addWidget(self.btn_guardar)

        layout.addLayout(btn_layout)

    def _cargar_datos(self) -> None:
        # Cargar Categorías
        categorias = self.categoria_repo.listar(solo_activas=True)
        self.cmb_categoria.clear()
        for cat in categorias:
            self.cmb_categoria.addItem(cat.nombre, cat.id)

        # Cargar Miembros
        miembros = self.miembro_repo.listar()
        self.cmb_miembro.clear()
        self.cmb_miembro.addItem("(Sin especificar)", None)
        for m in miembros:
            self.cmb_miembro.addItem(m.nombre, m.id)

        # Si estamos editando un gasto existente
        if self.gasto_edicion:
            g = self.gasto_edicion
            self.dt_fecha.setDate(QDate(g.fecha.year, g.fecha.month, g.fecha.day))

            # Formatear el monto en el campo de texto
            self.txt_monto.setText(str(g.monto).replace(".", ","))
            self.txt_descripcion.setText(g.descripcion or "")

            # Seleccionar categoría
            idx_cat = self.cmb_categoria.findData(g.categoria_id)
            if idx_cat >= 0:
                self.cmb_categoria.setCurrentIndex(idx_cat)
            else:
                # Si la categoría estaba desactivada, la añadimos para permitir editar sin romper
                cat_inactiva = self.categoria_repo.obtener_por_id(g.categoria_id)
                if cat_inactiva:
                    self.cmb_categoria.addItem(
                        f"{cat_inactiva.nombre} (Inactiva)", cat_inactiva.id
                    )
                    self.cmb_categoria.setCurrentIndex(self.cmb_categoria.count() - 1)

            # Seleccionar medio de pago
            idx_medio = self.cmb_medio_pago.findText(g.medio_pago or "")
            if idx_medio >= 0:
                self.cmb_medio_pago.setCurrentIndex(idx_medio)

            # Seleccionar miembro
            idx_miembro = self.cmb_miembro.findData(g.miembro_id)
            if idx_miembro >= 0:
                self.cmb_miembro.setCurrentIndex(idx_miembro)

    def _guardar(self) -> None:
        self.lbl_error.setVisible(False)
        self.lbl_error.setText("")

        qdate = self.dt_fecha.date()
        fecha_sel = date(qdate.year(), qdate.month(), qdate.day())
        categoria_id = self.cmb_categoria.currentData()
        monto_str = self.txt_monto.text().strip()
        descripcion = self.txt_descripcion.text().strip()
        medio_pago = self.cmb_medio_pago.currentText().strip()
        miembro_id = self.cmb_miembro.currentData()

        try:
            if self.gasto_edicion is None:
                # Crear nuevo gasto
                self.gasto_service.crear(
                    fecha=fecha_sel,
                    monto=monto_str,
                    categoria_id=categoria_id,
                    descripcion=descripcion,
                    medio_pago=medio_pago,
                    miembro_id=miembro_id,
                )
            else:
                # Actualizar gasto existente
                self.gasto_service.actualizar(
                    id_gasto=self.gasto_edicion.id,
                    fecha=fecha_sel,
                    monto=monto_str,
                    categoria_id=categoria_id,
                    descripcion=descripcion,
                    medio_pago=medio_pago,
                    miembro_id=miembro_id,
                )

            self.accept()
        except (ValueError, ServiceError) as e:
            self.lbl_error.setText(str(e))
            self.lbl_error.setVisible(True)
