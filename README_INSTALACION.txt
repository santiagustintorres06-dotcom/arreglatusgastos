========================================================
  ORGANIZADOR DE GASTOS FAMILIARES
  Versión portable — no requiere instalar nada
========================================================

CÓMO USAR:
----------
1. Copiá la carpeta "GastosFamilia" completa a donde quieras
   (en tu PC, en un pendrive, en el escritorio, donde prefieras).

2. Doble clic en el archivo:
       GastosFamilia\GastosFamilia.exe

¡Y listo! El programa se abre directamente.

DÓNDE SE GUARDAN LOS DATOS:
----------------------------
Todos tus datos (gastos, categorías, miembros) se guardan
automáticamente dentro de la carpeta del programa, en:

   GastosFamilia\data\gastos.db

Eso significa que si copias toda la carpeta a otro lugar,
tus datos van con ella. ¡Es completamente portable!

BACKUPS AUTOMÁTICOS:
--------------------
El programa hace un backup automático cada vez que lo abrís.
Los backups se guardan en:

   GastosFamilia\data\backups\

Se conservan los últimos 30 backups, así que tus datos
siempre están protegidos.

CATEGORÍAS DISPONIBLES:
-----------------------
  - Supermercado
  - Servicios
  - Casa
  - Vehículo (combustible, seguro, service, etc.)
  - Salud
  - Ocio
  - Educación
  - Otros

FUNCIONES PRINCIPALES:
----------------------
  ✔ Registrar gastos con fecha, categoría y monto
  ✔ Ver resumen mensual en tabla (tipo planilla Excel)
  ✔ Navegar mes a mes con los botones de la barra superior
  ✔ Calendario con colores que muestran los días con más gastos
  ✔ Exportar a Excel (.xlsx) o CSV
  ✔ Eliminar, duplicar y editar gastos existentes
  ✔ Buscar gastos por descripción
  ✔ Filtrar por categoría o miembro de la familia

SOLUCIÓN DE PROBLEMAS:
-----------------------
• Si el programa no abre: verificá que copiaste la carpeta
  completa "GastosFamilia" y no solo el archivo .exe.

• Si ves errores al abrir: revisar el archivo de registro en
      GastosFamilia\logs\app.log

• "Cargué cosas y no aparecen": fijate abajo a la izquierda de la
  ventana dónde dice "📁 Datos en: ...". Cada carpeta GastosFamilia
  guarda SUS propios datos. Usá siempre la misma carpeta. Si el
  programa encuentra otra copia con datos, te avisa al abrir.

• Para recuperar datos: en GastosFamilia\data\backups\ hay un
  respaldo por día (gastos_AAAAMMDD.db) y uno del último cierre
  (gastos_ultimo_cierre.db).

PROBAR SIN TOCAR LOS DATOS REALES:
----------------------------------
Doble clic en "Probar con datos de ejemplo.bat". Se abre el programa
con datos inventados (el título dice MODO PRUEBA). Lo que hagas ahí
se guarda aparte, en GastosFamilia\demo_datos\.

PARA QUIEN ACTUALIZA EL PROGRAMA:
---------------------------------
• Generar el portable SIEMPRE con build.bat (conserva los datos).
  Nunca ejecutar PyInstaller a mano: borra la carpeta data.
• Al reemplazar una versión vieja, copiar todo MENOS la carpeta data\.

========================================================
  Desarrollado con Python + PySide6  |  Oct 2026
========================================================
