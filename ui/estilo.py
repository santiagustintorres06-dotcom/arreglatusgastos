# ui/estilo.py
"""
Hoja de estilos QSS global para la aplicación GastosFamilia.
Se aplica una sola vez en main.py mediante app.setStyleSheet(STYLESHEET).
"""

# Paleta de colores
VERDE_ACENTO = "#27ae60"
VERDE_HOVER = "#2ecc71"
VERDE_PRESSED = "#1e8449"
AZUL_ACENTO = "#2980b9"
AZUL_HOVER = "#3498db"
AZUL_PRESSED = "#1a6698"
GRIS_OSCURO = "#2c3e50"
GRIS_MEDIO = "#34495e"
GRIS_CLARO = "#ecf0f1"
GRIS_BORDE = "#bdc3c7"
FONDO_APP = "#f4f6f8"
FONDO_TABLA_ALT = "#eaf4fb"
ROJO_ALERTA = "#e74c3c"
TEXTO_PRINCIPAL = "#2c3e50"
TEXTO_SECUNDARIO = "#7f8c8d"

STYLESHEET = f"""
/* ═══════════════════════════════════════════════════
   BASE — Ventana y Widgets Generales
═══════════════════════════════════════════════════ */
QMainWindow, QDialog {{
    background-color: {FONDO_APP};
}}

QWidget {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    color: {TEXTO_PRINCIPAL};
}}

/* ═══════════════════════════════════════════════════
   BOTONES
═══════════════════════════════════════════════════ */
QPushButton {{
    background-color: #dfe6e9;
    color: {GRIS_OSCURO};
    border: 1px solid {GRIS_BORDE};
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 600;
    min-width: 90px;
}}

QPushButton:hover {{
    background-color: #c8d6e5;
    border-color: #a0b0c0;
}}

QPushButton:pressed {{
    background-color: #b2bec3;
}}

QPushButton:disabled {{
    background-color: #ecf0f1;
    color: {GRIS_BORDE};
    border-color: {GRIS_CLARO};
}}

/* Botón primario — guardar/agregar */
QPushButton[class="btn-primary"] {{
    background-color: {VERDE_ACENTO};
    color: white;
    border: 1px solid {VERDE_PRESSED};
}}
QPushButton[class="btn-primary"]:hover {{
    background-color: {VERDE_HOVER};
}}
QPushButton[class="btn-primary"]:pressed {{
    background-color: {VERDE_PRESSED};
}}

/* Botón secundario — exportar / acción secundaria */
QPushButton[class="btn-secondary"] {{
    background-color: {GRIS_MEDIO};
    color: white;
    border: 1px solid {GRIS_OSCURO};
}}
QPushButton[class="btn-secondary"]:hover {{
    background-color: #4a6885;
}}
QPushButton[class="btn-secondary"]:pressed {{
    background-color: {GRIS_OSCURO};
}}

/* Botón navegación período (mes anterior / mes siguiente) */
QPushButton[class="btn-nav"] {{
    background-color: {AZUL_ACENTO};
    color: white;
    border: 1px solid {AZUL_PRESSED};
    border-radius: 5px;
    padding: 6px 16px;
    font-weight: 700;
    min-width: 130px;
}}
QPushButton[class="btn-nav"]:hover {{
    background-color: {AZUL_HOVER};
}}
QPushButton[class="btn-nav"]:pressed {{
    background-color: {AZUL_PRESSED};
}}

/* Botón "Mes Actual" — neutro */
QPushButton[class="btn-hoy"] {{
    background-color: #636e72;
    color: white;
    border: 1px solid #2d3436;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton[class="btn-hoy"]:hover {{
    background-color: #74b9ff;
    border-color: {AZUL_PRESSED};
}}

/* Botón en panel calendario (agregar para ese día) */
QPushButton[class="btn-cal"] {{
    background-color: {AZUL_ACENTO};
    color: white;
    border: 1px solid {AZUL_PRESSED};
    border-radius: 5px;
    padding: 8px;
    font-weight: 700;
}}
QPushButton[class="btn-cal"]:hover {{
    background-color: {AZUL_HOVER};
}}

/* ═══════════════════════════════════════════════════
   TABLA DE GASTOS
═══════════════════════════════════════════════════ */
QTableView {{
    background-color: white;
    alternate-background-color: {FONDO_TABLA_ALT};
    gridline-color: #dfe6e9;
    border: 1px solid {GRIS_BORDE};
    border-radius: 4px;
    selection-background-color: #d4e6f1;
    selection-color: {GRIS_OSCURO};
}}

QTableView::item {{
    padding: 4px 8px;
    min-height: 28px;
}}

QTableView::item:selected {{
    background-color: #d4e6f1;
    color: {GRIS_OSCURO};
}}

QHeaderView::section {{
    background-color: {GRIS_MEDIO};
    color: white;
    font-weight: 700;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #4a6885;
    border-bottom: 2px solid {VERDE_ACENTO};
}}

QHeaderView::section:first {{
    border-top-left-radius: 4px;
}}

QHeaderView::section:last {{
    border-right: none;
    border-top-right-radius: 4px;
}}

QHeaderView::section:horizontal:hover {{
    background-color: #4a6885;
}}

QHeaderView[orientation="vertical"]::section {{
    background-color: #f0f3f4;
    color: {TEXTO_SECUNDARIO};
    font-weight: 600;
    border: none;
    border-bottom: 1px solid {GRIS_BORDE};
    border-right: 2px solid {VERDE_ACENTO};
    padding: 2px 6px;
}}

/* ═══════════════════════════════════════════════════
   PESTAÑAS (QTabWidget / QTabBar)
═══════════════════════════════════════════════════ */
QTabWidget::pane {{
    border: 1px solid {GRIS_BORDE};
    border-top: 3px solid {VERDE_ACENTO};
    border-radius: 0px 4px 4px 4px;
    background-color: white;
}}

QTabBar::tab {{
    background-color: #dfe6e9;
    color: {GRIS_OSCURO};
    padding: 8px 20px;
    border: 1px solid {GRIS_BORDE};
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: 600;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: white;
    color: {VERDE_ACENTO};
    border-bottom: 3px solid {VERDE_ACENTO};
    font-weight: 700;
}}

QTabBar::tab:hover:!selected {{
    background-color: #c8d6e5;
}}

/* ═══════════════════════════════════════════════════
   INPUTS: LineEdit, ComboBox, DateEdit
═══════════════════════════════════════════════════ */
QLineEdit, QDateEdit {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
    border-radius: 4px;
    padding: 5px 8px;
    color: {TEXTO_PRINCIPAL};
    min-height: 22px;
}}

QLineEdit:focus, QDateEdit:focus {{
    border: 2px solid {AZUL_ACENTO};
    padding: 4px 7px;
}}

QLineEdit:disabled, QDateEdit:disabled {{
    background-color: #f4f6f8;
    color: {GRIS_BORDE};
}}

QComboBox {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
    border-radius: 4px;
    padding: 5px 8px;
    color: {TEXTO_PRINCIPAL};
    min-height: 22px;
    min-width: 120px;
}}

QComboBox:focus {{
    border: 2px solid {AZUL_ACENTO};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid {GRIS_BORDE};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}}

QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
    selection-background-color: {AZUL_ACENTO};
    selection-color: white;
    outline: none;
}}

/* ═══════════════════════════════════════════════════
   FRAMES / PANEL PiE DE TABLA
═══════════════════════════════════════════════════ */
QFrame[frameShape="4"] {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
    border-radius: 4px;
}}

/* ═══════════════════════════════════════════════════
   BARRA DE ESTADO
═══════════════════════════════════════════════════ */
QStatusBar {{
    background-color: {GRIS_OSCURO};
    color: white;
    font-weight: 600;
    border-top: 2px solid {VERDE_ACENTO};
}}

QStatusBar QLabel {{
    color: white;
    padding: 2px 6px;
}}

/* ═══════════════════════════════════════════════════
   LABEL PERÍODO PRINCIPAL
═══════════════════════════════════════════════════ */
QLabel[class="lbl-periodo"] {{
    color: {GRIS_OSCURO};
    font-size: 15pt;
    font-weight: 700;
    padding: 4px 10px;
}}

/* ═══════════════════════════════════════════════════
   SCROLLBARS
═══════════════════════════════════════════════════ */
QScrollBar:vertical {{
    background-color: {GRIS_CLARO};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {GRIS_BORDE};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: #a0b0c0;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {GRIS_CLARO};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {GRIS_BORDE};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: #a0b0c0;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ═══════════════════════════════════════════════════
   LISTA DE GASTOS DEL DÍA (panel calendario)
═══════════════════════════════════════════════════ */
QListWidget {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-bottom: 1px solid {GRIS_CLARO};
}}
QListWidget::item:selected {{
    background-color: #d4e6f1;
    color: {GRIS_OSCURO};
}}
QListWidget::item:hover {{
    background-color: #eaf4fb;
}}

/* ═══════════════════════════════════════════════════
   BARRA SUPERIOR DE PERÍODO (QFrame contenedor)
═══════════════════════════════════════════════════ */
QFrame[class="barra-periodo"] {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
    border-radius: 6px;
    padding: 2px;
}}

/* ═══════════════════════════════════════════════════
   MENSAJES (QMessageBox)
═══════════════════════════════════════════════════ */
QMessageBox {{
    background-color: {FONDO_APP};
}}
QMessageBox QLabel {{
    color: {TEXTO_PRINCIPAL};
    font-size: 10pt;
}}

/* ═══════════════════════════════════════════════════
   CALENDARIO NATIVO (cabecera de días)
═══════════════════════════════════════════════════ */
QCalendarWidget QToolButton {{
    background-color: {GRIS_MEDIO};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: 700;
}}
QCalendarWidget QToolButton:hover {{
    background-color: {AZUL_ACENTO};
}}
QCalendarWidget QMenu {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
}}
QCalendarWidget QAbstractItemView:enabled {{
    font-size: 10pt;
    color: {TEXTO_PRINCIPAL};
    selection-background-color: {AZUL_ACENTO};
    selection-color: white;
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {GRIS_MEDIO};
    border-radius: 4px;
    padding: 4px;
}}

/* ═══════════════════════════════════════════════════
   FRAME PANEL DETALLE CALENDARIO
═══════════════════════════════════════════════════ */
QFrame[class="panel-detalle"] {{
    background-color: white;
    border: 1px solid {GRIS_BORDE};
    border-radius: 6px;
}}

/* ═══════════════════════════════════════════════════
   TOOLTIP
═══════════════════════════════════════════════════ */
QToolTip {{
    background-color: {GRIS_OSCURO};
    color: white;
    border: 1px solid {VERDE_ACENTO};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 9pt;
}}
"""
