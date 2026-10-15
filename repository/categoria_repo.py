import sqlite3
from models.categoria import Categoria


class CategoriaRepo:
    """Acceso a datos para la entidad Categoria."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def crear(self, categoria: Categoria) -> Categoria:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO categoria (nombre, color, activa) VALUES (?, ?, ?);",
            (categoria.nombre, categoria.color, 1 if categoria.activa else 0),
        )
        categoria.id = cursor.lastrowid
        self.conn.commit()
        return categoria

    def actualizar(self, categoria: Categoria) -> None:
        if categoria.id is None:
            raise ValueError("No se puede actualizar una categoría sin ID.")
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE categoria SET nombre = ?, color = ?, activa = ? WHERE id = ?;",
            (
                categoria.nombre,
                categoria.color,
                1 if categoria.activa else 0,
                categoria.id,
            ),
        )
        self.conn.commit()

    def desactivar(self, id_categoria: int) -> None:
        """Desactiva una categoría (soft-delete) para no romper registros históricos."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE categoria SET activa = 0 WHERE id = ?;",
            (id_categoria,),
        )
        self.conn.commit()

    def reactivar(self, id_categoria: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE categoria SET activa = 1 WHERE id = ?;",
            (id_categoria,),
        )
        self.conn.commit()

    def obtener_por_id(self, id_categoria: int) -> Categoria | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, nombre, color, activa FROM categoria WHERE id = ?;",
            (id_categoria,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Categoria(
            id=row["id"],
            nombre=row["nombre"],
            color=row["color"],
            activa=bool(row["activa"]),
        )

    def obtener_por_nombre(self, nombre: str) -> Categoria | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, nombre, color, activa FROM categoria WHERE LOWER(nombre) = LOWER(?);",
            (nombre.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Categoria(
            id=row["id"],
            nombre=row["nombre"],
            color=row["color"],
            activa=bool(row["activa"]),
        )

    def listar(self, solo_activas: bool = True) -> list[Categoria]:
        cursor = self.conn.cursor()
        if solo_activas:
            cursor.execute(
                "SELECT id, nombre, color, activa FROM categoria WHERE activa = 1 ORDER BY nombre ASC;"
            )
        else:
            cursor.execute(
                "SELECT id, nombre, color, activa FROM categoria ORDER BY nombre ASC;"
            )

        filas = cursor.fetchall()
        return [
            Categoria(
                id=r["id"],
                nombre=r["nombre"],
                color=r["color"],
                activa=bool(r["activa"]),
            )
            for r in filas
        ]
