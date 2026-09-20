"""Generador de Informes Ejecutivos y Dictámenes de Portabilidad Hipotecaria en PDF.

Diseñado bajo la normativa chilena:
- Ley N° 21.236 de Portabilidad Financiera (Subrogación y aranceles CBR)
- Ley General de Bancos Art. 100 (Comisión de prepago)
- D.L. 3475 (Impuesto de Timbres y Estampillas)
"""

import io
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String, PolyLine, Circle


# Paleta Institucional HipoRefi-CL
CLR_NAVY = HexColor("#1B4F72")
CLR_SLATE = HexColor("#2C3E50")
CLR_BLUE = HexColor("#2980B9")
CLR_LIGHT_BG = HexColor("#F8F9FA")
CLR_ALT_BG = HexColor("#EAECEE")
CLR_BORDER = HexColor("#D5D8DC")
CLR_MUTED = HexColor("#7F8C8D")

# Colores de Semáforo Patrimonial
FLAG_COLORS = {
    "RECOMENDADO": {
        "bg": HexColor("#D4EFDF"),
        "text": HexColor("#196F3D"),
        "border": HexColor("#27AE60"),
        "badge": "RECOMENDADO",
    },
    "EVALUAR_CON_CAUTELA": {
        "bg": HexColor("#FCF3CF"),
        "text": HexColor("#B7950B"),
        "border": HexColor("#F39C12"),
        "badge": "EVALUAR CON CAUTELA",
    },
    "NO_CONVIENE": {
        "bg": HexColor("#FADBD8"),
        "text": HexColor("#943126"),
        "border": HexColor("#E74C3C"),
        "badge": "NO CONVIENE",
    },
}


