import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config import formatear_moneda
from repository.categoria_repo import CategoriaRepo
from repository.gasto_repo import GastoRepo
from repository.miembro_repo import MiembroRepo
from services.resumen_service import ResumenService


class ExportService:
    """Servicio de exportación de gastos y resúmenes a formatos Excel (.xlsx) y CSV."""

    def __init__(
        self,
        gasto_repo: GastoRepo,
        categoria_repo: CategoriaRepo,
        miembro_repo: MiembroRepo,
        resumen_service: ResumenService,
        tarjeta_repo=None,
    ):
        self.gasto_repo = gasto_repo
        self.tarjeta_repo = tarjeta_repo
        self.categoria_repo = categoria_repo
        self.miembro_repo = miembro_repo
        self.resumen_service = resumen_service

    def exportar_a_excel(
        self, ruta_archivo: Path | str, anio: int, mes: int
    ) -> Path:
        """Genera un archivo Excel con dos hojas: 'Gastos' y 'Resumen por Categoría'."""
        wb = Workbook()

        # Estilos para cabeceras
        font_cabecera = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        fill_cabecera = PatternFill(
            start_color="2C3E50", end_color="2C3E50", fill_type="solid"
        )
        align_centro = Alignment(horizontal="center", vertical="center")
        align_derecha = Alignment(horizontal="right", vertical="center")
        borde_fino = Border(
            left=Side(style="thin", color="E0E0E0"),
            right=Side(style="thin", color="E0E0E0"),
            top=Side(style="thin", color="E0E0E0"),
            bottom=Side(style="thin", color="E0E0E0"),
        )
        font_total = Font(name="Calibri", size=11, bold=True)

        # ----------------- HOJA 1: GASTOS DETALLADOS -----------------
        ws_gastos = wb.active
        ws_gastos.title = "Gastos"

        cabeceras_gastos = [
            "Fecha",
            "Categoría",
            "Descripción",
            "Monto ($)",
            "Medio de Pago",
            "Cuotas",
        ]
        ws_gastos.append(cabeceras_gastos)

        for col_idx in range(1, len(cabeceras_gastos) + 1):
            celda = ws_gastos.cell(row=1, column=col_idx)
            celda.font = font_cabecera
            celda.fill = fill_cabecera
            celda.alignment = align_centro

        gastos = self.gasto_repo.listar_por_mes(anio, mes)
        cats = {c.id: c for c in self.categoria_repo.listar(solo_activas=False)}

        fila_actual = 2
        for g in gastos:
            cat_nom = cats[g.categoria_id].nombre if g.categoria_id in cats else "General"

            ws_gastos.append(
                [
                    g.fecha.strftime("%d/%m/%Y"),
                    cat_nom,
                    g.descripcion,
                    float(g.monto),
                    g.medio_pago,
                    g.cuotas or "",
                ]
            )

            # Formato de celda de monto como moneda
            celda_monto = ws_gastos.cell(row=fila_actual, column=4)
            celda_monto.number_format = "$ #,##0.00"
            celda_monto.alignment = align_derecha

            # Formato fecha centrada
            ws_gastos.cell(row=fila_actual, column=1).alignment = align_centro

            for c in range(1, len(cabeceras_gastos) + 1):
                ws_gastos.cell(row=fila_actual, column=c).border = borde_fino

            fila_actual += 1

        # Fila de Total en Hoja Gastos
        if fila_actual > 2:
            celda_lbl = ws_gastos.cell(row=fila_actual, column=3, value="Total del Mes:")
            celda_lbl.font = font_total
            celda_lbl.alignment = align_derecha

            celda_sum = ws_gastos.cell(
                row=fila_actual,
                column=4,
                value=f"=SUM(D2:D{fila_actual-1})",
            )
            celda_sum.font = font_total
            celda_sum.number_format = "$ #,##0.00"
            celda_sum.alignment = align_derecha

        # ----------------- HOJA 2: RESUMEN POR CATEGORÍA -----------------
        ws_resumen = wb.create_sheet(title="Resumen por Categoría")
        cabeceras_resumen = ["Categoría", "Total Gastado ($)", "% del Total"]
        ws_resumen.append(cabeceras_resumen)

        for col_idx in range(1, len(cabeceras_resumen) + 1):
            celda = ws_resumen.cell(row=1, column=col_idx)
            celda.font = font_cabecera
            celda.fill = PatternFill(
                start_color="16A085", end_color="16A085", fill_type="solid"
            )
            celda.alignment = align_centro

        totales_cat = self.resumen_service.totales_por_categoria(anio, mes)
        fila_res = 2
        for r in totales_cat:
            ws_resumen.append(
                [r["nombre"], float(r["total"]), float(r["porcentaje"]) / 100.0]
            )
            # Monto moneda
            c_monto = ws_resumen.cell(row=fila_res, column=2)
            c_monto.number_format = "$ #,##0.00"
            c_monto.alignment = align_derecha

            # Porcentaje
            c_pct = ws_resumen.cell(row=fila_res, column=3)
            c_pct.number_format = "0.0%"
            c_pct.alignment = align_derecha

            for c in range(1, len(cabeceras_resumen) + 1):
                ws_resumen.cell(row=fila_res, column=c).border = borde_fino

            fila_res += 1

        hojas = [ws_gastos, ws_resumen]

        # ----------------- HOJA 3: TARJETAS -----------------
        if self.tarjeta_repo is not None:
            hojas.append(
                self._hoja_tarjetas(wb, anio, mes, font_cabecera, align_centro, align_derecha, borde_fino, font_total)
            )

        # Autoajustar ancho de columnas
        for ws in hojas:
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        ruta = Path(ruta_archivo)
        wb.save(ruta)
        return ruta

    def _hoja_tarjetas(
        self, wb, anio, mes, font_cabecera, align_centro, align_derecha, borde_fino, font_total
    ):
        """Hoja 'Tarjetas': cuotas del mes, detalle de consumos y proyección de 6 meses."""
        from services.calendario_tarjetas import ETIQUETA_ESTADO, eventos_vencimiento_mes_repo
        from services.tarjeta_service import calcular_saldo_pendiente, proyeccion_6_meses

        ws = wb.create_sheet(title="Tarjetas")
        fill = PatternFill(start_color="2471A3", end_color="2471A3", fill_type="solid")
        font_titulo = Font(name="Calibri", size=13, bold=True, color="2C3E50")
        formato = "$ #,##0.00"

        def titulo(texto):
            ws.append([])
            ws.append([texto])
            ws.cell(row=ws.max_row, column=1).font = font_titulo

        def cabecera(columnas):
            ws.append(columnas)
            for i in range(1, len(columnas) + 1):
                c = ws.cell(row=ws.max_row, column=i)
                c.font, c.fill, c.alignment = font_cabecera, fill, align_centro

        def fila(valores, cols_moneda=()):
            ws.append(valores)
            r = ws.max_row
            for i in range(1, len(valores) + 1):
                c = ws.cell(row=r, column=i)
                c.border = borde_fino
                if i in cols_moneda:
                    c.number_format = formato
                    c.alignment = align_derecha

        # 1) Cuotas que vencen en el mes exportado
        ws.append([f"Tarjetas — cuotas que vencen en {mes:02d}/{anio}"])
        ws.cell(row=1, column=1).font = font_titulo
        cabecera(["Tarjeta", "Vence", "Consumo", "Cuota", "Monto ($)", "Estado", "En Planilla"])
        total_mes = 0
        for ev in eventos_vencimiento_mes_repo(self.tarjeta_repo, anio, mes):
            for c in ev.cuotas:
                fila(
                    [
                        ev.tarjeta_nombre,
                        ev.fecha.strftime("%d/%m/%Y"),
                        c.descripcion,
                        f"{c.numero_cuota}/{c.total_cuotas}",
                        c.monto_cent / 100,
                        "Pagada" if c.pagada else ETIQUETA_ESTADO[ev.estado],
                        "Sí" if ev.volcado_planilla else "No",
                    ],
                    cols_moneda=(5,),
                )
                total_mes += c.monto_cent
        ws.append(["", "", "", "Total del mes:", total_mes / 100])
        ws.cell(row=ws.max_row, column=4).font = font_total
        c = ws.cell(row=ws.max_row, column=5)
        c.font, c.number_format, c.alignment = font_total, formato, align_derecha

        # 2) Detalle de todos los consumos
        titulo("Detalle de consumos")
        cabecera(["Descripción", "Tarjeta", "Fecha compra", "Total ($)", "Cuotas", "Pagadas", "Valor cuota ($)", "Saldo pendiente ($)", "Estado"])
        tarjetas = {t.id: t.nombre for t in self.tarjeta_repo.listar()}
        for cons in self.tarjeta_repo.listar_consumos():
            fila(
                [
                    cons.descripcion,
                    tarjetas.get(cons.tarjeta_id, "—"),
                    date.fromisoformat(cons.fecha_compra).strftime("%d/%m/%Y"),
                    cons.monto_total_cent / 100,
                    cons.cantidad_cuotas,
                    cons.cuotas_pagadas,
                    cons.monto_cuota_cent / 100,
                    (calcular_saldo_pendiente(cons) if cons.estado == "activo" else 0) / 100,
                    cons.estado.capitalize(),
                ],
                cols_moneda=(4, 7, 8),
            )

        # 3) Proyección
        titulo("Proyección: cuotas a pagar en los próximos 6 meses")
        cabecera(["Mes", "Total ($)"])
        for a, m, total in proyeccion_6_meses(self.tarjeta_repo, date(anio, mes, 1)):
            fila([f"{m:02d}/{a}", total / 100], cols_moneda=(2,))
        return ws

    def exportar_a_csv(
        self, ruta_archivo: Path | str, anio: int, mes: int
    ) -> Path:
        """Exporta los gastos a CSV compatible con UTF-8 para Excel."""
        gastos = self.gasto_repo.listar_por_mes(anio, mes)
        cats = {c.id: c for c in self.categoria_repo.listar(solo_activas=False)}

        ruta = Path(ruta_archivo)
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(
                [
                    "Fecha",
                    "Categoría",
                    "Descripción",
                    "Monto",
                    "Medio de Pago",
                    "Cuotas",
                ]
            )
            for g in gastos:
                cat_nom = cats[g.categoria_id].nombre if g.categoria_id in cats else ""
                writer.writerow(
                    [
                        g.fecha.strftime("%d/%m/%Y"),
                        cat_nom,
                        g.descripcion,
                        str(g.monto).replace(".", ","),
                        g.medio_pago,
                        g.cuotas or "",
                    ]
                )

        return ruta
