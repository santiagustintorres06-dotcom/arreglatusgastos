from dataclasses import dataclass


@dataclass
class Categoria:
    id: int | None
    nombre: str
    color: str = "#7f8c8d"  # Color hexadecimal para el calendario
    activa: bool = True
