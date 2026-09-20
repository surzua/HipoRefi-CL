"""Generadores de gráficos financieros interactivos con Plotly para HipoRefi-CL."""

from typing import List, Dict, Any, Optional
import numpy as np
import plotly.graph_objects as go

from src.core.amortizer import FrenchAmortizer, MortgageParams


def create_market_npv_chart(opportunities: List[Dict[str, Any]]) -> go.Figure:
    """Genera un gráfico de barras interactivo con el VPN generado por cada entidad financiera."""
    institutions = [opp["institution_name"] for opp in opportunities]
    npvs = [opp["evaluation"]["npv_uf"] for opp in opportunities]
    rates = [opp["annual_rate_pct"] for opp in opportunities]

    colors = ["#2ECC71" if npv > 20 else "#F39C12" if npv > 0 else "#E74C3C" for npv in npvs]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=institutions,
        y=npvs,
        text=[f"{npv:+.1f} UF<br>({rate:.2f}%)" for npv, rate in zip(npvs, rates)],
        textposition="outside",
        marker=dict(
            color=colors,
            line=dict(color="#2C3E50", width=1.2),
        ),
        hovertemplate="<b>%{x}</b><br>VPN: %{y:.2f} UF<extra></extra>",
    ))

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#7F8C8D",
        annotation_text="Punto Neutro (VPN = 0)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="<b>Ganancia Patrimonial Neta (VPN) por Banco / Mutuaria</b>",
        xaxis_title="Entidad Financiera",
        yaxis_title="Valor Presente Neto en UF",
        template="plotly_white",
        height=450,
        margin=dict(l=40, r=40, t=60, b=80),
        xaxis=dict(tickangle=-25),
    )
    return fig


