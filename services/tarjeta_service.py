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
    # Resumen (mes de cierre) al que pertenece la cuota
    resumen_anio: int = 0
    resumen_mes: int = 0


# Ajustes manuales de un resumen: {(anio, mes_de_cierre): (fecha_cierre, fecha_vencimiento)}
Ajustes = dict[tuple[int, int], tuple[date, date]]


@dataclass(frozen=True)
class FechasResumen:
    """Fechas de un resumen de tarjeta, identificado por su mes de cierre."""

    anio: int
    mes: int
    cierre: date
    vencimiento: date
    ajustado: bool = False


@dataclass
class ResumenTarjeta:
    """Un resumen (mes de cierre) de una tarjeta con sus cuotas."""

    tarjeta_id: int
    tarjeta_nombre: str
    fechas: FechasResumen
    cuotas: list[InfoCuota]

    @property
    def total_cent(self) -> int:
        return sum(c.monto_cent for c in self.cuotas)

    @property
    def pendiente_cent(self) -> int:
        return sum(c.monto_cent for c in self.cuotas if not c.pagada)

    @property
    def pagado(self) -> bool:
        return bool(self.cuotas) and self.pendiente_cent == 0


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


def fechas_resumen(
    tarjeta: Tarjeta, anio: int, mes: int, ajustes: Ajustes | None = None
) -> FechasResumen:
    """Fechas de cierre y vencimiento del resumen que cierra en (anio, mes).

    - Cierre: el día de cierre de la tarjeta (o el último día si el mes es más corto).
    - Vencimiento: si el día de vencimiento es MAYOR al de cierre, vence ese mismo
      mes (ej. cierra 5, vence 15); si es menor o igual, vence el mes siguiente
      (ej. Visa Macro cierra 22 y vence 5 → el resumen de noviembre vence el 5/12).
    - Si el usuario ajustó a mano las fechas de ese resumen, se usan esas.
    """
    if ajustes and (anio, mes) in ajustes:
        cierre, venc = ajustes[(anio, mes)]
        return FechasResumen(anio, mes, cierre, venc, ajustado=True)
    cierre = date(anio, mes, min(tarjeta.dia_cierre, _ultimo_dia_mes(anio, mes)))
    if tarjeta.dia_vencimiento > tarjeta.dia_cierre:
        anio_v, mes_v = anio, mes
    else:
        anio_v, mes_v = _sumar_meses(anio, mes, 1)
    venc = date(anio_v, mes_v, min(tarjeta.dia_vencimiento, _ultimo_dia_mes(anio_v, mes_v)))
    return FechasResumen(anio, mes, cierre, venc)


def resumen_de_compra(
    fecha_compra: date, tarjeta: Tarjeta, ajustes: Ajustes | None = None
) -> tuple[int, int]:
    """(anio, mes) del primer resumen que incluye la compra.

    Es el primer resumen cuyo cierre es igual o posterior a la fecha de compra
    (una compra hecha justo el día de cierre entra en ese resumen). Se mira
    también el mes anterior por si un cierre ajustado se corrió a este mes.
    """
    for delta in (-1, 0, 1, 2):
        anio, mes = _sumar_meses(fecha_compra.year, fecha_compra.month, delta)
        if fechas_resumen(tarjeta, anio, mes, ajustes).cierre >= fecha_compra:
            return anio, mes
    return _sumar_meses(fecha_compra.year, fecha_compra.month, 1)


def proyectar_cuotas(
    consumo: ConsumoTarjeta,
    tarjeta: Tarjeta,
    ajustes: Ajustes | None = None,
) -> list[InfoCuota]:
    """
    Genera la lista de InfoCuota para todas las cuotas del consumo,
    indicando cuáles ya están pagadas. La cuota N cae en el resumen
    N-1 meses posterior al primero; anio/mes/dia son su fecha de vencimiento.
    """
    fecha_compra = date.fromisoformat(consumo.fecha_compra)
    anio_prim, mes_prim = resumen_de_compra(fecha_compra, tarjeta, ajustes)

    cuotas: list[InfoCuota] = []
    for n in range(1, consumo.cantidad_cuotas + 1):
        anio_r, mes_r = _sumar_meses(anio_prim, mes_prim, n - 1)
        venc = fechas_resumen(tarjeta, anio_r, mes_r, ajustes).vencimiento
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
                resumen_anio=anio_r,
                resumen_mes=mes_r,
            )
        )
    return cuotas


