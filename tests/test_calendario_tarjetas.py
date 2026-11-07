from datetime import date

from models.tarjeta import ConsumoTarjeta, Tarjeta
from services.calendario_tarjetas import (
    PAGADO,
    PENDIENTE,
    PROXIMO,
    VENCIDO,
    estado_vencimiento,
    eventos_vencimiento_mes,
    eventos_vencimiento_mes_repo,
    total_tarjetas_sin_volcar_cent,
)

VISA = Tarjeta(id=1, nombre="Visa", dia_cierre=25, dia_vencimiento=10)
MASTER = Tarjeta(id=2, nombre="Master", dia_cierre=31, dia_vencimiento=31)


def _consumo(id_, tarjeta_id, fecha, cuotas, cuota_cent=10000, pagadas=0, estado="activo", desc=None):
    return ConsumoTarjeta(
        id=id_,
        tarjeta_id=tarjeta_id,
        fecha_compra=fecha,
        descripcion=desc or f"Compra {id_}",
        monto_total_cent=cuota_cent * cuotas,
        monto_cuota_cent=cuota_cent,
        cantidad_cuotas=cuotas,
        cuotas_pagadas=pagadas,
        estado=estado,
    )


HOY = date(2026, 11, 7)


# ---------------- estado_vencimiento ----------------


def test_estados():
    assert estado_vencimiento(date(2026, 11, 20), True, HOY) == PENDIENTE
    assert estado_vencimiento(date(2026, 11, 10), True, HOY) == PROXIMO
    assert estado_vencimiento(date(2026, 11, 7), True, HOY) == PROXIMO  # vence hoy
    assert estado_vencimiento(date(2026, 11, 6), True, HOY) == VENCIDO
    assert estado_vencimiento(date(2026, 11, 6), False, HOY) == PAGADO
    assert estado_vencimiento(date(2026, 12, 1), False, HOY) == PAGADO


def test_dias_aviso_configurable():
    assert estado_vencimiento(date(2026, 11, 10), True, HOY, dias_aviso=2) == PENDIENTE


# ---------------- eventos_vencimiento_mes ----------------


def test_agrupa_por_tarjeta_y_fecha_con_numero_de_cuota():
    consumos = [
        _consumo(1, 1, "2026-09-01", 6),  # 1ra cuota en sep → nov es la 3/6
        _consumo(2, 1, "2026-11-01", 1, cuota_cent=5000),  # 1 pago → nov
        _consumo(3, 2, "2026-11-02", 3, cuota_cent=20000),
    ]
    ev = eventos_vencimiento_mes([VISA, MASTER], consumos, 2026, 11, HOY)

    assert [(e.tarjeta_nombre, e.fecha) for e in ev] == [
        ("Visa", date(2026, 11, 10)),
        ("Master", date(2026, 11, 30)),  # día 31 en noviembre → 30
    ]
    visa = ev[0]
    assert visa.total_cent == 15000
    nums = {c.consumo_id: (c.numero_cuota, c.total_cuotas) for c in visa.cuotas}
    assert nums[1] == (3, 6)
    assert nums[2] == (1, 1)
    assert visa.estado == PROXIMO


def test_proyecta_meses_futuros_hasta_que_terminan_las_cuotas():
    consumos = [_consumo(1, 1, "2026-11-01", 3)]  # nov, dic, ene
    assert len(eventos_vencimiento_mes([VISA], consumos, 2026, 12, HOY)) == 1
    enero = eventos_vencimiento_mes([VISA], consumos, 2027, 1, HOY)  # cambio de año
    assert enero[0].fecha == date(2027, 1, 10)
    assert enero[0].cuotas[0].numero_cuota == 3
    assert eventos_vencimiento_mes([VISA], consumos, 2027, 2, HOY) == []


def test_febrero_y_dia_31():
    consumos = [_consumo(1, 2, "2027-01-15", 2)]
    feb = eventos_vencimiento_mes([MASTER], consumos, 2027, 2, HOY)
    assert feb[0].fecha == date(2027, 2, 28)
    feb_bis = eventos_vencimiento_mes([MASTER], [_consumo(1, 2, "2028-01-15", 2)], 2028, 2, HOY)
    assert feb_bis[0].fecha == date(2028, 2, 29)


def test_compra_justo_en_el_dia_de_cierre_va_al_mismo_mes():
    en_cierre = [_consumo(1, 1, "2026-11-25", 1)]
    despues = [_consumo(2, 1, "2026-11-26", 1)]
    assert eventos_vencimiento_mes([VISA], en_cierre, 2026, 11, HOY)
    assert not eventos_vencimiento_mes([VISA], despues, 2026, 11, HOY)
    assert eventos_vencimiento_mes([VISA], despues, 2026, 12, HOY)


def test_pagado_vencido_y_cancelados():
    consumos = [
        _consumo(1, 1, "2026-10-01", 2, pagadas=1),  # cuota 1 (oct) pagada
        _consumo(2, 1, "2026-10-02", 1),  # oct sin pagar → vencido
        _consumo(3, 1, "2026-10-03", 1, estado="cancelado"),
    ]
    oct_ = eventos_vencimiento_mes([VISA], consumos, 2026, 10, HOY)
    assert len(oct_) == 1
    assert oct_[0].estado == VENCIDO
    assert oct_[0].total_cent == 20000  # el cancelado no cuenta
    assert oct_[0].pendiente_cent == 10000

    solo_pagado = eventos_vencimiento_mes([VISA], consumos[:1], 2026, 10, HOY)
    assert solo_pagado[0].estado == PAGADO


def test_tarjeta_inactiva_no_se_muestra():
    inactiva = Tarjeta(id=3, nombre="Vieja", dia_cierre=1, dia_vencimiento=5, activa=False)
    assert eventos_vencimiento_mes([inactiva], [_consumo(1, 3, "2026-11-01", 1)], 2026, 11, HOY) == []


def test_no_cuenta_dos_veces_lo_volcado_a_planilla():
    consumos = [_consumo(1, 1, "2026-11-01", 1), _consumo(2, 2, "2026-11-01", 1, cuota_cent=3000)]
    ev = eventos_vencimiento_mes([VISA, MASTER], consumos, 2026, 11, HOY, meses_volcados={(1, 2026, 11)})
    assert [e.volcado_planilla for e in ev] == [True, False]
    assert total_tarjetas_sin_volcar_cent(ev) == 3000


def test_lee_desde_la_base(tarjeta_repo, gasto_service, categoria_repo):
    tid = tarjeta_repo.crear(Tarjeta(nombre="Naranja", dia_cierre=20, dia_vencimiento=5))
    tarjeta_repo.crear_consumo(_consumo(0, tid, "2026-11-01", 2))
    cat = categoria_repo.obtener_por_nombre("Servicios")
    gasto = gasto_service.crear("2026-12-05", "100", cat.id, "Resumen")
    tarjeta_repo.registrar_mes_volcado_planilla(tid, 2026, 12, gasto.id, 10000)

    nov = eventos_vencimiento_mes_repo(tarjeta_repo, 2026, 11, hoy=HOY)
    dic = eventos_vencimiento_mes_repo(tarjeta_repo, 2026, 12, hoy=HOY)
    assert nov[0].fecha == date(2026, 11, 5)
    assert not nov[0].volcado_planilla
    assert dic[0].volcado_planilla
