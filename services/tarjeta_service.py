from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from models.tarjeta import ConsumoTarjeta, Tarjeta
from repository.tarjeta_repo import TarjetaRepo


@dataclass
class InfoCuota:
    """Datos de una cuota individual proyectada."""

    consumo_id: int
    descripcion: str
    numero_cuota: int
    total_cuotas: int
    monto_cent: int
    anio: int
    mes: int
    dia_vencimiento: int
    tarjeta_id: int
    tarjeta_nombre: str
    pagada: bool


@dataclass
class ResumenMes:
    tarjeta_id: int
    tarjeta_nombre: str
    anio: int
    mes: int
    total_cent: int
    cuotas: list[InfoCuota]
    ya_volcado_planilla: bool = False


def _ultimo_dia_mes(anio: int, mes: int) -> int:
    return calendar.monthrange(anio, mes)[1]


def _sumar_meses(anio: int, mes: int, delta: int) -> tuple[int, int]:
    mes_total = (mes - 1) + delta
    return anio + mes_total // 12, mes_total % 12 + 1


def mes_primera_cuota(
    fecha_compra: date,
    dia_cierre: int,
    anio_ref: int | None = None,
    mes_ref: int | None = None,
) -> tuple[int, int]:
    """
    Retorna (anio, mes) del resumen en el que cae la primera cuota.

    Regla: si la compra es posterior al día de cierre → primer cuota
    en el resumen del mes siguiente; si es el mismo día o antes → mes actual.

    El "mes actual" se toma de fecha_compra salvo que se pase anio_ref/mes_ref
    (útil para tests).
    """
    anio = anio_ref if anio_ref is not None else fecha_compra.year
    mes = mes_ref if mes_ref is not None else fecha_compra.month

    cierre_efectivo = min(dia_cierre, _ultimo_dia_mes(anio, mes))
    fecha_cierre = date(anio, mes, cierre_efectivo)

    if fecha_compra > fecha_cierre:
        return _sumar_meses(anio, mes, 1)
    return anio, mes


def fecha_vencimiento_cuota(
    anio_primera: int,
    mes_primera: int,
    numero_cuota: int,
    dia_vencimiento: int,
) -> date:
    """Retorna la fecha de vencimiento de la cuota número `numero_cuota` (base 1)."""
    anio, mes = _sumar_meses(anio_primera, mes_primera, numero_cuota - 1)
    dia = min(dia_vencimiento, _ultimo_dia_mes(anio, mes))
    return date(anio, mes, dia)


def proyectar_cuotas(
    consumo: ConsumoTarjeta,
    tarjeta: Tarjeta,
) -> list[InfoCuota]:
    """
    Genera la lista de InfoCuota para todas las cuotas del consumo,
    indicando cuáles ya están pagadas.
    """
    fecha_compra = date.fromisoformat(consumo.fecha_compra)
    anio_prim, mes_prim = mes_primera_cuota(fecha_compra, tarjeta.dia_cierre)

    cuotas: list[InfoCuota] = []
    for n in range(1, consumo.cantidad_cuotas + 1):
        venc = fecha_vencimiento_cuota(anio_prim, mes_prim, n, tarjeta.dia_vencimiento)
        cuotas.append(
            InfoCuota(
                consumo_id=consumo.id,
                descripcion=consumo.descripcion,
                numero_cuota=n,
                total_cuotas=consumo.cantidad_cuotas,
                monto_cent=consumo.monto_cuota_cent,
                anio=venc.year,
                mes=venc.month,
                dia_vencimiento=venc.day,
                tarjeta_id=tarjeta.id,
                tarjeta_nombre=tarjeta.nombre,
                pagada=(n <= consumo.cuotas_pagadas),
            )
        )
    return cuotas


def calcular_saldo_pendiente(consumo: ConsumoTarjeta) -> int:
    """Centavos que restan por pagar en este consumo."""
    return consumo.monto_cuota_cent * consumo.cuotas_restantes


def resumen_mes_por_tarjeta(
    repo: TarjetaRepo,
    anio: int,
    mes: int,
) -> list[ResumenMes]:
    """
    Para cada tarjeta activa, calcula el total a pagar en el mes indicado.
    Solo incluye tarjetas con al menos una cuota en ese mes.
    """
    tarjetas = repo.listar(solo_activas=True)
    consumos_activos = repo.listar_consumos(estado="activo") + repo.listar_consumos(
        estado="finalizado"
    )

    resumenes: list[ResumenMes] = []
    for tarjeta in tarjetas:
        cuotas_mes: list[InfoCuota] = []
        consumos_tarjeta = [c for c in consumos_activos if c.tarjeta_id == tarjeta.id]

        for consumo in consumos_tarjeta:
            if consumo.estado == "cancelado":
                continue
            proyectadas = proyectar_cuotas(consumo, tarjeta)
            for ic in proyectadas:
                if ic.anio == anio and ic.mes == mes and not ic.pagada:
                    cuotas_mes.append(ic)

        if cuotas_mes:
            total = sum(ic.monto_cent for ic in cuotas_mes)
            ya_volcado = repo.esta_mes_volcado_planilla(tarjeta.id, anio, mes)
            resumenes.append(
                ResumenMes(
                    tarjeta_id=tarjeta.id,
                    tarjeta_nombre=tarjeta.nombre,
                    anio=anio,
                    mes=mes,
                    total_cent=total,
                    cuotas=cuotas_mes,
                    ya_volcado_planilla=ya_volcado,
                )
            )

    return resumenes


def proximas_a_vencer(
    repo: TarjetaRepo,
    dias_anticipacion: int = 5,
    hoy: date | None = None,
) -> list[InfoCuota]:
    """
    Retorna cuotas que vencen en los próximos `dias_anticipacion` días
    (inclusive hoy), aún no pagadas.
    """
    if hoy is None:
        hoy = date.today()

    tarjetas = {t.id: t for t in repo.listar()}
    consumos = repo.listar_consumos(estado="activo")

    alertas: list[InfoCuota] = []
    for consumo in consumos:
        tarjeta = tarjetas.get(consumo.tarjeta_id)
        if tarjeta is None:
            continue
        proyectadas = proyectar_cuotas(consumo, tarjeta)
        prox_sin_pagar = [ic for ic in proyectadas if not ic.pagada]
        if not prox_sin_pagar:
            continue
        siguiente = prox_sin_pagar[0]
        fecha_venc = date(siguiente.anio, siguiente.mes, siguiente.dia_vencimiento)
        delta = (fecha_venc - hoy).days
        if 0 <= delta <= dias_anticipacion:
            alertas.append(siguiente)

    return alertas


def proyeccion_6_meses(
    repo: TarjetaRepo,
    hoy: date | None = None,
) -> list[tuple[int, int, int]]:
    """
    Retorna lista de (anio, mes, total_cent) para los próximos 6 meses
    incluyendo el mes actual, para graficar carga futura.
    """
    if hoy is None:
        hoy = date.today()

    meses = [_sumar_meses(hoy.year, hoy.month, i) for i in range(6)]
    tarjetas = {t.id: t for t in repo.listar()}
    consumos = repo.listar_consumos(estado="activo")

    resultado: list[tuple[int, int, int]] = []
    for anio, mes in meses:
        total = 0
        for consumo in consumos:
            tarjeta = tarjetas.get(consumo.tarjeta_id)
            if tarjeta is None:
                continue
            proyectadas = proyectar_cuotas(consumo, tarjeta)
            for ic in proyectadas:
                if ic.anio == anio and ic.mes == mes and not ic.pagada:
                    total += ic.monto_cent
        resultado.append((anio, mes, total))

    return resultado
