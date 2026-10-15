# Organizador de Gastos Familiares

Aplicación de escritorio en Python para registrar y visualizar los gastos mensuales de una familia, con sincronización en tiempo real entre vista planilla (tipo Excel) y vista calendario.

## Características Principales

- **Vista Planilla:** Carga rápida y edición directa de gastos por fecha, categoría, descripción, monto, medio de pago y miembro.
- **Vista Calendario:** Visualización mensual con totales por día y mapa de calor de intensidad de gasto.
- **Sincronización en tiempo real:** Cualquier cambio en una vista se refleja inmediatamente en la otra.
- **Precisión monetaria:** Almacenamiento en centavos enteros en base de datos (`INTEGER`) y manejo en `Decimal` para evitar errores de redondeo.
- **Arquitectura en capas:** UI (PySide6) -> Servicios -> Repositorio -> Base de datos (SQLite).
- **Modo portable:** Diseñado para correr de manera autónoma con SQLite local y backups automáticos diarios.

## Requisitos y Configuración

```bash
# Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar tests
pytest
```
