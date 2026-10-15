import sqlite3
from models.miembro import Miembro


class MiembroRepo:
    """Acceso a datos para la entidad Miembro."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def crear(self, miembro: Miembro) -> Miembro:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO miembro (nombre) VALUES (?);",
            (miembro.nombre.strip(),),
        )
        miembro.id = cursor.lastrowid
        self.conn.commit()
        return miembro

    def obtener_por_id(self, id_miembro: int) -> Miembro | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, nombre FROM miembro WHERE id = ?;", (id_miembro,))
        row = cursor.fetchone()
        if not row:
            return None
        return Miembro(id=row["id"], nombre=row["nombre"])

    def obtener_por_nombre(self, nombre: str) -> Miembro | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, nombre FROM miembro WHERE LOWER(nombre) = LOWER(?);",
            (nombre.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Miembro(id=row["id"], nombre=row["nombre"])

    def listar(self) -> list[Miembro]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, nombre FROM miembro ORDER BY nombre ASC;")
        filas = cursor.fetchall()
        return [Miembro(id=r["id"], nombre=r["nombre"]) for r in filas]

    def eliminar(self, id_miembro: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM miembro WHERE id = ?;", (id_miembro,))
        self.conn.commit()
