from datetime import date

import pytest

from models.tarjeta import ConsumoTarjeta, Tarjeta
from services.tarjeta_service import (
    calcular_saldo_pendiente,
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
    def test_cantidad_correcta(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-10", cantidad=6)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert len(cuotas) == 6

    def test_primera_cuota_mismo_mes(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-10", cantidad=3)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert cuotas[0].anio == 2024
        assert cuotas[0].mes == 1

    def test_primera_cuota_mes_siguiente_por_cierre(self):
        tarjeta = _tarjeta(dia_cierre=15, dia_vencimiento=5)
        consumo = _consumo(fecha="2024-01-20", cantidad=3)
        cuotas = proyectar_cuotas(consumo, tarjeta)
        assert cuotas[0].anio == 2024
        assert cuotas[0].mes == 2

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
        assert cuotas[0].mes == 11
        assert cuotas[1].mes == 12
        assert cuotas[2].anio == 2025 and cuotas[2].mes == 1


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