def resumenes_tarjeta(
    tarjeta: Tarjeta,
    consumos: list[ConsumoTarjeta],
    desde: tuple[int, int],
    hasta: tuple[int, int],
    ajustes: Ajustes | None = None,
) -> list[ResumenTarjeta]:
    """Resúmenes de la tarjeta entre dos meses de cierre (inclusive), aunque estén vacíos."""
    por_mes: dict[tuple[int, int], list[InfoCuota]] = {}
    for consumo in consumos:
        if consumo.tarjeta_id != tarjeta.id or consumo.estado == "cancelado":
            continue
        for ic in proyectar_cuotas(consumo, tarjeta, ajustes):
            por_mes.setdefault((ic.resumen_anio, ic.resumen_mes), []).append(ic)

    resultado: list[ResumenTarjeta] = []
    anio, mes = desde
    while (anio, mes) <= hasta:
        cuotas = sorted(por_mes.get((anio, mes), []), key=lambda c: c.descripcion.lower())
        resultado.append(
            ResumenTarjeta(tarjeta.id, tarjeta.nombre, fechas_resumen(tarjeta, anio, mes, ajustes), cuotas)
        )
        anio, mes = _sumar_meses(anio, mes, 1)
    return resultado


def ultimo_resumen_con_cuotas(
    tarjeta: Tarjeta, consumos: list[ConsumoTarjeta], ajustes: Ajustes | None = None
) -> tuple[int, int] | None:
    """Mes de cierre del último resumen que todavía tiene cuotas (para saber hasta dónde listar)."""
    ultimos = [
        (ic.resumen_anio, ic.resumen_mes)
        for c in consumos
        if c.tarjeta_id == tarjeta.id and c.estado != "cancelado"
        for ic in proyectar_cuotas(c, tarjeta, ajustes)[-1:]
    ]
    return max(ultimos) if ultimos else None


def pagar_resumen(repo: TarjetaRepo, resumen: ResumenTarjeta) -> int:
    """Marca como pagadas todas las cuotas del resumen (y las anteriores de cada consumo).

    Devuelve cuántos consumos se actualizaron.
    """
    cambios = 0
    for ic in resumen.cuotas:
        if not ic.pagada:
            repo.marcar_pagadas_hasta(ic.consumo_id, ic.numero_cuota)
            cambios += 1
    return cambios


def deshacer_pago_resumen(repo: TarjetaRepo, resumen: ResumenTarjeta) -> int:
    """Vuelve a dejar pendientes las cuotas de este resumen (y las posteriores)."""
    cambios = 0
    for ic in resumen.cuotas:
        if ic.pagada:
            repo.marcar_pagadas_hasta(ic.consumo_id, ic.numero_cuota - 1)
            cambios += 1
    return cambios


def calcular_saldo_pendiente(consumo: ConsumoTarjeta) -> int:
    """Centavos que restan por pagar en este consumo."""
    return consumo.monto_cuota_cent * consumo.cuotas_restantes


def resumen_mes_por_tarjeta(
    repo: TarjetaRepo,
    anio: int,
    mes: int,
    incluir_pagadas: bool = False,
) -> list[ResumenMes]:
    """
    Para cada tarjeta activa, calcula el total a pagar en el mes indicado.
    Solo incluye tarjetas con al menos una cuota en ese mes.

    Con incluir_pagadas=True suma también las cuotas ya marcadas como pagadas
    (el total completo del resumen, que es lo que se pasa a la Planilla).
    """
    tarjetas = repo.listar(solo_activas=True)
    ajustes = repo.ajustes_por_tarjeta()
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
            proyectadas = proyectar_cuotas(consumo, tarjeta, ajustes.get(tarjeta.id))
            for ic in proyectadas:
                if ic.anio == anio and ic.mes == mes and (incluir_pagadas or not ic.pagada):
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
    ajustes = repo.ajustes_por_tarjeta()
    consumos = repo.listar_consumos(estado="activo")

    alertas: list[InfoCuota] = []
    for consumo in consumos:
        tarjeta = tarjetas.get(consumo.tarjeta_id)
        if tarjeta is None:
            continue
        proyectadas = proyectar_cuotas(consumo, tarjeta, ajustes.get(tarjeta.id))
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
    ajustes = repo.ajustes_por_tarjeta()
    consumos = repo.listar_consumos(estado="activo")

    resultado: list[tuple[int, int, int]] = []
    for anio, mes in meses:
        total = 0
        for consumo in consumos:
            tarjeta = tarjetas.get(consumo.tarjeta_id)
            if tarjeta is None:
                continue
            proyectadas = proyectar_cuotas(consumo, tarjeta, ajustes.get(tarjeta.id))
            for ic in proyectadas:
                if ic.anio == anio and ic.mes == mes and not ic.pagada:
                    total += ic.monto_cent
        resultado.append((anio, mes, total))

    return resultado
