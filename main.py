import sys

from PySide6.QtWidgets import QApplication

from db.conexion import inicializar_bd, obtener_conexion, realizar_backup
from paths import asegurar_directorios
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from ui.estilo import STYLESHEET
from ui.ventana_principal import VentanaPrincipal


def main() -> None:
    # 1. Asegurar estructura de carpetas portable (data, backups, logs)
    asegurar_directorios()

    # 2. Conexión y primera configuración de la base de datos
    conn = obtener_conexion()
    inicializar_bd(conn)

    # 3. Backup automático diario (conserva últimos 30)
    realizar_backup()

    # 4. Inicializar capas de Repositorio y Servicios
    cat_repo = CategoriaRepo(conn)
    miembro_repo = MiembroRepo(conn)
    gasto_repo = GastoRepo(conn)

    # 5. Inicializar aplicación Qt
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Aspecto limpio y moderno consistente en Windows
    app.setStyleSheet(STYLESHEET)  # Tema visual global

    gasto_service = GastoService(gasto_repo, cat_repo)
    resumen_service = ResumenService(gasto_repo, cat_repo)

    # 6. Crear y mostrar ventana principal
    ventana = VentanaPrincipal(
        gasto_service=gasto_service,
        resumen_service=resumen_service,
        categoria_repo=cat_repo,
        miembro_repo=miembro_repo,
        gasto_repo=gasto_repo,
    )
    ventana.show()

    # 7. Ejecutar loop de eventos
    codigo_salida = app.exec()
    conn.close()
    sys.exit(codigo_salida)


if __name__ == "__main__":
    main()