def create_payback_trajectory_chart(
    current_schedule: List[Dict[str, Any]],
    new_schedule: List[Dict[str, Any]],
    upfront_costs_uf: float,
    payback_months: Optional[int],
    annual_discount_rate: float = 0.025,
    institution_name: str = "Nueva Opción",
) -> go.Figure:
    """Genera la curva de flujo acumulado descontado mostrando el punto de equilibrio (Break-Even)."""
    max_months = max(len(current_schedule), len(new_schedule))
    months_axis = list(range(1, max_months + 1))
    monthly_discount = (1.0 + annual_discount_rate) ** (1.0 / 12.0) - 1.0

    flows_curr = np.zeros(max_months)
    flows_new = np.zeros(max_months)

    for i, row in enumerate(current_schedule):
        flows_curr[i] = row["total_dividend_uf"]
    for i, row in enumerate(new_schedule):
        flows_new[i] = row["total_dividend_uf"]

    monthly_diff = flows_curr - flows_new

    # Flujo neto acumulado descontado iniciando en -upfront_costs
    cum_net_cashflow = []
    running = -upfront_costs_uf
    for m_idx, diff in enumerate(monthly_diff, 1):
        disc_factor = (1.0 + monthly_discount) ** (-m_idx)
        running += diff * disc_factor
        cum_net_cashflow.append(running)

    fig = go.Figure()

    # Área de ganancia y pérdida
    fig.add_trace(go.Scatter(
        x=months_axis,
        y=cum_net_cashflow,
        mode="lines",
        name="Flujo Neto Acumulado Descontado",
        line=dict(color="#1B4F72", width=3.5),
        fill="tozeroy",
        fillcolor="rgba(41, 128, 185, 0.15)",
        hovertemplate="Mes %{x}: <b>%{y:+.2f} UF</b><extra></extra>",
    ))

    # Línea de equilibrio (Break-Even)
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#E74C3C",
        line_width=2,
        annotation_text="Punto de Equilibrio (Break-Even = 0 UF)",
        annotation_position="top left",
    )

    # Línea vertical de Payback
    if payback_months and payback_months <= max_months:
        fig.add_vline(
            x=payback_months,
            line_dash="dot",
            line_color="#27AE60",
            line_width=2.5,
            annotation_text=f"Recuperación: Mes {payback_months} (~{payback_months/12:.1f} años)",
            annotation_position="top right",
        )

    fig.update_layout(
        title=f"<b>Trayectoria de Retorno de la Inversión y Payback ({institution_name})</b>",
        xaxis_title="Meses Transcurridos",
        yaxis_title="Flujo Neto Acumulado Descontado (UF)",
        template="plotly_white",
        hovermode="x unified",
        height=450,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_amortization_comparison_chart(
    current_schedule: List[Dict[str, Any]],
    new_schedule: List[Dict[str, Any]],
    current_label: str = "Crédito Actual",
    new_label: str = "Nuevo Crédito",
) -> go.Figure:
    """Compara la evolución del saldo insoluto de capital mes a mes."""
    curr_months = [row["month"] for row in current_schedule]
    curr_balances = [row["end_balance_uf"] for row in current_schedule]

    new_months = [row["month"] for row in new_schedule]
    new_balances = [row["end_balance_uf"] for row in new_schedule]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curr_months,
        y=curr_balances,
        mode="lines",
        name=current_label,
        line=dict(color="#C0392B", width=2.8),
        hovertemplate="%{y:,.1f} UF",
    ))
    fig.add_trace(go.Scatter(
        x=new_months,
        y=new_balances,
        mode="lines",
        name=new_label,
        line=dict(color="#27AE60", width=2.8, dash="dash"),
        hovertemplate="%{y:,.1f} UF",
    ))

    fig.update_layout(
        title="<b>Evolución del Saldo Insoluto de Capital en el Tiempo</b>",
        xaxis_title="Mes del Crédito",
        yaxis_title="Saldo de Capital (UF)",
        template="plotly_white",
        height=400,
        legend=dict(x=0.7, y=0.95),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_sensitivity_heatmap(
    current_balance_uf: float,
    current_rate_pct: float,
    current_months: int,
    upfront_costs_uf: float,
    annual_discount_rate: float = 0.025,
) -> go.Figure:
    """Genera una matriz 2D (Heatmap) de VPN según combinaciones de Tasa Nueva y Plazo."""
    rate_deltas = [-1.5, -1.0, -0.75, -0.5, -0.25, 0.0, +0.5]
    new_rates = [round(max(2.0, current_rate_pct + delta), 2) for delta in rate_deltas]
    terms_years = [10, 15, 20, 25, 30]

    # Generar tabla actual
    params_curr = MortgageParams(
        principal=current_balance_uf,
        annual_rate=current_rate_pct / 100.0,
        months_remaining=current_months,
    )
    sched_curr = FrenchAmortizer.generate_schedule(params_curr)
    monthly_disc = (1.0 + annual_discount_rate) ** (1.0 / 12.0) - 1.0

    z_matrix = []
    for r in new_rates:
        row = []
        for t_years in terms_years:
            t_months = t_years * 12
            params_new = MortgageParams(
                principal=current_balance_uf,
                annual_rate=r / 100.0,
                months_remaining=t_months,
            )
            sched_new = FrenchAmortizer.generate_schedule(params_new)

            max_m = max(current_months, t_months)
            fc = np.zeros(max_m)
            fn = np.zeros(max_m)
            for i, item in enumerate(sched_curr):
                fc[i] = item["total_dividend_uf"]
            for i, item in enumerate(sched_new):
                fn[i] = item["total_dividend_uf"]

            diff = fc - fn
            disc_factors = np.array([(1.0 + monthly_disc) ** (-m) for m in range(1, max_m + 1)])
            npv = float(-upfront_costs_uf + np.sum(diff * disc_factors))
            row.append(round(npv, 1))
        z_matrix.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=[f"{t} años" for t in terms_years],
        y=[f"{r:.2f}%" for r in new_rates],
        colorscale="RdYlGn",
        text=[[f"{val:+.1f} UF" for val in row] for row in z_matrix],
        texttemplate="%{text}",
        hoverongaps=False,
        colorbar=dict(title="VPN (UF)"),
    ))

    fig.update_layout(
        title="<b>Matriz de Sensibilidad Patrimonial: Tasa Nueva vs Plazo (VPN en UF)</b>",
        xaxis_title="Nuevo Plazo Pactado",
        yaxis_title="Nueva Tasa Anual Ofrecida",
        template="plotly_white",
        height=450,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_dividend_fallacy_chart(
    current_schedule: List[Dict[str, Any]],
    trap_schedule: List[Dict[str, Any]],
    current_label: str = "Mantener Plazo Actual",
    trap_label: str = "Oferta Trampa (Alargar Plazo)",
) -> go.Figure:
    """Compara el costo total acumulado de la deuda (capital + intereses) para ilustrar la Falacia del Dividendo."""
    curr_principal = current_schedule[0]["start_balance_uf"]
    curr_interest = sum(row["interest_uf"] for row in current_schedule)
    trap_interest = sum(row["interest_uf"] for row in trap_schedule)

    categories = [current_label, trap_label]
    interest_vals = [curr_interest, trap_interest]
    principal_vals = [curr_principal, curr_principal]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Capital Amortizado (UF)",
        x=categories,
        y=principal_vals,
        marker_color="#2980B9",
        text=[f"{v:,.1f} UF" for v in principal_vals],
        textposition="inside",
    ))
    fig.add_trace(go.Bar(
        name="Intereses Totales Pagados (UF)",
        x=categories,
        y=interest_vals,
        marker_color="#E74C3C",
        text=[f"{v:,.1f} UF" for v in interest_vals],
        textposition="inside",
    ))

    fig.update_layout(
        barmode="stack",
        title="<b>Costo Total de la Deuda: La 'Falacia del Dividendo' en Números</b>",
        xaxis_title="Escenario de Financiamiento",
        yaxis_title="Desembolso Total Acumulado (UF)",
        template="plotly_white",
        height=450,
        legend=dict(x=0.02, y=0.98),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


# ============================================================================
# Visualizaciones de Hito 8: Módulo Financiero y Normativo Avanzado
# ============================================================================

def create_prepayment_comparison_chart(
    base_schedule: List[Dict[str, Any]],
    term_schedule: List[Dict[str, Any]],
    div_schedule: List[Dict[str, Any]],
) -> go.Figure:
    """Genera la comparativa de trayectorias de dividendo entre crédito base y las dos opciones de prepago."""
    max_months = len(base_schedule)
    months_axis = list(range(1, max_months + 1))

    flows_base = [r["total_dividend_uf"] for r in base_schedule]
    flows_div = [r["total_dividend_uf"] for r in div_schedule]

    # Para reducción de plazo, tras terminar el crédito el dividendo es 0
    flows_term = [r["total_dividend_uf"] for r in term_schedule]
    if len(flows_term) < max_months:
        flows_term.extend([0.0] * (max_months - len(flows_term)))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=months_axis,
        y=flows_base,
        mode="lines",
        name="Crédito Original (Sin Prepago)",
        line=dict(color="#7F8C8D", width=2, dash="dash"),
        hovertemplate="Mes %{x}: <b>%{y:.2f} UF</b><extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=months_axis,
        y=flows_term,
        mode="lines",
        name="Opción A: Reducir Plazo",
        line=dict(color="#2980B9", width=3),
        hovertemplate="Mes %{x}: <b>%{y:.2f} UF</b><extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=months_axis,
        y=flows_div,
        mode="lines",
        name="Opción B: Reducir Dividendo",
        line=dict(color="#27AE60", width=3),
        hovertemplate="Mes %{x}: <b>%{y:.2f} UF</b><extra></extra>",
    ))

    if len(term_schedule) < max_months:
        fig.add_vline(
            x=len(term_schedule),
            line_dash="dot",
            line_color="#2980B9",
            annotation_text=f"Fin Opción Plazo (Mes {len(term_schedule)})",
            annotation_position="top right",
        )

    fig.update_layout(
        title="<b>Comparativa de Flujos de Dividendos: Abono Extraordinario</b>",
        xaxis_title="Mes del Crédito",
        yaxis_title="Dividendo Mensual Total (UF)",
        template="plotly_white",
        height=450,
        legend=dict(x=0.02, y=0.98),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_mixed_rate_stress_chart(
    pure_fixed_dividend: float,
    scenarios: List[Any],
    fixed_period_months: int,
    total_months: int,
) -> go.Figure:
    """Genera el gráfico de trayectorias de dividendo bajo los escenarios de estrés de tasa mixta."""
    months_axis = list(range(1, total_months + 1))
    colors = {
        -150: "#27AE60",  # Bajista
        0: "#2980B9",     # Base
        150: "#E67E22",   # Alcista
        300: "#C0392B",   # Severo
    }

    fig = go.Figure()

    # Línea de crédito 100% fijo puro
    fig.add_trace(go.Scatter(
        x=months_axis,
        y=[pure_fixed_dividend] * total_months,
        mode="lines",
        name=f"100% Fijo ({pure_fixed_dividend:.2f} UF)",
        line=dict(color="#2C3E50", width=2.5, dash="dash"),
        hovertemplate="Mes %{x}: <b>%{y:.2f} UF</b> (Fijo Puro)<extra></extra>",
    ))

    # Trazar cada escenario
    for sc in scenarios:
        bps = getattr(sc, "rate_change_bps", 0)
        name = getattr(sc, "scenario_name", "Escenario")
        initial_div = getattr(sc, "initial_dividend_uf", 0.0)
        sub_div = getattr(sc, "subsequent_dividend_uf", 0.0)

        # Flujo de este escenario
        flows = [initial_div] * fixed_period_months + [sub_div] * (total_months - fixed_period_months)

        fig.add_trace(go.Scatter(
            x=months_axis,
            y=flows,
            mode="lines",
            name=f"{name} ({sub_div:.2f} UF)",
            line=dict(color=colors.get(bps, "#8E44AD"), width=2),
            hovertemplate="Mes %{x}: <b>%{y:.2f} UF</b><extra></extra>",
        ))

    # Hito del mes de cambio de tasa
    fig.add_vline(
        x=fixed_period_months,
        line_dash="dot",
        line_color="#7F8C8D",
        annotation_text=f"Reinicio de Tasa (Mes {fixed_period_months})",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="<b>Matriz de Estrés de Dividendos: Tasa Mixta vs. Fija</b>",
        xaxis_title="Mes del Crédito",
        yaxis_title="Dividendo Mensual Total (UF)",
        template="plotly_white",
        height=450,
        legend=dict(x=0.02, y=0.98),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_french_vs_german_chart(
    french_schedule: List[Dict[str, Any]],
    german_schedule: List[Dict[str, Any]],
) -> go.Figure:
    """Genera la comparativa cuota a cuota entre sistema francés y sistema alemán."""
    months_axis = [r["month"] for r in french_schedule]
    french_divs = [r["total_dividend_uf"] for r in french_schedule]
    german_divs = [r["total_dividend_uf"] for r in german_schedule]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=months_axis,
        y=french_divs,
        mode="lines",
        name="Sistema Francés (Dividendo Constante)",
        line=dict(color="#2980B9", width=3),
        hovertemplate="Mes %{x}: <b>%{y:.2f} UF</b> (Francés)<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=months_axis,
        y=german_divs,
        mode="lines",
        name="Sistema Alemán (Cuota Decreciente)",
        line=dict(color="#8E44AD", width=3),
        hovertemplate="Mes %{x}: <b>%{y:.2f} UF</b> (Alemán)<extra></extra>",
    ))

    # Punto de cruce aproximado
    cross_month = None
    for i, (f, g) in enumerate(zip(french_divs, german_divs)):
        if g <= f:
            cross_month = i + 1
            break

    if cross_month:
        fig.add_vline(
            x=cross_month,
            line_dash="dash",
            line_color="#27AE60",
            annotation_text=f"Punto de Cruce (Mes {cross_month})",
            annotation_position="top right",
        )

    fig.update_layout(
        title="<b>Perfil de Dividendos: Sistema Alemán vs. Francés</b>",
        xaxis_title="Mes del Crédito",
        yaxis_title="Dividendo Mensual Total (UF)",
        template="plotly_white",
        height=450,
        legend=dict(x=0.02, y=0.98),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_actuarial_insurability_gauge(maturity_age: int, status: str) -> go.Figure:
    """Genera un indicador gráfico tipo velocímetro / gauge para la edad al vencimiento del crédito."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=maturity_age,
        title={"text": f"<b>Edad al Vencimiento ({maturity_age} años) - {status}</b>", "font": {"size": 16}},
        gauge={
            "axis": {"range": [18, 90], "tickwidth": 1, "tickcolor": "#2C3E50"},
            "bar": {"color": "#1B4F72", "thickness": 0.3},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "#BDC3C7",
            "steps": [
                {"range": [18, 70], "color": "#D4EFDF"},
                {"range": [70, 75], "color": "#FCF3CF"},
                {"range": [75, 80], "color": "#FAD7A0"},
                {"range": [80, 90], "color": "#FADBD8"},
            ],
            "threshold": {
                "line": {"color": "#C0392B", "width": 4},
                "thickness": 0.8,
                "value": maturity_age,
            },
        },
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    return fig

