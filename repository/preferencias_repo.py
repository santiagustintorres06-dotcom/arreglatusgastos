"""Preferencias del usuario guardadas en la base (tabla `preferencia`)."""

import sqlite3

from config import DIAS_AVISO_VENCIMIENTO

DIAS_AVISO = "dias_aviso_vencimiento"
MOSTRAR_AVISOS = "mostrar_avisos_al_abrir"


class PreferenciasRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def obtener(self, clave: str, defecto: str) -> str:
        try:
            row = self._conn.execute(
                "SELECT valor FROM preferencia WHERE clave = ?", (clave,)
            ).fetchone()
        except sqlite3.Error:
            return defecto
        return row["valor"] if row else defecto

    def guardar(self, clave: str, valor: str) -> None:
        self._conn.execute(
            """INSERT INTO preferencia (clave, valor) VALUES (?, ?)
               ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor""",
            (clave, str(valor)),
        )
        self._conn.commit()

    # --- Accesos cómodos ---

    def dias_aviso(self) -> int:
        try:
            return max(1, min(30, int(self.obtener(DIAS_AVISO, str(DIAS_AVISO_VENCIMIENTO)))))
        except ValueError:
            return DIAS_AVISO_VENCIMIENTO

    def mostrar_avisos(self) -> bool:
        return self.obtener(MOSTRAR_AVISOS, "1") == "1"
