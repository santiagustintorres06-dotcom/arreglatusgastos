from pathlib import Path

from db.conexion import inicializar_bd, obtener_conexion
from services.ubicacion_datos import (
    guardar_ignorados,
    leer_ignorados,
    otras_copias_con_datos,
)


def _crear_copia(carpeta: Path, gastos: int) -> Path:
    ruta = carpeta / "data" / "gastos.db"
    ruta.parent.mkdir(parents=True)
    conn = obtener_conexion(ruta)
    inicializar_bd(conn)
    for i in range(gastos):
        conn.execute("INSERT INTO gasto (fecha, monto_cent, categoria_id) VALUES ('2026-11-01', 100, 1)")
    conn.commit()
    conn.close()
    return ruta


def test_detecta_otra_carpeta_con_datos(tmp_path: Path):
    escritorio = tmp_path / "Desktop"
    descargas = tmp_path / "Downloads"
    actual = _crear_copia(escritorio / "GastosFamilia", gastos=0)
    otra = _crear_copia(descargas / "GastosFamilia (1)", gastos=3)
    _crear_copia(descargas / "vacia" / "GastosFamilia", gastos=0)  # sin datos: no se avisa

    copias = otras_copias_con_datos(actual, raices=[escritorio, descargas])

    assert [c.ruta_bd for c in copias] == [otra.resolve()]
    assert copias[0].cantidad_gastos == 3
    assert copias[0].carpeta_programa.name == "GastosFamilia (1)"


def test_no_se_avisa_a_si_misma(tmp_path: Path):
    actual = _crear_copia(tmp_path / "GastosFamilia", gastos=5)
    assert otras_copias_con_datos(actual, raices=[tmp_path]) == []


def test_ignorados(tmp_path: Path):
    guardar_ignorados(tmp_path, {"C:/a/data/gastos.db"})
    assert leer_ignorados(tmp_path) == {"C:/a/data/gastos.db"}
