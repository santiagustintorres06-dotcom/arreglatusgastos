"""Gráfico simple de barras: cuotas de tarjeta a pagar en los próximos 6 meses.

Dibujado con QPainter (sin librerías extra) para ver cuándo "se libera plata".
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from config import formatear_moneda
from repository.tarjeta_repo import TarjetaRepo
from services.tarjeta_service import proyeccion_6_meses

MESES_CORTOS = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
COLOR_BARRA = "#2471a3"
COLOR_BARRA_ACTUAL = "#d35400"


def texto_compacto(monto: Decimal) -> str:
    """$ 1,2 M / $ 350 mil / $ 900, para que entre arriba de la barra."""
    if monto >= 1_000_000:
        return f"$ {monto / 1_000_000:.1f} M".replace(".", ",")
    if monto >= 1000:
        return f"$ {int(monto / 1000)} mil"
    return f"$ {int(monto)}"


class GraficoBarras(QWidget):
    """Barras verticales con etiqueta de mes y monto."""

    def __init__(self, datos: list[tuple[str, Decimal]] | None = None, parent=None):
        super().__init__(parent)
        self.datos: list[tuple[str, Decimal]] = datos or []
        self.setMinimumSize(420, 240)

    def fijar_datos(self, datos: list[tuple[str, Decimal]]) -> None:
        self.datos = datos
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nombre de Qt)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#ffffff"))
        if not self.datos:
            p.end()
            return

        margen_x, margen_sup, margen_inf = 16, 34, 34
        ancho = self.width() - 2 * margen_x
        alto = self.height() - margen_sup - margen_inf
        maximo = max((m for _, m in self.datos), default=Decimal(0))
        n = len(self.datos)
        hueco = ancho / n
        ancho_barra = hueco * 0.6

        base_y = margen_sup + alto
        p.setPen(QPen(QColor("#bdc3c7"), 1))
        p.drawLine(margen_x, int(base_y), margen_x + ancho, int(base_y))

        f_monto = QFont()
        f_monto.setPointSize(9)
        f_monto.setBold(True)
        f_mes = QFont()
        f_mes.setPointSize(10)

        for i, (etiqueta, monto) in enumerate(self.datos):
            x = margen_x + i * hueco + (hueco - ancho_barra) / 2
            h = 0 if maximo == 0 else float(monto / maximo) * alto
            color = QColor(COLOR_BARRA_ACTUAL if i == 0 else COLOR_BARRA)
            if monto > 0:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(color)
                p.drawRoundedRect(QRectF(x, base_y - h, ancho_barra, h), 4, 4)
            # Monto arriba de la barra
            p.setPen(QColor("#2c3e50"))
            p.setFont(f_monto)
            p.drawText(
                QRectF(x - 20, base_y - h - 22, ancho_barra + 40, 20),
                Qt.AlignmentFlag.AlignCenter,
                texto_compacto(monto) if monto > 0 else "$ 0",
            )
            # Mes abajo
            p.setFont(f_mes)
            p.drawText(
                QRectF(x - 20, base_y + 6, ancho_barra + 40, 22),
                Qt.AlignmentFlag.AlignCenter,
                etiqueta,
            )
        p.end()


def datos_proyeccion(repo: TarjetaRepo, hoy: date | None = None) -> list[tuple[str, Decimal]]:
    """[(\"Nov 2026\", monto), ...] de los próximos 6 meses (cuotas sin pagar)."""
    return [
        (f"{MESES_CORTOS[mes]} {anio}", Decimal(total) / 100)
        for anio, mes, total in proyeccion_6_meses(repo, hoy)
    ]


class DialogoProyeccion(QDialog):
    def __init__(self, repo: TarjetaRepo, parent=None, hoy: date | None = None):
        super().__init__(parent)
        self.setWindowTitle("📊 Cuotas de tarjeta: próximos 6 meses")
        self.setModal(True)
        self.resize(680, 420)
        datos = datos_proyeccion(repo, hoy)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        titulo = QLabel("Cuánto hay que pagar de tarjetas cada mes (cuotas todavía no pagadas)")
        titulo.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(titulo)

        self.grafico = GraficoBarras(datos, self)
        layout.addWidget(self.grafico, stretch=1)

        # Lectura en palabras: cuándo baja la carga
        self.lbl_resumen = QLabel(self._explicacion(datos))
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setStyleSheet(
            "background-color: #eaf2f8; color: #1b4f72; border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(self.lbl_resumen)

        fila = QHBoxLayout()
        fila.addStretch()
        btn = QPushButton("Cerrar")
        btn.setProperty("class", "btn-secondary")
        btn.clicked.connect(self.accept)
        fila.addWidget(btn)
        layout.addLayout(fila)

    @staticmethod
    def _explicacion(datos: list[tuple[str, Decimal]]) -> str:
        if not datos or all(m == 0 for _, m in datos):
            return "No hay cuotas pendientes en los próximos 6 meses."
        partes = [f"Este mes: {formatear_moneda(datos[0][1])}."]
        for i in range(1, len(datos)):
            if datos[i][1] < datos[i - 1][1]:
                libera = datos[i - 1][1] - datos[i][1]
                partes.append(f"En {datos[i][0]} se liberan {formatear_moneda(libera)}.")
        if datos[-1][1] == 0:
            primero_cero = next(e for e, m in datos if m == 0)
            partes.append(f"Desde {primero_cero} no quedan cuotas (de lo cargado hasta hoy).")
        return " ".join(partes)
