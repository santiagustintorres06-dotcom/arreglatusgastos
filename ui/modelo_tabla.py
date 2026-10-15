from datetime import date
from decimal import Decimal
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal

from config import formatear_moneda, parsear_monto
from models.categoria import Categoria
from models.gasto import Gasto
from models.miembro import Miembro
from services.gasto_service import GastoService, ServiceError


class ModeloTablaGastos(QAbstractTableModel):
    """Modelo de datos tipo tabla para visualizar y editar gastos inline."""

    error_ocurrido = Signal(str)

    COL_FECHA = 0
    COL_CATEGORIA = 1
    COL_DESCRIPCION = 2
    COL_MONTO = 3
    COL_MEDIO_PAGO = 4
    COL_CUOTAS = 5

    CABECERAS = [
        "Fecha",
        "Categoría",
        "Descripción",
        "Monto",
        "Medio de Pago",
        "Cuotas",
    ]

    def __init__(self, gasto_service: GastoService, parent=None):
        super().__init__(parent)
        self.gasto_service = gasto_service
        self.gastos: list[Gasto] = []
        self.categorias: dict[int, Categoria] = {}
        self.miembros: dict[int, Miembro] = {}

        # Fila borrador para inserción rápida al final de la tabla
        self._borrador_nueva_fila = self._nuevo_borrador()

    def _nuevo_borrador(self) -> dict:
        return {
            "fecha": date.today(),
            "categoria_id": None,
            "descripcion": "",
            "monto": None,
            "medio_pago": "",
            "cuotas": "",
            "miembro_id": None,
        }

    def actualizar_catalogos(
        self,
        categorias: list[Categoria],
        miembros: list[Miembro] | None = None,
    ) -> None:
        """Actualiza los diccionarios de categorías y miembros en memoria."""
        self.categorias = {c.id: c for c in categorias if c.id is not None}
        if miembros:
            self.miembros = {m.id: m for m in miembros if m.id is not None}
        # Si el borrador no tiene categoría, asignar la primera por defecto
        if categorias and self._borrador_nueva_fila["categoria_id"] is None:
            self._borrador_nueva_fila["categoria_id"] = categorias[0].id

    def cargar_gastos(self, lista_gastos: list[Gasto]) -> None:
        """Reemplaza la lista completa de gastos."""
        self.beginResetModel()
        self.gastos = list(lista_gastos)
        self._borrador_nueva_fila = self._nuevo_borrador()
        if self.categorias:
            self._borrador_nueva_fila["categoria_id"] = next(
                iter(self.categorias.keys())
            )
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        # +1 por la fila vacía al final para agregar nuevo gasto
        return len(self.gastos) + 1

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.CABECERAS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self.CABECERAS):
                    return self.CABECERAS[section]
            elif orientation == Qt.Orientation.Vertical:
                if section < len(self.gastos):
                    return str(section + 1)
                return "+"  # Indicador de nueva fila
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        es_fila_nueva = row >= len(self.gastos)

        # Manejo de alineación de texto
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == self.COL_MONTO:
                return int(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            if col in (self.COL_FECHA, self.COL_MEDIO_PAGO, self.COL_CUOTAS):
                return int(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

        # Fila vacía al final para nuevo registro
        if es_fila_nueva:
            b = self._borrador_nueva_fila
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
                if col == self.COL_FECHA:
                    return b["fecha"].strftime("%d/%m/%Y") if b["fecha"] else ""
                if col == self.COL_CATEGORIA:
                    cat = self.categorias.get(b["categoria_id"])
                    return cat.nombre if cat else ""
                if col == self.COL_DESCRIPCION:
                    return b["descripcion"]
                if col == self.COL_MONTO:
                    if b["monto"] is not None:
                        return (
                            formatear_moneda(b["monto"])
                            if role == Qt.ItemDataRole.DisplayRole
                            else str(b["monto"])
                        )
                    return ""
                if col == self.COL_MEDIO_PAGO:
                    return b["medio_pago"]
                if col == self.COL_CUOTAS:
                    return b.get("cuotas", "")
            return None

        # Filas existentes de gastos
        gasto = self.gastos[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_FECHA:
                return gasto.fecha.strftime("%d/%m/%Y")
            if col == self.COL_CATEGORIA:
                cat = self.categorias.get(gasto.categoria_id)
                return cat.nombre if cat else f"Cat #{gasto.categoria_id}"
            if col == self.COL_DESCRIPCION:
                return gasto.descripcion
            if col == self.COL_MONTO:
                return formatear_moneda(gasto.monto)
            if col == self.COL_MEDIO_PAGO:
                return gasto.medio_pago
            if col == self.COL_CUOTAS:
                return gasto.cuotas or ""

        if role == Qt.ItemDataRole.EditRole:
            if col == self.COL_FECHA:
                return gasto.fecha.isoformat()
            if col == self.COL_CATEGORIA:
                cat = self.categorias.get(gasto.categoria_id)
                return cat.nombre if cat else ""
            if col == self.COL_DESCRIPCION:
                return gasto.descripcion
            if col == self.COL_MONTO:
                return str(gasto.monto)
            if col == self.COL_MEDIO_PAGO:
                return gasto.medio_pago
            if col == self.COL_CUOTAS:
                return gasto.cuotas or ""

        return None

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()
        es_fila_nueva = row >= len(self.gastos)

        if es_fila_nueva:
            return self._set_data_nueva_fila(col, value)

        # Edición de fila existente
        gasto = self.gastos[row]
        nueva_fecha = gasto.fecha
        nuevo_monto = gasto.monto
        nueva_cat_id = gasto.categoria_id
        nueva_desc = gasto.descripcion
        nuevo_medio = gasto.medio_pago
        nueva_cuotas = gasto.cuotas

        try:
            if col == self.COL_FECHA:
                val_str = str(value).strip()
                if "/" in val_str:
                    partes = val_str.split("/")
                    nueva_fecha = date(
                        int(partes[2]), int(partes[1]), int(partes[0])
                    )
                else:
                    nueva_fecha = date.fromisoformat(val_str)
            elif col == self.COL_CATEGORIA:
                val_str = str(value).strip()
                cat_encontrada = next(
                    (
                        c
                        for c in self.categorias.values()
                        if c.nombre.lower() == val_str.lower()
                    ),
                    None,
                )
                if not cat_encontrada:
                    raise ValueError(f"Categoría '{val_str}' no válida.")
                nueva_cat_id = cat_encontrada.id
            elif col == self.COL_DESCRIPCION:
                nueva_desc = str(value).strip()
            elif col == self.COL_MONTO:
                nuevo_monto = parsear_monto(str(value))
            elif col == self.COL_MEDIO_PAGO:
                nuevo_medio = str(value).strip()
            elif col == self.COL_CUOTAS:
                nueva_cuotas = str(value).strip()

            # Invocar al servicio para validar y persistir
            self.gasto_service.actualizar(
                id_gasto=gasto.id,
                fecha=nueva_fecha,
                monto=nuevo_monto,
                categoria_id=nueva_cat_id,
                descripcion=nueva_desc,
                medio_pago=nuevo_medio,
                cuotas=nueva_cuotas,
            )

            # Actualizar objeto local
            gasto.fecha = nueva_fecha
            gasto.monto = nuevo_monto
            gasto.categoria_id = nueva_cat_id
            gasto.descripcion = nueva_desc
            gasto.medio_pago = nuevo_medio
            gasto.cuotas = nueva_cuotas

            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            return True

        except (ValueError, ServiceError) as e:
            self.error_ocurrido.emit(str(e))
            return False

    def _set_data_nueva_fila(self, col: int, value: Any) -> bool:
        b = self._borrador_nueva_fila
        try:
            if col == self.COL_FECHA:
                val_str = str(value).strip()
                if "/" in val_str:
                    partes = val_str.split("/")
                    b["fecha"] = date(
                        int(partes[2]), int(partes[1]), int(partes[0])
                    )
                else:
                    b["fecha"] = date.fromisoformat(val_str)
            elif col == self.COL_CATEGORIA:
                val_str = str(value).strip()
                cat = next(
                    (
                        c
                        for c in self.categorias.values()
                        if c.nombre.lower() == val_str.lower()
                    ),
                    None,
                )
                if not cat:
                    raise ValueError(f"Categoría '{val_str}' no válida.")
                b["categoria_id"] = cat.id
            elif col == self.COL_DESCRIPCION:
                b["descripcion"] = str(value).strip()
            elif col == self.COL_MONTO:
                b["monto"] = parsear_monto(str(value))
            elif col == self.COL_MEDIO_PAGO:
                b["medio_pago"] = str(value).strip()
            elif col == self.COL_CUOTAS:
                b["cuotas"] = str(value).strip()

            # Si ya tenemos los datos mínimos requeridos (fecha, categoría y monto), creamos el gasto
            if b["fecha"] and b["categoria_id"] and b["monto"] is not None:
                nuevo = self.gasto_service.crear(
                    fecha=b["fecha"],
                    monto=b["monto"],
                    categoria_id=b["categoria_id"],
                    descripcion=b["descripcion"],
                    medio_pago=b["medio_pago"],
                    cuotas=b.get("cuotas", ""),
                )
                # Insertar en la lista interna
                pos = len(self.gastos)
                self.beginInsertRows(QModelIndex(), pos, pos)
                self.gastos.append(nuevo)
                self._borrador_nueva_fila = self._nuevo_borrador()
                if self.categorias:
                    self._borrador_nueva_fila["categoria_id"] = next(
                        iter(self.categorias.keys())
                    )
                self.endInsertRows()

            return True

        except (ValueError, ServiceError) as e:
            self.error_ocurrido.emit(str(e))
            return False

    def obtener_gasto_en_fila(self, row: int) -> Gasto | None:
        if 0 <= row < len(self.gastos):
            return self.gastos[row]
        return None
