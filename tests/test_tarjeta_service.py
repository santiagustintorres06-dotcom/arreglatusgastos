from datetime import date

import pytest

from models.tarjeta import ConsumoTarjeta, Tarjeta
from services.tarjeta_service import (
    calcular_saldo_pendiente,
    deshacer_pago_resumen,
    fechas_resumen,
    pagar_resumen,
    resumen_de_compra,
    resumenes_tarjeta,
    ultimo_resumen_con_cuotas,
    fecha_vencimiento_cuota,
    mes_primera_cuota,
    proyectar_cuotas,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tarjeta(dia_cierre: int, dia_vencimiento: int) -> Tarjeta:
    return Tarjeta(
        id=1,
        nombre="TEST",
        dia_cierre=dia_cierre,
        dia_vencimiento=dia_vencimiento,
    )


def _consumo(
    tarjeta_id: int = 1,
    fecha: str = "2024-01-15",
    total_cent: int = 10000,
    cuota_cent: int = 1000,
    cantidad: int = 10,
    pagadas: int = 0,
) -> ConsumoTarjeta:
    return ConsumoTarjeta(
        id=1,
        tarjeta_id=tarjeta_id,
        fecha_compra=fecha,
        descripcion="test",
        monto_total_cent=total_cent,
        monto_cuota_cent=cuota_cent,
        cantidad_cuotas=cantidad,
        cuotas_pagadas=pagadas,
    )


# ---------------------------------------------------------------------------
# mes_primera_cuota
# ---------------------------------------------------------------------------

class TestMesPrimeraCuota:
    def test_compra_antes_cierre_mismo_mes(self):
        compra = date(2024, 1, 10)
        anio, mes = mes_primera_cuota(compra, dia_cierre=15)
        assert (anio, mes) == (2024, 1)

    def test_compra_en_dia_cierre_mismo_mes(self):
        compra = date(2024, 1, 15)
        anio, mes = mes_primera_cuota(compra, dia_cierre=15)
        assert (anio, mes) == (2024, 1)

    def test_compra_despues_cierre_mes_siguiente(self):
        compra = date(2024, 1, 20)
        anio, mes = mes_primera_cuota(compra, dia_cierre=15)
        assert (anio, mes) == (2024, 2)

    def test_compra_fin_de_diciembre_pasa_a_enero(self):
        compra = date(2024, 12, 20)
        anio, mes = mes_primera_cuota(compra, dia_cierre=15)
        assert (anio, mes) == (2025, 1)

    def test_cierre_dia_31_en_febrero_usa_ultimo_dia(self):
        # Febrero 2024 tiene 29 días; el cierre efectivo es el 29
        compra = date(2024, 2, 28)
        anio, mes = mes_primera_cuota(compra, dia_cierre=31)
        assert (anio, mes) == (2024, 2)

    def test_cierre_dia_31_en_febrero_compra_despues(self):
        compra = date(2024, 3, 1)
        anio, mes = mes_primera_cuota(compra, dia_cierre=31, anio_ref=2024, mes_ref=3)
        # 31 de marzo existe; compra el 1 está antes del cierre → mismo mes
        assert (anio, mes) == (2024, 3)

    def test_compra_en_noviembre_cierre_30_despues(self):
        # Cierre día 30 en noviembre, compra el 30 → mismo mes
        compra = date(2024, 11, 30)
        anio, mes = mes_primera_cuota(compra, dia_cierre=30)
        assert (anio, mes) == (2024, 11)


# ---------------------------------------------------------------------------
# fecha_vencimiento_cuota
# ---------------------------------------------------------------------------

class TestFechaVencimientoCuota:
    def test_primera_cuota_mismo_mes(self):
        fecha = fecha_vencimiento_cuota(2024, 1, 1, dia_vencimiento=10)
        assert fecha == date(2024, 1, 10)

    def test_segunda_cuota_mes_siguiente(self):
        fecha = fecha_vencimiento_cuota(2024, 1, 2, dia_vencimiento=10)
        assert fecha == date(2024, 2, 10)

    def test_vencimiento_dia_31_en_febrero_no_existe(self):
        # Febrero 2024 tiene 29 días; ajusta al último
        fecha = fecha_vencimiento_cuota(2024, 1, 2, dia_vencimiento=31)
        assert fecha == date(2024, 2, 29)

    def test_cambio_de_anio(self):
        fecha = fecha_vencimiento_cuota(2024, 12, 2, dia_vencimiento=10)
        assert fecha == date(2025, 1, 10)

    def test_vencimiento_dia_31_en_noviembre(self):
        fecha = fecha_vencimiento_cuota(2024, 11, 1, dia_vencimiento=31)
        assert fecha == date(2024, 11, 30)


# ---------------------------------------------------------------------------
# proyectar_cuotas
# ---------------------------------------------------------------------------

class TestProyectarCuotas:
    # Tarjeta que cierra el 15 y vence el 5 del mes siguiente
    def test_cantidad_correcta(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-10", cantidad=6)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert len(cuotas) == 6

    def test_antes_del_cierre_vence_el_mes_siguiente(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-10", cantidad=3)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert (cuotas[0].resumen_anio, cuotas[0].resumen_mes) == (2024, 1)
        assert date(cuotas[0].anio, cuotas[0].mes, cuotas[0].dia_vencimiento) == date(2024, 2, 5)

    def test_despues_del_cierre_pasa_al_resumen_siguiente(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-20", cantidad=3)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert (cuotas[0].resumen_anio, cuotas[0].resumen_mes) == (2024, 2)
        assert (cuotas[0].anio, cuotas[0].mes) == (2024, 3)

    def test_vencimiento_mayor_al_cierre_vence_el_mismo_mes(self):
        tarjeta = _tarjeta(dia_cierre=5, dia_vencimiento=15)
        cuotas = proyectar_cuotas(_consumo(fecha="2024-01-03", cantidad=1), tarjeta)
        assert date(cuotas[0].anio, cuotas[0].mes, cuotas[0].dia_vencimiento) == date(2024, 1, 15)

    def test_pagadas_marcadas_correctamente(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-10", cantidad=6, pagadas=3)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert all(ic.pagada for ic in cuotas[:3])
        assert all(not ic.pagada for ic in cuotas[3:])

    def test_una_sola_cuota(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-10", cantidad=1, cuota_cent=5000, total_cent=5000)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert len(cuotas) == 1
        assert cuotas[0].numero_cuota == 1
        assert cuotas[0].total_cuotas == 1

    def test_cambio_de_anio(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-11-10", cantidad=3)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert (cuotas[0].anio, cuotas[0].mes) == (2024, 12)
        assert (cuotas[1].anio, cuotas[1].mes) == (2025, 1)
        assert (cuotas[2].anio, cuotas[2].mes) == (2025, 2)


# ---------------------------------------------------------------------------
# Resúmenes por tarjeta (cada tarjeta con su propio cierre)
# ---------------------------------------------------------------------------

VISA_MACRO = Tarjeta(id=1, nombre="Visa Macro", dia_cierre=22, dia_vencimiento=5)
NARANJA = Tarjeta(id=2, nombre="Naranja Visa", dia_cierre=28, dia_vencimiento=10)


class TestResumenes:
    def test_misma_compra_distinto_resumen_segun_tarjeta(self):
        compra = date(2026, 11, 23)
        # Visa Macro ya cerró el 22/11 → resumen de diciembre, vence 5/1
        assert resumen_de_compra(compra, VISA_MACRO) == (2026, 12)
        assert fechas_resumen(VISA_MACRO, 2026, 12).vencimiento == date(2027, 1, 5)
        # Naranja cierra el 28/11 → resumen de noviembre, vence 10/12
        assert resumen_de_compra(compra, NARANJA) == (2026, 11)
        assert fechas_resumen(NARANJA, 2026, 11).vencimiento == date(2026, 12, 10)

    def test_cierre_31_en_meses_cortos(self):
        t = Tarjeta(id=3, nombre="X", dia_cierre=31, dia_vencimiento=10)
        assert fechas_resumen(t, 2027, 2).cierre == date(2027, 2, 28)
        assert fechas_resumen(t, 2027, 2).vencimiento == date(2027, 3, 10)
        assert resumen_de_compra(date(2027, 2, 28), t) == (2027, 2)
        assert resumen_de_compra(date(2027, 3, 1), t) == (2027, 3)

    def test_ajuste_manual(self):
        ajustes = {(2026, 11): (date(2026, 11, 24), date(2026, 12, 7))}
        f = fechas_resumen(VISA_MACRO, 2026, 11, ajustes)
        assert f.ajustado and f.cierre == date(2026, 11, 24) and f.vencimiento == date(2026, 12, 7)
        # Con el cierre corrido al 24, una compra del 23/11 entra en noviembre
        assert resumen_de_compra(date(2026, 11, 23), VISA_MACRO, ajustes) == (2026, 11)
        assert not fechas_resumen(VISA_MACRO, 2026, 12, ajustes).ajustado

    def test_cierre_ajustado_que_cae_en_el_mes_siguiente(self):
        # El resumen de octubre se corrió al 2/11: una compra del 1/11 entra en octubre
        ajustes = {(2026, 10): (date(2026, 11, 2), date(2026, 11, 12))}
        assert resumen_de_compra(date(2026, 11, 1), VISA_MACRO, ajustes) == (2026, 10)

    def test_resumenes_tarjeta_lista_meses_y_totales(self):
        consumos = [
            ConsumoTarjeta(id=1, tarjeta_id=1, fecha_compra="2026-11-10", descripcion="Tele",
                           monto_total_cent=30000, monto_cuota_cent=10000, cantidad_cuotas=3, cuotas_pagadas=1),
            ConsumoTarjeta(id=2, tarjeta_id=2, fecha_compra="2026-11-10", descripcion="Otra tarjeta",
                           monto_total_cent=500, monto_cuota_cent=500, cantidad_cuotas=1),
            ConsumoTarjeta(id=3, tarjeta_id=1, fecha_compra="2026-11-10", descripcion="Cancelado",
                           monto_total_cent=500, monto_cuota_cent=500, cantidad_cuotas=1, estado="cancelado"),
        ]
        res = resumenes_tarjeta(VISA_MACRO, consumos, (2026, 10), (2027, 2))
        assert [(r.fechas.anio, r.fechas.mes) for r in res] == [
            (2026, 10), (2026, 11), (2026, 12), (2027, 1), (2027, 2)
        ]
        assert [r.total_cent for r in res] == [0, 10000, 10000, 10000, 0]
        assert res[1].pagado and not res[2].pagado
        assert ultimo_resumen_con_cuotas(VISA_MACRO, consumos) == (2027, 1)

    def test_pagar_y_deshacer_resumen(self, tarjeta_repo):
        tid = tarjeta_repo.crear(Tarjeta(nombre="Visa Macro", dia_cierre=22, dia_vencimiento=5))
        tarjeta = tarjeta_repo.obtener(tid)
        cid = tarjeta_repo.crear_consumo(
            ConsumoTarjeta(tarjeta_id=tid, fecha_compra="2026-11-10", descripcion="Tele",
                           monto_total_cent=30000, monto_cuota_cent=10000, cantidad_cuotas=3)
        )

        def resumen(mes_offset):
            consumos = tarjeta_repo.listar_consumos()
            return resumenes_tarjeta(tarjeta, consumos, (2026, 11), (2027, 1))[mes_offset]

        # Pagar el resumen de diciembre (cuota 2) deja pagadas la 1 y la 2
        assert pagar_resumen(tarjeta_repo, resumen(1)) == 1
        assert tarjeta_repo.obtener_consumo(cid).cuotas_pagadas == 2
        # Pagar el último finaliza el consumo
        pagar_resumen(tarjeta_repo, resumen(2))
        c = tarjeta_repo.obtener_consumo(cid)
        assert c.cuotas_pagadas == 3 and c.estado == "finalizado"
        # Deshacer el de diciembre vuelve a dejar 1 pagada y el consumo activo
        deshacer_pago_resumen(tarjeta_repo, resumen(1))
        c = tarjeta_repo.obtener_consumo(cid)
        assert c.cuotas_pagadas == 1 and c.estado == "activo"


# ---------------------------------------------------------------------------
# calcular_saldo_pendiente
# ---------------------------------------------------------------------------

class TestCalcularSaldoPendiente:
    def test_sin_pagos(self):
        consumo = _consumo(cuota_cent=1000, cantidad=6, pagadas=0)
        assert calcular_saldo_pendiente(consumo) == 6000

    def test_parcialmente_pagado(self):
        consumo = _consumo(cuota_cent=1000, cantidad=6, pagadas=4)
        assert calcular_saldo_pendiente(consumo) == 2000

    def test_completamente_pagado(self):
        consumo = _consumo(cuota_cent=1000, cantidad=6, pagadas=6)
        assert calcular_saldo_pendiente(consumo) == 0

    def test_una_cuota_sin_pagar(self):
        consumo = _consumo(cuota_cent=5000, cantidad=1, pagadas=0)
        assert calcular_saldo_pendiente(consumo) == 5000
