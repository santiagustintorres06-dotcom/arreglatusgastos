"""Vencimientos de tarjeta para el Calendario.

Calcula los eventos a partir de las tablas `tarjeta` y `consumo_tarjeta`
(única fuente de verdad: no se guarda nada extra en la base).
Las funciones de cálculo son puras (reciben listas y la fecha de hoy).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from config import DIAS_AVISO_VENCIMIENTO
from models.tarjeta import ConsumoTarjeta, Tarjeta
from repository.tarjeta_repo import TarjetaRepo
from services.tarjeta_service import InfoCuota, proyectar_cuotas

# Estados posibles de un vencimiento
PENDIENTE = "pendiente"
PROXIMO = "proximo"  # vence dentro de pocos días
VENCIDO = "vencido"  # ya pasó la fecha y quedan cuotas sin pagar
PAGADO = "pagado"  # todas las cuotas de ese vencimiento están pagadas

ETIQUETA_ESTADO = {
    PENDIENTE: "Pendiente",
    PROXIMO: "Próximo a vencer",
    VENCIDO: "Vencido",
    PAGADO: "Pagado",
}


@dataclass
class EventoVencimiento:
    """Vencimiento del resumen de una tarjeta en una fecha."""

    tarjeta_id: int
    tarjeta_nombre: str
    fecha: date
    cuotas: list[InfoCuota] = field(default_factory=list)
    estado: str = PENDIENTE
    volcado_planilla: bool = False

    @property
    def total_cent(self) -> int:
        """Total del resumen (cuotas pagadas y sin pagar)."""
        return sum(c.monto_cent for c in self.cuotas)

    @property
    def pendiente_cent(self) -> int:
        """Lo que todavía falta pagar de este vencimiento."""
        return sum(c.monto_cent for c in self.cuotas if not c.pagada)


def estado_vencimiento(
    fecha: date, hay_pendientes: bool, hoy: date, dias_aviso: int = DIAS_AVISO_VENCIMIENTO
) -> str:
    """Estado según la fecha de vencimiento y si quedan cuotas sin pagar."""
    if not hay_pendientes:
        return PAGADO
    dias = (fecha - hoy).days
    if dias < 0:
        return VENCIDO
    if dias <= dias_aviso:
        return PROXIMO
    return PENDIENTE


def eventos_vencimiento_mes(
    tarjetas: list[Tarjeta],
    consumos: list[ConsumoTarjeta],
    anio: int,
    mes: int,
    hoy: date,
    meses_volcados: set[tuple[int, int, int]] | None = None,
    dias_aviso: int = DIAS_AVISO_VENCIMIENTO,
) -> list[EventoVencimiento]:
    """Eventos de vencimiento del mes indicado, uno por tarjeta y fecha.

    - Se ignoran consumos cancelados (borrado lógico) y tarjetas inactivas,
      igual que en la pestaña Tarjetas, para que los totales coincidan.
    - Las cuotas futuras se proyectan, así que navegar a meses siguientes
      muestra los vencimientos hasta que terminen las cuotas.
    - `meses_volcados` contiene (tarjeta_id, anio, mes) ya pasados a la Planilla.
    """
    meses_volcados = meses_volcados or set()
    tarjetas_activas = {t.id: t for t in tarjetas if t.activa}

    agrupados: dict[tuple[int, date], EventoVencimiento] = {}
    for consumo in consumos:
        if consumo.estado == "cancelado":
            continue
        tarjeta = tarjetas_activas.get(consumo.tarjeta_id)
        if tarjeta is None:
            continue
        for cuota in proyectar_cuotas(consumo, tarjeta):
            if cuota.anio != anio or cuota.mes != mes:
                continue
            fecha = date(cuota.anio, cuota.mes, cuota.dia_vencimiento)
            clave = (tarjeta.id, fecha)
            if clave not in agrupados:
                agrupados[clave] = EventoVencimiento(
                    tarjeta_id=tarjeta.id,
                    tarjeta_nombre=tarjeta.nombre,
                    fecha=fecha,
                    volcado_planilla=(tarjeta.id, anio, mes) in meses_volcados,
                )
            agrupados[clave].cuotas.append(cuota)

    eventos = sorted(agrupados.values(), key=lambda e: (e.fecha, e.tarjeta_nombre.lower()))
    for ev in eventos:
        ev.cuotas.sort(key=lambda c: c.descripcion.lower())
        ev.estado = estado_vencimiento(ev.fecha, ev.pendiente_cent > 0, hoy, dias_aviso)
    return eventos


def total_tarjetas_sin_volcar_cent(eventos: list[EventoVencimiento]) -> int:
    """Total de tarjetas del mes que todavía NO se pasó a la Planilla.

    Lo que ya se volcó figura como gasto en la Planilla, así que no se suma
    de nuevo (evita contar dos veces el mismo resumen).
    """
    return sum(e.total_cent for e in eventos if not e.volcado_planilla)


def eventos_vencimiento_mes_repo(
    repo: TarjetaRepo, anio: int, mes: int, hoy: date | None = None
) -> list[EventoVencimiento]:
    """Igual que `eventos_vencimiento_mes`, leyendo los datos desde la base."""
    hoy = hoy or date.today()
    tarjetas = repo.listar()
    volcados = {
        (t.id, anio, mes) for t in tarjetas if repo.esta_mes_volcado_planilla(t.id, anio, mes)
    }
    return eventos_vencimiento_mes(tarjetas, repo.listar_consumos(), anio, mes, hoy, volcados)
