"""Avisos de vencimientos de tarjeta (vencidos sin pagar o próximos a vencer)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from config import formatear_moneda
from repository.tarjeta_repo import TarjetaRepo
from services.calendario_tarjetas import (
    PROXIMO,
    VENCIDO,
    EventoVencimiento,
    eventos_vencimiento_mes_repo,
)
from services.tarjeta_service import _sumar_meses


def filtrar_alertas(eventos: list[EventoVencimiento]) -> list[EventoVencimiento]:
    """Se avisa sólo lo que tiene saldo pendiente y está vencido o por vencer.

    Vencidos primero (más urgentes), después por fecha.
    """
    alertas = [e for e in eventos if e.estado in (VENCIDO, PROXIMO) and e.pendiente_cent > 0]
    return sorted(alertas, key=lambda e: (e.estado != VENCIDO, e.fecha, e.tarjeta_nombre))


def alertas_vencimientos(
    repo: TarjetaRepo, hoy: date | None = None, dias_aviso: int = 5, meses_atras: int = 2
) -> list[EventoVencimiento]:
    """Revisa desde `meses_atras` meses antes hasta el mes siguiente."""
    hoy = hoy or date.today()
    eventos: list[EventoVencimiento] = []
    for delta in range(-meses_atras, 2):
        anio, mes = _sumar_meses(hoy.year, hoy.month, delta)
        eventos += eventos_vencimiento_mes_repo(repo, anio, mes, hoy=hoy, dias_aviso=dias_aviso)
    return filtrar_alertas(eventos)


def texto_alerta(ev: EventoVencimiento, hoy: date) -> str:
    """Frase corta y clara para mostrar en el aviso."""
    monto = formatear_moneda(Decimal(ev.pendiente_cent) / 100)
    dias = (ev.fecha - hoy).days
    if ev.estado == VENCIDO:
        return f"⛔ {ev.tarjeta_nombre}: venció el {ev.fecha:%d/%m} y falta pagar {monto}"
    if dias == 0:
        return f"🔔 {ev.tarjeta_nombre}: vence HOY — {monto}"
    if dias == 1:
        return f"🔔 {ev.tarjeta_nombre}: vence mañana ({ev.fecha:%d/%m}) — {monto}"
    return f"🔔 {ev.tarjeta_nombre}: vence el {ev.fecha:%d/%m} (en {dias} días) — {monto}"
