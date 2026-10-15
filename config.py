from decimal import Decimal, InvalidOperation
import re
from paths import BACKUP_DIR, DATA_DIR, DB_PATH, LOG_DIR

# Configuración de Moneda
SIMBOLO_MONEDA = "$"
MEDIOS_DE_PAGO = [
    "Efectivo",
    "Débito",
    "Crédito",
    "Transferencia",
]

# Categorías iniciales por defecto (nombre, color hex)
CATEGORIAS_POR_DEFECTO = [
    ("Supermercado", "#27ae60"),
    ("Servicios", "#2980b9"),
    ("Casa", "#d35400"),
    ("Transporte", "#8e44ad"),
    ("Salud", "#c0392b"),
    ("Ocio", "#f39c12"),
    ("Educación", "#16a085"),
    ("Otros", "#7f8c8d"),
]

MAX_LARGO_DESCRIPCION = 250


def formatear_moneda(monto: Decimal) -> str:
    """Formatea un objeto Decimal a cadena con formato local: $ 1.234,50"""
    monto_redondeado = monto.quantize(Decimal("0.01"))
    # Formatear estándar con comas para miles y punto para decimales
    texto = f"{monto_redondeado:,.2f}"
    # Invertir para convención local (punto miles, coma decimal)
    partes = texto.split(".")
    entero_con_puntos = partes[0].replace(",", ".")
    decimales = partes[1]
    return f"{SIMBOLO_MONEDA} {entero_con_puntos},{decimales}"


def parsear_monto(texto: str) -> Decimal:
    """Convierte una cadena ingresada por el usuario (acepta coma o punto) a Decimal.
    Lanza ValueError si el formato no es válido o es <= 0.
    """
    if not texto:
        raise ValueError("El monto no puede estar vacío.")

    limpio = texto.strip().replace(SIMBOLO_MONEDA, "").strip()
    # Si tiene puntos como separadores de miles y coma como decimal (ej: 1.234,50)
    if "." in limpio and "," in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio:
        # Si sólo tiene coma, asumimos que es el separador decimal (ej: 1234,50)
        limpio = limpio.replace(",", ".")

    try:
        monto = Decimal(limpio).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Formato de monto inválido: '{texto}'")

    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")

    return monto
