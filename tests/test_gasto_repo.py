from datetime import date
from decimal import Decimal
import pytest

from models.categoria import Categoria
from models.gasto import Gasto
from models.miembro import Miembro
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo


def test_categoria_repo_sembrado_y_crud(categoria_repo: CategoriaRepo):
    # Verificar que se sembraron las categorías por defecto
    cats = categoria_repo.listar()
    assert len(cats) >= 5
    supermercado = categoria_repo.obtener_por_nombre("Supermercado")
    assert supermercado is not None
    assert supermercado.activa is True

    # Crear nueva categoría
    nueva = Categoria(id=None, nombre="Mascotas", color="#123456", activa=True)
    creada = categoria_repo.crear(nueva)
    assert creada.id is not None

    # Desactivar
    categoria_repo.desactivar(creada.id)
    activas = categoria_repo.listar(solo_activas=True)
    assert not any(c.id == creada.id for c in activas)
    todas = categoria_repo.listar(solo_activas=False)
    assert any(c.id == creada.id and not c.activa for c in todas)


def test_miembro_repo_crud(miembro_repo: MiembroRepo):
    m = Miembro(id=None, nombre="Santiago")
    creado = miembro_repo.crear(m)
    assert creado.id is not None

    obtenido = miembro_repo.obtener_por_id(creado.id)
    assert obtenido is not None
    assert obtenido.nombre == "Santiago"

    todos = miembro_repo.listar()
    assert len(todos) == 1


def test_gasto_repo_crud_y_precision_monetaria(
    gasto_repo: GastoRepo, categoria_repo: CategoriaRepo, miembro_repo: MiembroRepo
):
    super_cat = categoria_repo.obtener_por_nombre("Supermercado")
    assert super_cat is not None
    miembro = miembro_repo.crear(Miembro(id=None, nombre="Santiago"))

    # Crear gasto con centavos exactos (1234.56)
    gasto = Gasto(
        fecha=date(2026, 10, 15),
        monto=Decimal("1234.56"),
        categoria_id=super_cat.id,
        miembro_id=miembro.id,
        descripcion="Compra semanal",
        medio_pago="Débito",
    )
    creado = gasto_repo.crear(gasto)
    assert creado.id is not None
    assert creado.monto_cent == 123456

    # Leer y comprobar precisión Decimal
    recuperado = gasto_repo.obtener_por_id(creado.id)
    assert recuperado is not None
    assert recuperado.monto == Decimal("1234.56")
    assert recuperado.descripcion == "Compra semanal"
    assert recuperado.fecha == date(2026, 10, 15)

    # Actualizar
    recuperado.monto = Decimal("1500.00")
    recuperado.descripcion = "Compra semanal ampliada"
    gasto_repo.actualizar(recuperado)

    actualizado = gasto_repo.obtener_por_id(creado.id)
    assert actualizado.monto == Decimal("1500.00")
    assert actualizado.monto_cent == 150000
    assert actualizado.descripcion == "Compra semanal ampliada"

    # Eliminar
    gasto_repo.eliminar(creado.id)
    assert gasto_repo.obtener_por_id(creado.id) is None


def test_gasto_repo_consultas_agrupadas(
    gasto_repo: GastoRepo, categoria_repo: CategoriaRepo
):
    cat_super = categoria_repo.obtener_por_nombre("Supermercado")
    cat_servicios = categoria_repo.obtener_por_nombre("Servicios")

    # Dos gastos el 2026-10-10
    gasto_repo.crear(
        Gasto(
            fecha=date(2026, 10, 10),
            monto=Decimal("100.50"),
            categoria_id=cat_super.id,
        )
    )
    gasto_repo.crear(
        Gasto(
            fecha=date(2026, 10, 10),
            monto=Decimal("50.25"),
            categoria_id=cat_servicios.id,
        )
    )

    # Un gasto el 2026-10-15
    gasto_repo.crear(
        Gasto(
            fecha=date(2026, 10, 15),
            monto=Decimal("200.00"),
            categoria_id=cat_super.id,
        )
    )

    # Un gasto en otro mes (2026-11-01) que no debe entrar
    gasto_repo.crear(
        Gasto(
            fecha=date(2026, 11, 1),
            monto=Decimal("999.00"),
            categoria_id=cat_super.id,
        )
    )

    # Totales por día en Octubre
    totales_dia = gasto_repo.totales_por_dia(2026, 10)
    assert len(totales_dia) == 2
    assert totales_dia[date(2026, 10, 10)] == Decimal("150.75")
    assert totales_dia[date(2026, 10, 15)] == Decimal("200.00")

    # Totales por categoría en Octubre
    totales_cat = gasto_repo.totales_por_categoria(2026, 10)
    assert totales_cat[cat_super.id] == Decimal("300.50")
    assert totales_cat[cat_servicios.id] == Decimal("50.25")