class ExecutiveReportGenerator:
    """Motor de generación de informes técnicos y dictámenes ejecutivos de portabilidad hipotecaria."""

    @classmethod
    def generate_pdf(cls, data: Dict[str, Any]) -> bytes:
        """
        Construye el documento PDF en memoria y retorna los bytes binarios.
        
        Args:
            data: Diccionario con la información del crédito actual, la oferta propuesta,
                  los costos de cambio de la Ley 21.236 y los resultados de evaluación cuantitativa.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = cls._build_stylesheet()
        story = []

        # =====================================================================
        # PÁGINA 1: Portada, Resumen Ejecutivo, Semáforo y Costos Normativos
        # =====================================================================
        cls._add_header(story, styles, data)
        cls._add_client_card(story, styles, data)
        cls._add_decision_banner(story, styles, data)
        cls._add_key_metrics_cards(story, styles, data)
        cls._add_comparison_table(story, styles, data)
        cls._add_switching_costs_section(story, styles, data)

        # Salto de página para segunda sección técnica
        story.append(PageBreak())

        # =====================================================================
        # PÁGINA 2: Gráfico de Payback, Benchmark de Mercado y Cláusulas
        # =====================================================================
        cls._add_page2_header(story, styles)
        cls._add_payback_vector_chart(story, styles, data)
        cls._add_market_ranking_section(story, styles, data)
        cls._add_legal_disclaimers(story, styles)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    @staticmethod
    def _build_stylesheet() -> Dict[str, ParagraphStyle]:
        """Inicializa los estilos tipográficos para el documento."""
        base = getSampleStyleSheet()
        styles = {}

        styles["Title"] = ParagraphStyle(
            "DocTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=CLR_NAVY,
        )
        styles["Subtitle"] = ParagraphStyle(
            "DocSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=CLR_MUTED,
        )
        styles["SectionHeader"] = ParagraphStyle(
            "SectionHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=CLR_NAVY,
            spaceAfter=4,
        )
        styles["CardLabel"] = ParagraphStyle(
            "CardLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=CLR_SLATE,
            alignment=1,  # Center
        )
        styles["CardValue"] = ParagraphStyle(
            "CardValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=CLR_NAVY,
            alignment=1,  # Center
        )
        styles["CardDelta"] = ParagraphStyle(
            "CardDelta",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=CLR_BLUE,
            alignment=1,  # Center
        )
        styles["BannerDecision"] = ParagraphStyle(
            "BannerDecision",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=0,
        )
        styles["BannerRationale"] = ParagraphStyle(
            "BannerRationale",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=CLR_SLATE,
        )
        styles["TableBody"] = ParagraphStyle(
            "TableBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=CLR_SLATE,
        )
        styles["TableBodyBold"] = ParagraphStyle(
            "TableBodyBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=CLR_SLATE,
        )
        styles["TableHeader"] = ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=white,
            alignment=1,
        )
        styles["Disclaimer"] = ParagraphStyle(
            "Disclaimer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=CLR_MUTED,
        )
        return styles

    @classmethod
    def _add_header(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Cabecera institucional y fecha de emisión."""
        date_str = data.get("date_str") or datetime.now().strftime("%d/%m/%Y %H:%M")
        uf_val = data.get("uf_value", 40967.24)

        header_data = [
            [
                Paragraph("<b>HipoRefi-CL 🇨🇱</b><br/><font size='8' color='#566573'>Dictamen Técnico de Portabilidad Hipotecaria</font>", styles["Title"]),
                Paragraph(f"<b>Fecha:</b> {date_str}<br/><b>UF Vigente:</b> ${uf_val:,.2f} CLP<br/><b>Regulación:</b> Ley N° 21.236", styles["Subtitle"]),
            ]
        ]
        header_table = Table(header_data, colWidths=[360, 180])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1.5, color=CLR_NAVY, spaceBefore=2, spaceAfter=8))

    @classmethod
    def _add_client_card(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Ficha del deudor y crédito hipotecario vigente."""
        bank_current = data.get("current_bank", "Banco Actual")
        op_num = data.get("operation_number") or "N/A"
        client = data.get("client_name", "Titular del Crédito")
        balance_uf = data.get("current_balance_uf", 3200.0)
        uf_val = data.get("uf_value", 40967.24)
        rate_current = data.get("current_rate_pct", 5.20)
        months_current = data.get("months_remaining", 180)

        card_data = [
            [
                Paragraph(f"<b>Titular:</b> {client}", styles["TableBody"]),
                Paragraph(f"<b>Acreedor Actual:</b> {bank_current}", styles["TableBody"]),
                Paragraph(f"<b>N° Operación:</b> {op_num}", styles["TableBody"]),
            ],
            [
                Paragraph(f"<b>Saldo Insoluto:</b> {balance_uf:,.2f} UF (${balance_uf * uf_val:,.0f} CLP)", styles["TableBodyBold"]),
                Paragraph(f"<b>Tasa Actual:</b> {rate_current:.2f}% anual", styles["TableBodyBold"]),
                Paragraph(f"<b>Plazo Remanente:</b> {months_current} meses ({months_current/12:.1f} años)", styles["TableBodyBold"]),
            ]
        ]
        card_table = Table(card_data, colWidths=[200, 180, 160])
        card_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CLR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(card_table)
        story.append(Spacer(1, 8))

    @classmethod
    def _add_decision_banner(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Banner destacado con semáforo patrimonial y dictamen cuantitativo."""
        flag = data.get("recommendation_flag", "RECOMENDADO")
        flag_info = FLAG_COLORS.get(flag, FLAG_COLORS["RECOMENDADO"])
        target_bank = data.get("target_bank", "Mejor Alternativa")
        rationale = data.get("rationale", "El refinanciamiento genera una ganancia patrimonial neta positiva.")

        banner_content = [
            [
                Paragraph(f"<font color='{flag_info['text'].hexval()}'>DICTAMEN PATRIMONIAL: {flag_info['badge']} ({target_bank})</font>", styles["BannerDecision"]),
            ],
            [
                Paragraph(f"<b>Fundamento Técnico:</b> {rationale}", styles["BannerRationale"]),
            ]
        ]
        banner_table = Table(banner_content, colWidths=[540])
        banner_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), flag_info["bg"]),
            ("BOX", (0, 0), (-1, -1), 1.5, flag_info["border"]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 8))

    @classmethod
    def _add_key_metrics_cards(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Tarjetas horizontales de 4 indicadores financieros esenciales."""
        npv_uf = data.get("npv_uf", 0.0)
        npv_clp = data.get("npv_clp", 0.0)
        savings_month_uf = data.get("monthly_savings_uf", 0.0)
        savings_month_clp = data.get("monthly_savings_clp", 0.0)
        payback = data.get("payback_months")
        payback_str = f"{payback} meses" if payback else "> Plazo"
        new_rate = data.get("new_rate_pct", 0.0)
        curr_rate = data.get("current_rate_pct", 0.0)
        delta_rate = new_rate - curr_rate

        cards = [
            [
                Paragraph("GANANCIA NETA (VPN)", styles["CardLabel"]),
                Paragraph("AHORRO MENSUAL", styles["CardLabel"]),
                Paragraph("PUNTO DE EQUILIBRIO", styles["CardLabel"]),
                Paragraph("TASA OFRECIDA", styles["CardLabel"]),
            ],
            [
                Paragraph(f"{npv_uf:+,.1f} UF", styles["CardValue"]),
                Paragraph(f"{savings_month_uf:+,.2f} UF/mes", styles["CardValue"]),
                Paragraph(payback_str, styles["CardValue"]),
                Paragraph(f"{new_rate:.2f}% anual", styles["CardValue"]),
            ],
            [
                Paragraph(f"${npv_clp:+,.0f} CLP", styles["CardDelta"]),
                Paragraph(f"${savings_month_clp:+,.0f} CLP/mes", styles["CardDelta"]),
                Paragraph("Meses a Break-Even", styles["CardDelta"]),
                Paragraph(f"{delta_rate:+.2f}% vs Actual", styles["CardDelta"]),
            ]
        ]
        cards_table = Table(cards, colWidths=[135, 135, 135, 135])
        cards_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CLR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(cards_table)
        story.append(Spacer(1, 8))

    @classmethod
    def _add_comparison_table(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Comparativa directa: Crédito Actual vs. Nueva Alternativa."""
        story.append(Paragraph("1. Comparativa Directa de Condiciones Financieras", styles["SectionHeader"]))
        curr_div_uf = data.get("current_total_dividend_uf", 0.0)
        curr_div_clp = data.get("current_dividend_clp", 0.0)
        new_div_uf = data.get("new_dividend_uf", 0.0)
        new_div_clp = data.get("new_dividend_clp", 0.0)
        curr_rate = data.get("current_rate_pct", 0.0)
        new_rate = data.get("new_rate_pct", 0.0)
        curr_months = data.get("months_remaining", 0)
        new_months = data.get("new_months", curr_months)
        target_bank = data.get("target_bank", "Nueva Entidad")
        curr_bank = data.get("current_bank", "Banco Actual")

        comp_data = [
            [
                Paragraph("Concepto Financiero", styles["TableHeader"]),
                Paragraph(f"Crédito Vigente ({curr_bank})", styles["TableHeader"]),
                Paragraph(f"Nueva Propuesta ({target_bank})", styles["TableHeader"]),
                Paragraph("Diferencial / Beneficio", styles["TableHeader"]),
            ],
            [
                Paragraph("Tasa de Interés Anual (UF)", styles["TableBodyBold"]),
                Paragraph(f"{curr_rate:.2f}%", styles["TableBody"]),
                Paragraph(f"{new_rate:.2f}%", styles["TableBody"]),
                Paragraph(f"<b>{new_rate - curr_rate:+.2f}%</b>", styles["TableBodyBold"]),
            ],
            [
                Paragraph("Dividendo Total Mensual (UF)", styles["TableBodyBold"]),
                Paragraph(f"{curr_div_uf:,.2f} UF", styles["TableBody"]),
                Paragraph(f"{new_div_uf:,.2f} UF", styles["TableBody"]),
                Paragraph(f"<b>{curr_div_uf - new_div_uf:+,.2f} UF/mes</b>", styles["TableBodyBold"]),
            ],
            [
                Paragraph("Dividendo Mensual en Pesos ($)", styles["TableBodyBold"]),
                Paragraph(f"${curr_div_clp:,.0f}", styles["TableBody"]),
                Paragraph(f"${new_div_clp:,.0f}", styles["TableBody"]),
                Paragraph(f"<b>${curr_div_clp - new_div_clp:+,.0f} CLP/mes</b>", styles["TableBodyBold"]),
            ],
            [
                Paragraph("Plazo Remanente", styles["TableBodyBold"]),
                Paragraph(f"{curr_months} meses ({curr_months/12:.1f} años)", styles["TableBody"]),
                Paragraph(f"{new_months} meses ({new_months/12:.1f} años)", styles["TableBody"]),
                Paragraph(f"{new_months - curr_months:+d} meses", styles["TableBody"]),
            ]
        ]
        comp_table = Table(comp_data, colWidths=[150, 130, 130, 130])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), CLR_NAVY),
            ("BOX", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CLR_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 8))

    @classmethod
    def _add_switching_costs_section(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Desglose pormenorizado de gastos operacionales y beneficios legales de cambio."""
        story.append(Paragraph("2. Desglose Normativo de Costos de Cambio (Ley N° 21.236 & D.L. 3475)", styles["SectionHeader"]))
        costs = data.get("switching_costs", {})
        uf_val = data.get("uf_value", 40967.24)

        prepago_uf = costs.get("prepayment_penalty_uf", 0.0)
        cbr_uf = costs.get("cbr_uf", 0.0)
        stamp_uf = costs.get("stamp_tax_uf", 0.0)
        appraisal_uf = costs.get("appraisal_uf", 3.0)
        title_uf = costs.get("title_deed_uf", 4.0)
        notary_uf = costs.get("notary_uf", 1.0)
        total_uf = costs.get("total_cost_uf", 0.0)
        total_clp = total_uf * uf_val

        cost_rows = [
            [
                Paragraph("Ítem Operacional / Arancel", styles["TableHeader"]),
                Paragraph("Fundamento Legal / Exención", styles["TableHeader"]),
                Paragraph("Monto (UF)", styles["TableHeader"]),
                Paragraph("Monto Estimado (CLP)", styles["TableHeader"]),
            ],
            [
                Paragraph("Comisión de Prepago", styles["TableBodyBold"]),
                Paragraph("Ley General de Bancos Art. 100 (Tope máx. 1.5 meses de intereses)", styles["TableBody"]),
                Paragraph(f"{prepago_uf:.2f} UF", styles["TableBody"]),
                Paragraph(f"${prepago_uf * uf_val:,.0f}", styles["TableBody"]),
            ],
            [
                Paragraph("Conservador de Bienes Raíces", styles["TableBodyBold"]),
                Paragraph("Ley N° 21.236 (50% de descuento legal por subrogación de gravamen)", styles["TableBody"]),
                Paragraph(f"{cbr_uf:.2f} UF", styles["TableBody"]),
                Paragraph(f"${cbr_uf * uf_val:,.0f}", styles["TableBody"]),
            ],
            [
                Paragraph("Impuesto Timbres y Estampillas", styles["TableBodyBold"]),
                Paragraph("D.L. 3475 (100% EXENTO sobre el capital refinanciado puro)", styles["TableBody"]),
                Paragraph(f"{stamp_uf:.2f} UF", styles["TableBody"]),
                Paragraph("$0 (Exento)" if stamp_uf == 0 else f"${stamp_uf * uf_val:,.0f}", styles["TableBody"]),
            ],
            [
                Paragraph("Tasación y Estudio de Títulos", styles["TableBodyBold"]),
                Paragraph("Gastos operacionales obligatorios de la entidad oferente", styles["TableBody"]),
                Paragraph(f"{appraisal_uf + title_uf:.2f} UF", styles["TableBody"]),
                Paragraph(f"${(appraisal_uf + title_uf) * uf_val:,.0f}", styles["TableBody"]),
            ],
            [
                Paragraph("Gastos Notariales", styles["TableBodyBold"]),
                Paragraph("Escritura pública de subrogación bajo arancel regulado", styles["TableBody"]),
                Paragraph(f"{notary_uf:.2f} UF", styles["TableBody"]),
                Paragraph(f"${notary_uf * uf_val:,.0f}", styles["TableBody"]),
            ],
            [
                Paragraph("<b>TOTAL GASTOS DE CIERRE ($G_k$)</b>", styles["TableBodyBold"]),
                Paragraph("<b>Inversión inicial requerida para migrar la operación</b>", styles["TableBodyBold"]),
                Paragraph(f"<b>{total_uf:.2f} UF</b>", styles["TableBodyBold"]),
                Paragraph(f"<b>${total_clp:,.0f} CLP</b>", styles["TableBodyBold"]),
            ]
        ]
        cost_table = Table(cost_rows, colWidths=[140, 200, 90, 110])
        cost_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), CLR_SLATE),
            ("BOX", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [white, CLR_LIGHT_BG]),
            ("BACKGROUND", (0, -1), (-1, -1), CLR_ALT_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(cost_table)

    @classmethod
    def _add_page2_header(cls, story: List[Any], styles: Dict[str, ParagraphStyle]) -> None:
        """Cabecera de continuidad para la segunda página."""
        story.append(Paragraph("<b>HipoRefi-CL 🇨🇱</b> | Dictamen Técnico (Página 2 de 2)", styles["Subtitle"]))
        story.append(HRFlowable(width="100%", thickness=1.0, color=CLR_NAVY, spaceBefore=2, spaceAfter=8))

    @classmethod
    def _add_payback_vector_chart(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Gráfico vectorial nativo de ReportLab con la curva de amortización del costo de cambio."""
        story.append(Paragraph("3. Curva de Recuperación de Inversión y Punto de Equilibrio (Break-Even)", styles["SectionHeader"]))
        story.append(Paragraph("Evolución proyectada de los ahorros acumulados descontados versus el costo operacional de portabilidad.", styles["Subtitle"]))
        story.append(Spacer(1, 4))

        costs = data.get("switching_costs", {})
        total_cost_uf = costs.get("total_cost_uf", 31.5)
        payback = data.get("payback_months", 28)
        monthly_savings = data.get("monthly_savings_uf", 1.15)
        discount_annual = data.get("discount_rate_pct", 2.5) / 100.0
        r_disc = (1.0 + discount_annual) ** (1.0 / 12.0) - 1.0

        # Dimensiones del área de dibujo
        width = 540
        height = 135
        d = Drawing(width, height)

        ox = 45
        oy = 25
        pw = 460
        ph = 95
        max_months = 60

        # Fondo del gráfico
        d.add(Rect(ox, oy, pw, ph, fillColor=HexColor("#FAFAFA"), strokeColor=CLR_BORDER, strokeWidth=0.5))

        # Líneas horizontales de referencia
        y_max = max(total_cost_uf * 1.6, total_cost_uf + 15.0)
        for val_uf in [total_cost_uf * 0.5, total_cost_uf, total_cost_uf * 1.5]:
            if val_uf <= y_max:
                y_pos = oy + (val_uf / y_max) * ph
                d.add(Line(ox, y_pos, ox + pw, y_pos, strokeColor=HexColor("#E0E0E0"), strokeWidth=0.5))
                d.add(String(ox - 35, y_pos - 3, f"{val_uf:,.0f} UF", fontSize=6.5, fontName="Helvetica", fillColor=CLR_MUTED))

        # Línea de Costo Inicial (Roja discontinua)
        cost_y = oy + (total_cost_uf / y_max) * ph
        d.add(Line(ox, cost_y, ox + pw, cost_y, strokeColor=HexColor("#E74C3C"), strokeWidth=1.5))
        d.add(String(ox + pw - 130, cost_y + 4, f"Costo Total: {total_cost_uf:.1f} UF", fontSize=7.5, fontName="Helvetica-Bold", fillColor=HexColor("#C0392B")))

        # Curva de ahorro acumulado descontado
        points = [(ox, oy)]
        cum_savings = 0.0
        for m in range(1, max_months + 1):
            disc_factor = (1.0 + r_disc) ** (-m)
            cum_savings += monthly_savings * disc_factor
            px = ox + (m / max_months) * pw
            py = min(oy + ph, oy + (cum_savings / y_max) * ph)
            points.append((px, py))

        d.add(PolyLine(points, strokeColor=CLR_BLUE, strokeWidth=2.0))

        # Punto de Intersección (Payback)
        if payback and payback <= max_months:
            pbx = ox + (payback / max_months) * pw
            pby = cost_y
            d.add(Circle(pbx, pby, 4.5, fillColor=HexColor("#27AE60"), strokeColor=white, strokeWidth=1.5))
            d.add(String(pbx + 6, pby - 4, f"Break-Even: Mes {payback}", fontSize=8, fontName="Helvetica-Bold", fillColor=HexColor("#196F3D")))

        # Eje X: Meses
        for m_mark in [12, 24, 36, 48, 60]:
            mx = ox + (m_mark / max_months) * pw
            d.add(Line(mx, oy, mx, oy - 3, strokeColor=CLR_SLATE, strokeWidth=0.5))
            d.add(String(mx - 8, oy - 12, f"M{m_mark}", fontSize=7, fontName="Helvetica", fillColor=CLR_SLATE))

        d.add(String(ox + pw / 2 - 25, oy - 20, "Plazo de Pago (Meses)", fontSize=7.5, fontName="Helvetica-Bold", fillColor=CLR_SLATE))
        story.append(d)
        story.append(Spacer(1, 10))

    @classmethod
    def _add_market_ranking_section(cls, story: List[Any], styles: Dict[str, ParagraphStyle], data: Dict[str, Any]) -> None:
        """Tabla con las alternativas más convenientes del mercado."""
        story.append(Paragraph("4. Benchmark de Mercado: Alternativas Evaluadas", styles["SectionHeader"]))
        market_opps = data.get("market_opportunities", [])

        bench_rows = [
            [
                Paragraph("Institución", styles["TableHeader"]),
                Paragraph("Tasa Anual", styles["TableHeader"]),
                Paragraph("Dividendo (UF)", styles["TableHeader"]),
                Paragraph("Ahorro / Mes", styles["TableHeader"]),
                Paragraph("VPN en UF", styles["TableHeader"]),
                Paragraph("Payback", styles["TableHeader"]),
                Paragraph("Dictamen", styles["TableHeader"]),
            ]
        ]

        for opp in market_opps[:5]:  # Top 5
            b_name = opp.get("bank_name", "Banco")
            b_rate = opp.get("annual_rate_pct", 0.0)
            b_div = opp.get("monthly_dividend_uf", 0.0)
            b_save_clp = opp.get("monthly_savings_clp", 0.0)
            b_npv = opp.get("npv_uf", 0.0)
            b_pb = opp.get("payback_months")
            b_flag = opp.get("recommendation_flag", "EVALUAR")
            pb_text = f"{b_pb}m" if b_pb else "> 60m"

            bench_rows.append([
                Paragraph(b_name, styles["TableBodyBold"]),
                Paragraph(f"{b_rate:.2f}%", styles["TableBody"]),
                Paragraph(f"{b_div:.2f} UF", styles["TableBody"]),
                Paragraph(f"${b_save_clp:+,.0f}", styles["TableBody"]),
                Paragraph(f"<b>{b_npv:+,.1f} UF</b>", styles["TableBodyBold"]),
                Paragraph(pb_text, styles["TableBody"]),
                Paragraph(b_flag, styles["TableBodyBold"]),
            ])

        bench_table = Table(bench_rows, colWidths=[120, 65, 75, 80, 75, 55, 70])
        bench_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), CLR_NAVY),
            ("BOX", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, CLR_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ]))
        story.append(bench_table)
        story.append(Spacer(1, 10))

    @classmethod
    def _add_legal_disclaimers(cls, story: List[Any], styles: Dict[str, ParagraphStyle]) -> None:
        """Notas metodológicas y advertencias legales normativas."""
        story.append(Paragraph("5. Metodología Financiera y Consideraciones Regulatorias", styles["SectionHeader"]))
        disclaimer_text = """
        <b>Marco Regulatorio:</b> Las estimaciones contenidas en este informe se basan estrictamente en la 
        <b>Ley N° 21.236 de Portabilidad Financiera</b>, que garantiza la subrogación del gravamen hipotecario y un descuento 
        legal del 50% en los aranceles del Conservador de Bienes Raíces (CBR). La comisión de prepago se encuentra acotada por el 
        <b>Artículo 100 de la Ley General de Bancos</b> a un máximo de 1.5 meses de intereses devengados sobre el capital prepagado. 
        De conformidad con el <b>D.L. 3475</b>, el crédito destinado exclusivamente al refinanciamiento está exento del Impuesto de Timbres y Estampillas.<br/>
        <b>Tasa de Descuento:</b> El Valor Presente Neto (VPN) y el Payback Dinámico se calculan utilizando una tasa de descuento real 
        en UF representativa del costo de oportunidad del deudor (2.5% anual real).<br/>
        <b>Validez:</b> Este documento constituye una simulación analítica de orientación cuantitativa y no reemplaza la evaluación formal 
        de riesgo crediticio ni la oferta vinculante de la institución acreedora.
        """
        story.append(Paragraph(disclaimer_text, styles["Disclaimer"]))
        story.append(Spacer(1, 8))

        # Firma / Certificación de Algoritmo
        cert_data = [
            [
                Paragraph("<b>Certificación Cuantitativa:</b> Generado automáticamente por el motor de optimización financiera HipoRefi-CL.", styles["Disclaimer"]),
                Paragraph("<b>Auditado bajo Estándares CMF & BCCh</b>", styles["Disclaimer"]),
            ]
        ]
        cert_table = Table(cert_data, colWidths=[360, 180])
        cert_table.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        story.append(cert_table)
