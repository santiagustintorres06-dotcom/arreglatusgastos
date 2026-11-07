import logging
import os
import sys
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox

from db.conexion import (
    inicializar_bd,
    obtener_conexion,
    realizar_backup,
    respaldo_al_cerrar,
)
from paths import DATA_DIR, DB_PATH, LOG_DIR, asegurar_directorios, base_dir
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from repository.tarjeta_repo import TarjetaRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from services.ubicacion_datos import (
    contar_datos,
    guardar_ignorados,
    leer_ignorados,
    otras_copias_con_datos,
)
from ui.estilo import STYLESHEET
from ui.ventana_principal import VentanaPrincipal

logger = logging.getLogger("gastos_familia")


def _configurar_log() -> None:
    """Asegura que los errores queden anotados en logs/app.log."""
    if not logger.handlers:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        except OSError:
            pass


def _manejador_errores(tipo, valor, tb) -> None:
    """Cualquier error inesperado se anota en el log y se avisa con un mensaje
    entendible, en lugar de que el programa se cierre o falle en silencio."""
    logger.error("Error inesperado:\n%s", "".join(traceback.format_exception(tipo, valor, tb)))
    if QApplication.instance() is not None:
        QMessageBox.warning(
            None,
            "Ocurrió un problema",
            "Algo no salió como se esperaba y la última acción pudo no completarse.\n\n"
            "Los datos guardados antes siguen a salvo.\n"
            f"Detalle técnico (para Santiago): {valor}",
        )


def _carpeta_es_temporal(carpeta: Path) -> bool:
    """True si el programa corre desde una carpeta temporal de Windows.

    Pasa cuando se abre el .exe directamente desde dentro de un .zip:
    Windows lo descomprime en una carpeta temporal que borra después,
    y todo lo cargado se pierde al volver a abrir.
    """
    temporales = {Path(tempfile.gettempdir()).resolve()}
    if os.environ.get("TEMP"):
        temporales.add(Path(os.environ["TEMP"]).resolve())
    try:
        carpeta = carpeta.resolve()
    except OSError:
        return False
    return any(t == carpeta or t in carpeta.parents for t in temporales)


def avisar_otras_copias(ventana) -> None:
    """Si hay otra carpeta del programa con datos, avisar (una vez por carpeta)."""
    try:
        ignorados = leer_ignorados(DATA_DIR)
        copias = [c for c in otras_copias_con_datos(DB_PATH) if str(c.ruta_bd) not in ignorados]
    except Exception:  # noqa: BLE001 - la búsqueda nunca debe impedir usar el programa
        logger.exception("No se pudo buscar otras copias de datos")
        return
    if not copias:
        return
    gastos_aca, consumos_aca = contar_datos(DB_PATH)
    lineas = "\n".join(
        f"• {c.carpeta_programa}\n   ({c.cantidad_gastos} gastos, {c.cantidad_consumos} consumos"
        f" de tarjeta, último cambio {c.modificada:%d/%m/%Y %H:%M})"
        for c in copias[:4]
    )
    caja = QMessageBox(ventana)
    caja.setIcon(QMessageBox.Icon.Warning)
    caja.setWindowTitle("Hay otra copia del programa con datos")
    caja.setText(
        "Encontré otra carpeta del programa que tiene datos cargados:\n\n"
        f"{lineas}\n\n"
        f"La copia que estás usando ahora está en:\n• {base_dir()}\n"
        f"   ({gastos_aca} gastos, {consumos_aca} consumos de tarjeta)\n\n"
        "Cada carpeta guarda sus propios datos. Si cargaste cosas en la otra,\n"
        "no van a aparecer acá. Conviene usar SIEMPRE la misma carpeta\n"
        "(y borrar o renombrar la que no se usa, después de revisarla)."
    )
    no_avisar = QCheckBox("No volver a avisar por estas carpetas")
    caja.setCheckBox(no_avisar)
    caja.exec()
    if no_avisar.isChecked():
        guardar_ignorados(DATA_DIR, ignorados | {str(c.ruta_bd) for c in copias})


def main() -> None:
    # 1. Asegurar estructura de carpetas portable (data, backups, logs)
    asegurar_directorios()
    _configurar_log()
    sys.excepthook = _manejador_errores
    logger.info("Inicio del programa. Base de datos: %s", DB_PATH)

    # 2. Inicializar aplicación Qt (antes que nada, para poder mostrar mensajes)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Aspecto limpio y moderno consistente en Windows
    app.setStyleSheet(STYLESHEET)  # Tema visual global

    if getattr(sys, "frozen", False) and _carpeta_es_temporal(base_dir()):
        QMessageBox.warning(
            None,
            "Atención: los datos no se van a guardar",
            "El programa se está ejecutando desde una carpeta temporal\n"
            "(probablemente se abrió directamente desde un archivo .zip).\n\n"
            "Lo que cargues ahora se va a PERDER al cerrar.\n\n"
            "Solución: cerrá el programa, copiá la carpeta 'GastosFamilia' completa\n"
            "al Escritorio o a Documentos y abrí el programa desde ahí.",
        )

    # 3. Respaldo diario ANTES de tocar/migrar la base (conserva últimos 30)
    try:
        realizar_backup()
    except Exception:  # noqa: BLE001 - un backup fallido no debe impedir usar el programa
        logger.exception("No se pudo realizar el backup diario")

    # 4. Conexión y migración segura (CREATE TABLE IF NOT EXISTS)
    try:
        conn = obtener_conexion()
        inicializar_bd(conn)
    except Exception as e:  # noqa: BLE001 - se informa al usuario y se anota
        logger.exception("No se pudo abrir la base de datos")
        QMessageBox.critical(
            None,
            "No se pudo abrir la base de datos",
            "No se pudo abrir el archivo de datos:\n"
            f"{DB_PATH}\n\n"
            "Verificá que la carpeta del programa no esté en un pendrive desconectado\n"
            "o en una ubicación de solo lectura.\n\n"
            f"Detalle técnico: {e}",
        )
        sys.exit(1)

    # 5. Inicializar capas de Repositorio y Servicios
    cat_repo = CategoriaRepo(conn)
    miembro_repo = MiembroRepo(conn)
    gasto_repo = GastoRepo(conn)
    tarjeta_repo = TarjetaRepo(conn)

    gasto_service = GastoService(gasto_repo, cat_repo)
    resumen_service = ResumenService(gasto_repo, cat_repo)

    # 6. Crear y mostrar ventana principal
    ventana = VentanaPrincipal(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=cat_repo,
        miembro_repo=miembro_repo,
        gasto_repo=gasto_repo,
        tarjeta_repo=tarjeta_repo,
    )
    ventana.show()
    # Revisar, ya con la ventana abierta, si hay otra carpeta del programa con datos
    QTimer.singleShot(400, lambda: avisar_otras_copias(ventana))

    # 7. Ejecutar loop de eventos
    codigo_salida = app.exec()
    conn.close()

    # 8. Copia de seguridad de cómo quedó todo al cerrar
    try:
        respaldo_al_cerrar()
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo realizar el respaldo al cerrar")
    logger.info("Cierre normal del programa.")
    sys.exit(codigo_salida)


if __name__ == "__main__":
    main()
