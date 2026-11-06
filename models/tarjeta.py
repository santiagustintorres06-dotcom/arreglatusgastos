from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Tarjeta:
    nombre: str
    dia_cierre: int
    dia_vencimiento: int
    id: int = 0
    limite_cent: int | None = None
    activa: bool = True
    creado_en: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConsumoTarjeta:
    tarjeta_id: int
    fecha_compra: str
    descripcion: str
    monto_total_cent: int
    monto_cuota_cent: int
    cantidad_cuotas: int
    id: int = 0
    cuotas_pagadas: int = 0
    precio_contado_cent: int | None = None
    estado: str = "activo"
    gasto_id_planilla: int | None = None
    creado_en: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def cuotas_restantes(self) -> int:
        return self.cantidad_cuotas - self.cuotas_pagadas

    @property
    def saldo_pendiente_cent(self) -> int:
        return self.monto_cuota_cent * self.cuotas_restantes
