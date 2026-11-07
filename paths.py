import os
import sys
from pathlib import Path


def base_dir() -> Path:
    """Retorna el directorio base de la aplicación.
    Si está congelado con PyInstaller (sys.frozen), usa la carpeta del ejecutable.
    De lo contrario, usa la raíz del código fuente.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


# GASTOS_DATA_DIR permite usar otra carpeta de datos (por ejemplo, el modo demo
# para probar sin tocar los datos reales). Normalmente no se define.
DATA_DIR = Path(os.environ["GASTOS_DATA_DIR"]) if os.environ.get("GASTOS_DATA_DIR") else base_dir() / "data"
DB_PATH = DATA_DIR / "gastos.db"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = base_dir() / "logs"


def asegurar_directorios() -> None:
    """Crea los directorios de datos, backups y logs si no existen."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
