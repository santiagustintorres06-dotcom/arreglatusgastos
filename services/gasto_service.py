from datetime import date
from decimal import Decimal
import logging
import sqlite3

from PySide6.QtCore import QCoreApplication, QObject, Signal

from config import MAX_LARGO_DESCRIPCION, parsear_monto
from models.gasto import Gasto
from paths import LOG_DIR
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo

logger = logging.getLogger("gastos_familia")


def _configurar_logger() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "app.log"
    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


_configurar_logger()


class ServiceError(Exception):
    """Excepción para errores de negocio y base de datos en los servicios."""

    pass


class GastoService(QObject):
    """Servicio que aplica reglas de negocio antes de persistir y emite señales de cambio."""

    gasto_cambiado = Signal()

    def __init__(
        self,
        gasto_repo: GastoRepo,
        categoria_repo: CategoriaRepo,
        parent: QObject | None = None,
    ):
        # Asegurar QCoreApplication si aún no existe (útil en tests de consola)
        if QCoreApplication.instance() is None:
            self._app = QCoreApplication([])
        super().__init__(parent)
        self.gasto_repo = gasto_repo
        self.categoria_repo = categoria_repo

    def _validar(
        self,
        fecha: date | str,
        monto: Decimal | str | float | int,
        categoria_id: int,
        descripcion: str = "",
    ) -> tuple[date, Decimal, int, str]:
        # 1. Validación de fecha
        if not fecha:
            raise ValueError("La fecha no puede estar vacía.")
        if isinstance(fecha, str):
            try:
                fecha_obj = date.fromisoformat(fecha.strip())
            except ValueError:
                raise ValueError(
                    f"Formato de fecha inválido '{fecha}'. Se espera YYYY-MM-DD."
                )
        elif isinstance(fecha, date):
            fecha_obj = fecha
        else:
            raise ValueError("Tipo de fecha inválido.")

        # 2. Validación de monto
        if isinstance(monto, (str, float, int)):
            monto_decimal = (
                parsear_monto(str(monto))
                if isinstance(monto, str)
                else Decimal(str(monto)).quantize(Decimal("0.01"))
            )
        elif isinstance(monto, Decimal):
            monto_decimal = monto.quantize(Decimal("0.01"))
        else:
            raise ValueError("El monto no tiene un tipo válido.")

        if monto_decimal <= 0:
            raise ValueError("El monto debe ser estrictamente mayor a 0.")

        # 3. Validación de categoría existente y activa
        if not isinstance(categoria_id, int):
            raise ValueError("La categoría seleccionada no es válida.")
        cat = self.categoria_repo.obtener_por_id(categoria_id)
        if cat is None:
            raise ValueError(f"La categoría con ID {categoria_id} no existe.")
        if not cat.activa:
            raise ValueError(f"La categoría '{cat.nombre}' se encuentra desactivada.")

        # 4. Validación de descripción
        desc_limpia = (descripcion or "").strip()
        if len(desc_limpia) > MAX_LARGO_DESCRIPCION:
            raise ValueError(
                f"La descripción no puede superar los {MAX_LARGO_DESCRIPCION} caracteres."
            )

        return fecha_obj, monto_decimal, categoria_id, desc_limpia

    def crear(
        self,
        fecha: date | str,
        monto: Decimal | str | float | int,
        categoria_id: int,
        descripcion: str = "",
        medio_pago: str = "",
        miembro_id: int | None = None,
    ) -> Gasto:
        fecha_obj, monto_decimal, cat_id, desc_limpia = self._validar(
            fecha, monto, categoria_id, descripcion
        )
        gasto = Gasto(
            fecha=fecha_obj,
            monto=monto_decimal,
            categoria_id=cat_id,
            descripcion=desc_limpia,
            medio_pago=(medio_pago or "").strip(),
            miembro_id=miembro_id,
        )
        try:
            nuevo = self.gasto_repo.crear(gasto)
            self.gasto_cambiado.emit()
            return nuevo
        except sqlite3.Error as e:
            logger.error("Error al crear gasto en BD: %s", e)
            raise ServiceError("Error de base de datos al guardar el gasto.") from e

    def actualizar(
        self,
        id_gasto: int,
        fecha: date | str,
        monto: Decimal | str | float | int,
        categoria_id: int,
        descripcion: str = "",
        medio_pago: str = "",
        miembro_id: int | None = None,
    ) -> None:
        if not id_gasto:
            raise ValueError("Se requiere un ID de gasto válido para actualizar.")

        fecha_obj, monto_decimal, cat_id, desc_limpia = self._validar(
            fecha, monto, categoria_id, descripcion
        )
        gasto = Gasto(
            id=id_gasto,
            fecha=fecha_obj,
            monto=monto_decimal,
            categoria_id=cat_id,
            descripcion=desc_limpia,
            medio_pago=(medio_pago or "").strip(),
            miembro_id=miembro_id,
        )
        try:
            self.gasto_repo.actualizar(gasto)
            self.gasto_cambiado.emit()
        except sqlite3.Error as e:
            logger.error("Error al actualizar gasto %s en BD: %s", id_gasto, e)
            raise ServiceError("Error de base de datos al actualizar el gasto.") from e

    def eliminar(self, id_gasto: int) -> None:
        try:
            self.gasto_repo.eliminar(id_gasto)
            self.gasto_cambiado.emit()
        except sqlite3.Error as e:
            logger.error("Error al eliminar gasto %s en BD: %s", id_gasto, e)
            raise ServiceError("Error de base de datos al eliminar el gasto.") from e

    def obtener_por_id(self, id_gasto: int) -> Gasto | None:
        try:
            return self.gasto_repo.obtener_por_id(id_gasto)
        except sqlite3.Error as e:
            logger.error("Error al obtener gasto %s: %s", id_gasto, e)
            raise ServiceError("Error de base de datos al consultar el gasto.") from e

    def listar_por_mes(
        self,
        anio: int,
        mes: int,
        categoria_id: int | None = None,
        miembro_id: int | None = None,
    ) -> list[Gasto]:
        try:
            return self.gasto_repo.listar_por_mes(
                anio, mes, categoria_id=categoria_id, miembro_id=miembro_id
            )
        except sqlite3.Error as e:
            logger.error("Error al listar gastos de %04d-%02d: %s", anio, mes, e)
            raise ServiceError("Error de base de datos al listar gastos.") from e

    def listar_por_fecha(self, fecha: date | str) -> list[Gasto]:
        try:
            return self.gasto_repo.listar_por_fecha(fecha)
        except sqlite3.Error as e:
            logger.error("Error al listar gastos de fecha %s: %s", fecha, e)
            raise ServiceError("Error de base de datos al listar gastos por fecha.") from e
