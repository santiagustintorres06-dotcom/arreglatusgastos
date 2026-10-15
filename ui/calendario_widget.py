from datetime import date
from decimal import Decimal

from PySide6.QtCore import QDate, QRect, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QCalendarWidget


class CalendarioGastosWidget(QCalendarWidget):
    """Subclase de QCalendarWidget que dibuja el mapa de calor y el monto total en cada celda."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.totales_por_dia: dict[date, Decimal] = {}
        self.monto_maximo: Decimal = Decimal("0.00")
        self.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.setGridVisible(True)

    def actualizar_totales(self, totales: dict[date, Decimal]) -> None:
        """Actualiza el mapa de gastos {date: Decimal} y recalcula la escala de calor."""
        self.totales_por_dia = dict(totales)
        if self.totales_por_dia:
            self.monto_maximo = max(self.totales_por_dia.values())
        else:
            self.monto_maximo = Decimal("0.00")
        self.updateCells()

    def paintCell(
        self, painter: QPainter, rect: QRect, qdate: QDate
    ) -> None:
        fecha_obj = date(qdate.year(), qdate.month(), qdate.day())
        es_mes_actual = qdate.month() == self.monthShown()
        es_seleccionado = qdate == self.selectedDate()
        total_dia = self.totales_por_dia.get(fecha_obj, Decimal("0.00"))

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Dibujar fondo de la celda
        if es_mes_actual and total_dia > 0 and self.monto_maximo > 0:
            # Mapa de calor: intensidad según el gasto relativo al día más caro del mes
            intensidad = float(total_dia / self.monto_maximo)
            # Intensidad entre alpha 45 y 200
            alpha = int(45 + intensidad * 155)
            color_fondo = QColor(231, 76, 60, alpha)  # Tono coral / rojizo
            painter.fillRect(rect, color_fondo)
        elif es_seleccionado:
            painter.fillRect(rect, QColor("#e8f4fd"))
        else:
            painter.fillRect(
                rect, QColor("#ffffff") if es_mes_actual else QColor("#f9f9f9")
            )

        # 2. Borde si está seleccionado
        if es_seleccionado:
            pen_sel = QPen(QColor("#2980b9"), 2)
            painter.setPen(pen_sel)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # 3. Dibujar número del día (arriba a la izquierda/centro)
        rect_dia = QRect(rect.x() + 4, rect.y() + 3, rect.width() - 8, 16)
        pen_texto = QPen(
            QColor("#2c3e50") if es_mes_actual else QColor("#bdc3c7")
        )
        painter.setPen(pen_texto)
        font_dia = painter.font()
        font_dia.setPointSize(9)
        if es_seleccionado:
            font_dia.setBold(True)
        painter.setFont(font_dia)
        painter.drawText(
            rect_dia,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            str(qdate.day()),
        )

        # 4. Dibujar monto del día si tiene gastos y pertenece al mes
        if es_mes_actual and total_dia > 0:
            rect_monto = QRect(
                rect.x() + 2,
                rect.y() + rect.height() // 2,
                rect.width() - 4,
                rect.height() // 2 - 3,
            )
            # Formato compacto para caber en la celda: $ 15.400 o $ 1.250,50
            if total_dia >= 1000:
                entero = int(total_dia)
                texto_monto = f"${entero:,.0f}".replace(",", ".")
            else:
                texto_monto = f"${total_dia:,.2f}".replace(".", ",")

            font_monto = QFont()
            font_monto.setPointSize(8)
            font_monto.setBold(True)
            painter.setFont(font_monto)

            # Contraste de texto según la intensidad del fondo
            if total_dia / self.monto_maximo > Decimal("0.65"):
                painter.setPen(QColor("#ffffff"))
            else:
                painter.setPen(QColor("#962d22"))

            painter.drawText(
                rect_monto,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                texto_monto,
            )

        painter.restore()
