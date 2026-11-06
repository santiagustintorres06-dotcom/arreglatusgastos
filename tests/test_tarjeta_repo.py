import pytest
from models.tarjeta import ConsumoTarjeta, Tarjeta
from repository.tarjeta_repo import TarjetaRepo


def test_tarjeta_crud_y_desactivacion(tarjeta_repo: TarjetaRepo):
    # 1. Crear tarjeta
    t = Tarjeta(
        nombre="Visa Galicia",
        dia_cierre=20,
        dia_vencimiento=5,
        limite_cent=50000000,  # $ 500.000,00
    )
    t_id = tarjeta_repo.crear(t)
    assert t_id > 0

    # 2. Obtener tarjeta
    recuperada = tarjeta_repo.obtener(t_id)
    assert recuperada is not None
    assert recuperada.nombre == "Visa Galicia"
    assert recuperada.dia_cierre == 20
    assert recuperada.dia_vencimiento == 5
    assert recuperada.limite_cent == 50000000
    assert recuperada.activa is True

    # 3. Actualizar tarjeta
    recuperada.nombre = "Visa Galicia Oro"
    recuperada.limite_cent = 60000000
    tarjeta_repo.actualizar(recuperada)
    actualizada = tarjeta_repo.obtener(t_id)
    assert actualizada.nombre == "Visa Galicia Oro"
    assert actualizada.limite_cent == 60000000

    # 4. Desactivar tarjeta (soft-disable)
    tarjeta_repo.desactivar(t_id)
    desactivada = tarjeta_repo.obtener(t_id)
    assert desactivada.activa is False

    # Listar solo activas no la incluye
    assert len(tarjeta_repo.listar(solo_activas=True)) == 0
    # Listar todas sí la incluye
    assert len(tarjeta_repo.listar(solo_activas=False)) == 1


def test_consumo_tarjeta_pagos_adelantar_y_cancelar(tarjeta_repo: TarjetaRepo):
    t_id = tarjeta_repo.crear(
        Tarjeta(nombre="Mastercard BBVA", dia_cierre=15, dia_vencimiento=2)
    )

    c = ConsumoTarjeta(
        tarjeta_id=t_id,
        fecha_compra="2026-10-10",
        descripcion="Smart TV 55",
        monto_total_cent=12000000,  # $ 120.000
        monto_cuota_cent=2000000,   # $ 20.000
        cantidad_cuotas=6,
        cuotas_pagadas=0,
    )
    c_id = tarjeta_repo.crear_consumo(c)
    assert c_id > 0

    consumo = tarjeta_repo.obtener_consumo(c_id)
    assert consumo.cuotas_restantes == 6
    assert consumo.saldo_pendiente_cent == 12000000
    assert consumo.estado == "activo"

    # Marcar cuota pagada
    tarjeta_repo.marcar_cuota_pagada(c_id)
    consumo = tarjeta_repo.obtener_consumo(c_id)
    assert consumo.cuotas_pagadas == 1
    assert consumo.cuotas_restantes == 5
    assert consumo.saldo_pendiente_cent == 10000000
    assert consumo.estado == "activo"

    # Deshacer última cuota
    tarjeta_repo.deshacer_ultima_cuota(c_id)
    consumo = tarjeta_repo.obtener_consumo(c_id)
    assert consumo.cuotas_pagadas == 0
    assert consumo.cuotas_restantes == 6

    # Adelantar cuotas restantes
    tarjeta_repo.adelantar_cuotas_restantes(c_id)
    consumo = tarjeta_repo.obtener_consumo(c_id)
    assert consumo.cuotas_pagadas == 6
    assert consumo.cuotas_restantes == 0
    assert consumo.saldo_pendiente_cent == 0
    assert consumo.estado == "finalizado"

    # Cancelar consumo (soft-delete)
    c2 = ConsumoTarjeta(
        tarjeta_id=t_id,
        fecha_compra="2026-10-11",
        descripcion="Error de carga",
        monto_total_cent=500000,
        monto_cuota_cent=500000,
        cantidad_cuotas=1,
    )
    c2_id = tarjeta_repo.crear_consumo(c2)
    tarjeta_repo.cancelar_consumo(c2_id)
    consumo_cancelado = tarjeta_repo.obtener_consumo(c2_id)
    assert consumo_cancelado.estado == "cancelado"


def test_resumen_tarjeta_mes_evita_duplicados(tarjeta_repo: TarjetaRepo, gasto_repo):
    t_id = tarjeta_repo.crear(
        Tarjeta(nombre="Tarjeta Naranja", dia_cierre=25, dia_vencimiento=10)
    )

    assert not tarjeta_repo.esta_mes_volcado_planilla(t_id, 2026, 11)

    from datetime import date
    from decimal import Decimal
    from models.gasto import Gasto
    gasto = gasto_repo.crear(
        Gasto(
            fecha=date(2026, 11, 10),
            monto=Decimal("45000.00"),
            categoria_id=1,
            descripcion="Resumen Tarjeta Naranja",
        )
    )

    tarjeta_repo.registrar_mes_volcado_planilla(
        tarjeta_id=t_id,
        anio=2026,
        mes=11,
        gasto_id=gasto.id,
        total_cent=4500000,
    )

    assert tarjeta_repo.esta_mes_volcado_planilla(t_id, 2026, 11)
    assert not tarjeta_repo.esta_mes_volcado_planilla(t_id, 2026, 12)
