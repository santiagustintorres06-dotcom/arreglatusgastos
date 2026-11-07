"""Crea una base de PRUEBA con datos de ejemplo y abre el programa con ella.

No toca los datos reales (data/gastos.db): usa la carpeta demo_datos/.
Uso:  .venv\\Scripts\\python.exe herramientas\\cargar_demo.py [--nueva]
  --nueva  borra la base de prueba anterior y la vuelve a crear.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DEMO_DIR = RAIZ / "demo_datos"
sys.path.insert(0, str(RAIZ))


def _sumar_meses(d: date, n: int, dia: int) -> date:
    import calendar

    total = d.month - 1 + n
    anio, mes = d.year + total // 12, total % 12 + 1
    return date(anio, mes, min(dia, calendar.monthrange(anio, mes)[1]))


def crear_datos_demo(ruta_bd: Path, hoy: date | None = None) -> None:
    from db.conexion import inicializar_bd, obtener_conexion
    from models.tarjeta import ConsumoTarjeta, Tarjeta
    from repository.categoria_repo import CategoriaRepo
    from repository.gasto_repo import GastoRepo
    from repository.tarjeta_repo import TarjetaRepo
    from services.gasto_service import GastoService

    hoy = hoy or date.today()
    conn = obtener_conexion(ruta_bd)
    inicializar_bd(conn)
    cats = CategoriaRepo(conn)
    gastos = GastoService(GastoRepo(conn), cats)
    tarjetas = TarjetaRepo(conn)

    def cat(nombre):
        return cats.obtener_por_nombre(nombre).id

    # Gastos de la Planilla: este mes y el anterior
    for delta, dia, monto, categoria, desc, medio in [
        (0, 2, "45800", "Supermercado", "Compra grande del mes", "Débito"),
        (0, 5, "18500", "Servicios", "Luz", "Transferencia"),
        (0, 6, "3200", "Supermercado", "Panadería", "Efectivo"),
        (-1, 3, "41200", "Supermercado", "Compra grande del mes", "Débito"),
        (-1, 12, "60000", "Vehículo", "Service del auto", "Transferencia"),
        (-1, 20, "9800", "Salud", "Farmacia", "Efectivo"),
    ]:
        f = _sumar_meses(hoy, delta, dia)
        if f <= hoy:
            gastos.crear(f, monto, cat(categoria), desc, medio)

    # Tarjetas con distinto cierre (como en la vida real)
    macro = tarjetas.crear(Tarjeta(nombre="Visa Macro", dia_cierre=22, dia_vencimiento=5, limite_cent=150000000))
    naranja = tarjetas.crear(Tarjeta(nombre="Naranja Visa", dia_cierre=28, dia_vencimiento=10))

    def consumo(tid, fecha, desc, cuota, cuotas, pagadas=0):
        tarjetas.crear_consumo(
            ConsumoTarjeta(
                tarjeta_id=tid,
                fecha_compra=fecha.isoformat(),
                descripcion=desc,
                monto_total_cent=cuota * 100 * cuotas,
                monto_cuota_cent=cuota * 100,
                cantidad_cuotas=cuotas,
                cuotas_pagadas=pagadas,
            )
        )

    consumo(macro, _sumar_meses(hoy, -3, 10), "Heladera", 25000, 6, pagadas=2)
    consumo(macro, _sumar_meses(hoy, -1, 15), "Zapatillas", 30000, 3)
    consumo(macro, hoy - timedelta(days=2), "Supermercado con tarjeta", 52000, 1)
    consumo(naranja, _sumar_meses(hoy, -2, 25), "Televisor", 40000, 12, pagadas=1)
    consumo(naranja, _sumar_meses(hoy, -1, 5), "Ropa", 15000, 2)
    conn.close()


def main() -> None:
    DEMO_DIR.mkdir(exist_ok=True)
    ruta = DEMO_DIR / "gastos.db"
    if "--nueva" in sys.argv and ruta.exists():
        ruta.unlink()
    if not ruta.exists():
        crear_datos_demo(ruta)
        print(f"Base de prueba creada en {ruta}")
    entorno = dict(os.environ, GASTOS_DATA_DIR=str(DEMO_DIR))
    subprocess.run([sys.executable, str(RAIZ / "main.py")], env=entorno, cwd=RAIZ)


if __name__ == "__main__":
    main()
