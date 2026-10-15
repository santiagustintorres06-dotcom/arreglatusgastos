from datetime import date
from decimal import Decimal
import pytest
from PySide6.QtCore import QDate, QRect
from PySide6.QtGui import QImage, QPainter

from ui.calendario_widget import CalendarioGastosWidget


def test_calendario_gastos_widget_totales_y_pintado(qapp):
    widget = CalendarioGastosWidget()
    assert widget.monto_maximo == Decimal("0.00")

    # Cargar totales
    totales = {
        date(2026, 10, 10): Decimal("1500.00"),
        date(2026, 10, 15): Decimal("5000.00"),
        date(2026, 10, 20): Decimal("250.50"),
    }
    widget.actualizar_totales(totales)

    assert widget.monto_maximo == Decimal("5000.00")
    assert len(widget.totales_por_dia) == 3

    # Probar que paintCell ejecuta sin excepciones con un QPainter real sobre QImage
    imagen = QImage(100, 100, QImage.Format.Format_ARGB32)
    painter = QPainter(imagen)

    # Celda con gastos
    qdate_con_gasto = QDate(2026, 10, 15)
    widget.setCurrentPage(2026, 10)
    widget.paintCell(painter, QRect(0, 0, 80, 50), qdate_con_gasto)

    # Celda sin gastos
    qdate_sin_gasto = QDate(2026, 10, 1)
    widget.paintCell(painter, QRect(0, 0, 80, 50), qdate_sin_gasto)

    # Celda de otro mes
    qdate_otro_mes = QDate(2026, 9, 30)
    widget.paintCell(painter, QRect(0, 0, 80, 50), qdate_otro_mes)

    painter.end()
