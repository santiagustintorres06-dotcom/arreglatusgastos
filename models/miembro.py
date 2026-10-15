from dataclasses import dataclass


@dataclass
class Miembro:
    id: int | None
    nombre: str
