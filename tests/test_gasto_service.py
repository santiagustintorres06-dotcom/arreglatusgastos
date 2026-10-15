from datetime import date
from decimal import Decimal
import pytest

from models.categoria import Categoria
from repository.categoria_repo import CategoriaRepo
from services.gasto_service import GastoService


def test_gasto_service_crear_y_emision_de_senial(
    gasto_service: GastoService, categoria_repo: CategoriaRepo
):
    cat = categoria_repo.obtener_por_nombre("Supermercado")
    assert cat is not None

    seniales_emitidas = 0

    def slot():
        nonlocal seniales_emitidas
        seniales_emitidas += 1

    gasto_service.gasto_cambiado.connect(slot)

    # Crear gasto pasando texto con coma decimal
    gasto = gasto_service.crear(
        fecha="2026-10-15",
        monto="1.250,50",
        categoria_id=cat.id,
        descripcion=" Compra del mes  ",
        medio_pago="Tarjeta Débito",
    )

    assert gasto.id is not None
    assert gasto.monto == Decimal("1250.50")
    assert gasto.descripcion == "Compra del mes"
    assert gasto.fecha == date(2026, 10, 15)
    assert seniales_emitidas == 1

    # Actualizar gasto
    gasto_service.actualizar(
        id_gasto=gasto.id,
        fecha=date(2026, 10, 16),
        monto=Decimal("1300.00"),
        categoria_id=cat.id,
        descripcion="Ajuste",
    )
    assert seniales_emitidas == 2

    # Eliminar gasto
    gasto_service.eliminar(gasto.id)
    assert seniales_emitidas == 3
    assert gasto_service.obtener_por_id(gasto.id) is None


def test_gasto_service_validaciones(
    gasto_service: GastoService, categoria_repo: CategoriaRepo
):
    cat = categoria_repo.obtener_por_nombre("Supermercado")
    assert cat is not None

    # Monto cero o negativo
    with pytest.raises(ValueError, match="mayor a (0|cero)"):
        gasto_service.crear(fecha="2026-10-15", monto="0", categoria_id=cat.id)

    with pytest.raises(ValueError, match="mayor a (0|cero)"):
        gasto_service.crear(fecha="2026-10-15", monto="-50.00", categoria_id=cat.id)

    # Monto con letras inválidas
    with pytest.raises(ValueError, match="inválido"):
        gasto_service.crear(fecha="2026-10-15", monto="abc", categoria_id=cat.id)

    # Fecha inválida o vacía
    with pytest.raises(ValueError, match="vacía"):
        gasto_service.crear(fecha="", monto="100", categoria_id=cat.id)

    with pytest.raises(ValueError, match="Formato de fecha"):
        gasto_service.crear(fecha="15/10/2026", monto="100", categoria_id=cat.id)

    # Categoría inexistente
    with pytest.raises(ValueError, match="no existe"):
        gasto_service.crear(fecha="2026-10-15", monto="100", categoria_id=99999)

    # Categoría inactiva
    cat_inactiva = categoria_repo.crear(
        Categoria(id=None, nombre="Vieja", activa=False)
    )
    with pytest.raises(ValueError, match="desactivada"):
        gasto_service.crear(
            fecha="2026-10-15", monto="100", categoria_id=cat_inactiva.id
        )

    # Descripción demasiado larga
    with pytest.raises(ValueError, match="superar"):
        gasto_service.crear(
            fecha="2026-10-15",
            monto="100",
            categoria_id=cat.id,
            descripcion="x" * 300,
        )
