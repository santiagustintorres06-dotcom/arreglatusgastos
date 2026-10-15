import pytest
import sqlite3

from db.conexion import obtener_conexion, inicializar_bd
from repository.categoria_repo import CategoriaRepo
from repository.miembro_repo import MiembroRepo
from repository.gasto_repo import GastoRepo
from services.gasto_service import GastoService
from services.resumen_service import ResumenService
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Instancia QApplication para tests que interactúan con widgets o modelos Qt."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def db_conn():
    """Crea una base de datos SQLite en memoria con esquema y categorías por defecto."""
    conn = obtener_conexion(":memory:")
    inicializar_bd(conn)
    yield conn
    conn.close()


@pytest.fixture
def categoria_repo(db_conn: sqlite3.Connection):
    return CategoriaRepo(db_conn)


@pytest.fixture
def miembro_repo(db_conn: sqlite3.Connection):
    return MiembroRepo(db_conn)


@pytest.fixture
def gasto_repo(db_conn: sqlite3.Connection):
    return GastoRepo(db_conn)


@pytest.fixture
def gasto_service(gasto_repo: GastoRepo, categoria_repo: CategoriaRepo):
    return GastoService(gasto_repo, categoria_repo)


@pytest.fixture
def resumen_service(gasto_repo: GastoRepo, categoria_repo: CategoriaRepo):
    return ResumenService(gasto_repo, categoria_repo)
