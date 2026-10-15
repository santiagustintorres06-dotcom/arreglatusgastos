from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Gasto:
    fecha: date
    monto: Decimal
    categoria_id: int
    id: int | None = None
    descripcion: str = ""
    medio_pago: str = ""
    cuotas: str = ""
    miembro_id: int | None = None
    creado_en: str | None = None

    @property
    def monto_cent(self) -> int:
        """Convierte el Decimal a centavos enteros para guardar en SQLite."""
        return int(round(self.monto * 100))

    @staticmethod
    def centavos_a_decimal(centavos: int) -> Decimal:
        """Convierte centavos enteros de SQLite a Decimal para la lógica de la app."""
        return (Decimal(centavos) / Decimal(100)).quantize(Decimal("0.01"))
