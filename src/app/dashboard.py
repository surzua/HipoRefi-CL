"""Dashboard Interactivo de Optimización de Refinanciamiento Hipotecario en Chile.

Construido con Streamlit y Plotly. Cumple con la normativa chilena:
Ley N° 21.236 (Portabilidad Financiera), D.L. 3475 (Timbres y Estampillas) y LGB Art. 100.
"""

import sys
from pathlib import Path
import io
import pandas as pd
import streamlit as st

# Asegurar importación de src si se ejecuta como script independiente
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator
from src.core.metrics import RefinanceAnalyzer
from src.scrapers.market_service import MarketDataService
from src.parsers.statement_extractor import StatementExtractor
from src.parsers.pdf_reader import PDFReader
from src.app.charts import (
    create_market_npv_chart,
    create_payback_trajectory_chart,
    create_amortization_comparison_chart,
    create_sensitivity_heatmap,
    create_dividend_fallacy_chart,
)


# ============================================================================
# Configuración General de la Página y Estilos
# ============================================================================

st.set_page_config(
    page_title="HipoRefi-CL | Optimización Hipotecaria",
    page_icon="🇨🇱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B4F72;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #566573;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #F8F9F9 0%, #EBEDEF 100%);
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #2980B9;
        margin-bottom: 10px;
    }
    .badge-recommended {
        background-color: #D4EFDF;
        color: #196F3D;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-caution {
        background-color: #FCF3CF;
        color: #B7950B;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-not-recommended {
        background-color: #FADBD8;
        color: #943126;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Inicialización de Servicios y Estado de Sesión
# ============================================================================

market_service = MarketDataService()
extractor = StatementExtractor(mode="auto")

# Inicialización de session state para parámetros del crédito
if "balance_uf" not in st.session_state:
    st.session_state["balance_uf"] = 3200.0
if "annual_rate_pct" not in st.session_state:
    st.session_state["annual_rate_pct"] = 5.20
if "months_remaining" not in st.session_state:
    st.session_state["months_remaining"] = 180
if "current_dividend_uf" not in st.session_state:
    st.session_state["current_dividend_uf"] = 23.10
if "fire_insurance_uf" not in st.session_state:
    st.session_state["fire_insurance_uf"] = 0.70
if "detected_bank" not in st.session_state:
    st.session_state["detected_bank"] = "Banco de Chile"


# ============================================================================
# Encabezado Principal e Indicadores Macroeconómicos
# ============================================================================

st.markdown('<div class="main-title">🇨🇱 HipoRefi-CL: Motor de Optimización Hipotecaria</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Evaluación Cuantitativa de Refinanciamiento, Costos Normativos (Ley N° 21.236) y Benchmark de Mercado</div>', unsafe_allow_html=True)

uf_current = market_service.get_current_uf()
overview = market_service.get_market_overview()
macro_rates = overview.get("latest_macro_rates", {})

col_uf, col_tpm, col_cmf, col_ley = st.columns(4)

with col_uf:
    st.metric(
        label="Valor UF Vigente",
        value=f"${uf_current:,.2f} CLP",
        delta="Chile Real-Time",
    )

with col_tpm:
    tpm_val = overview.get("tpm_current", 4.50)
    st.metric(
        label="TPM (Banco Central)",
        value=f"{tpm_val:.2f}%",
        delta="Tasa Política Monetaria",
    )

with col_cmf:
    cmf_val = macro_rates.get("F072.CLP.COL.VIV.Z.M", {}).get("value", 4.92)
    st.metric(
        label="Tasa Promedio CMF",
        value=f"{cmf_val:.2f}%",
        delta="Créditos Vivienda",
    )

with col_ley:
    st.metric(
        label="Ley N° 21.236",
        value="Activa",
        delta="50% Descuento CBR",
    )

st.divider()


# ============================================================================
# Barra Lateral: Ingesta Documental y Parámetros del Crédito
# ============================================================================

with st.sidebar:
    st.header("📄 Ingesta de Cartola")
    st.caption("Sube tu estado de cuenta o cartola hipotecaria bancaria en PDF.")

    uploaded_pdf = st.file_uploader(
        "Subir Cartola en PDF (Drag & Drop)",
        type=["pdf"],
        help="El documento se analiza localmente de forma privada para extraer automáticamente las variables.",
    )

    if uploaded_pdf is not None:
        try:
            pdf_bytes = uploaded_pdf.read()
            extracted = extractor.extract_from_pdf(io.BytesIO(pdf_bytes))

            st.session_state["balance_uf"] = extracted.current_balance_uf
            st.session_state["annual_rate_pct"] = extracted.annual_interest_rate_pct
            st.session_state["months_remaining"] = extracted.remaining_installments
            st.session_state["current_dividend_uf"] = extracted.current_total_dividend_uf
            if extracted.fire_insurance_uf:
                st.session_state["fire_insurance_uf"] = extracted.fire_insurance_uf
            st.session_state["detected_bank"] = extracted.bank_name

            st.success(f"✓ Extraído con éxito: {extracted.bank_name}")
            st.caption(f"Operación: {extracted.operation_number or 'N/A'}")
        except Exception as e:
            st.error(f"No fue posible procesar el PDF: {e}")

    st.header("⚙️ Crédito Actual")

    st.text_input(
        "Banco Acreedor Actual",
        key="detected_bank",
    )

    balance_uf = st.number_input(
        "Saldo Insoluto de Capital (UF)",
        min_value=100.0,
        max_value=50000.0,
        step=50.0,
        key="balance_uf",
    )
    st.caption(f"Equivalente a: **${balance_uf * uf_current:,.0f} CLP**")

    annual_rate_pct = st.number_input(
        "Tasa Anual Pactada (%)",
        min_value=1.0,
        max_value=15.0,
        step=0.05,
        format="%.2f",
        key="annual_rate_pct",
    )

    months_remaining = st.number_input(
        "Plazo Restante (Meses)",
        min_value=12,
        max_value=480,
        step=6,
        key="months_remaining",
    )
    st.caption(f"Plazo restante: **{months_remaining/12:.1f} años**")

    current_dividend_uf = st.number_input(
        "Dividendo Mensual Actual (UF)",
        min_value=1.0,
        max_value=500.0,
        step=0.5,
        key="current_dividend_uf",
    )
    st.caption(f"Equivalente a: **${current_dividend_uf * uf_current:,.0f} CLP/mes**")

    fire_insurance_uf = st.number_input(
        "Seguro Incendio y Sismo Mensual (UF)",
        min_value=0.0,
        max_value=10.0,
        step=0.05,
        key="fire_insurance_uf",
    )

    st.header("🛡️ Parámetros de Refinanciamiento")

    finance_costs = st.checkbox(
        "¿Financiar gastos operacionales en nuevo crédito?",
        value=False,
        help="Si marcas esta casilla, los costos de cambio no se pagan al contado en t=0, sino que se suman al capital del nuevo préstamo.",
    )

    additional_cash_uf = st.number_input(
        "Capital adicional libre disposición (UF)",
        min_value=0.0,
        max_value=5000.0,
        value=0.0,
        step=50.0,
        help="Monto de dinero fresco solicitado. Bajo el D.L. 3475, este capital tributa con el 0.8% del impuesto de timbres.",
    )
    if additional_cash_uf > 0:
        st.warning(f"⚠️ Capital fresco tributa {additional_cash_uf * 0.008:.2f} UF (${additional_cash_uf * 0.008 * uf_current:,.0f} CLP) por Impuesto de Timbres (D.L. 3475).")

    discount_rate_pct = st.slider(
        "Tasa de Descuento de Oportunidad (Anual en UF)",
        min_value=1.0,
        max_value=5.0,
        value=2.5,
        step=0.25,
        help="Costo de oportunidad del capital en términos reales (por encima de la UF).",
    )


# ============================================================================
# Cálculos de Base del Crédito Actual y Costos Normativos
# ============================================================================

current_rate_dec = annual_rate_pct / 100.0
discount_rate_dec = discount_rate_pct / 100.0

# 1. Tabla de amortización del crédito actual
params_curr = MortgageParams(
    principal=balance_uf,
    annual_rate=current_rate_dec,
    months_remaining=months_remaining,
    fire_insurance_monthly_uf=fire_insurance_uf,
    life_insurance_rate_monthly=0.00028,
)
sched_curr = FrenchAmortizer.generate_schedule(params_curr)

# 2. Costos de cambio normativos
costs = SwitchingCostCalculator.calculate_total_costs(
    balance_uf=balance_uf,
    current_annual_rate=current_rate_dec,
    additional_cash_uf=additional_cash_uf,
)

# 3. Evaluación global contra el mercado
market_eval = market_service.evaluate_refinance_against_market(
    current_balance_uf=balance_uf,
    current_annual_rate=current_rate_dec,
    months_remaining=months_remaining,
    current_total_dividend_uf=current_dividend_uf,
    fire_insurance_uf=fire_insurance_uf,
    finance_costs=finance_costs,
)

opportunities = market_eval.get("all_opportunities", [])
best_opp = market_eval.get("best_opportunity")


# ============================================================================
# Pestañas Principales de la Aplicación
# ============================================================================

tab_market, tab_breakeven, tab_sim, tab_fallacy, tab_schedule = st.tabs([
    "🏆 Comparador de Mercado",
    "📈 Punto de Equilibrio & Payback",
    "🎛️ Simulador a Medida & Sensibilidad",
    "⚠️ Detector de la 'Falacia del Dividendo'",
    "📋 Tabla de Amortización",
])


# ----------------------------------------------------------------------------
# PESTAÑA 1: Comparador de Mercado
# ----------------------------------------------------------------------------
with tab_market:
    st.subheader("Benchmark de Mercado: Bancos y Mutuarias de Chile")
    st.caption("Comparación de tu crédito actual contra las tasas comerciales vigentes modeladas según estándares CMF.")

    if best_opp:
        best_quote = best_opp["bank_quote"]
        best_decision = best_opp["evaluation"]

        # Tarjeta destacada de la mejor oportunidad
        st.markdown(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #1B4F72;">🥇 Mejor Alternativa: {best_quote['bank_name']}</h3>
                <span class="{'badge-recommended' if best_decision['recommendation_flag'] == 'RECOMENDADO' else 'badge-caution'}">
                    {best_decision['recommendation_flag']}
                </span>
            </div>
            <p style="margin-top: 8px; color: #2C3E50;">{best_decision['rationale']}</p>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            label="Ganancia Patrimonial (VPN)",
            value=f"{best_decision['npv_uf']:+,.1f} UF",
            delta=f"${best_decision['npv_uf'] * uf_current:+,.0f} CLP",
        )
        m2.metric(
            label="Ahorro Mensual",
            value=f"{best_decision['monthly_savings_uf']:,.2f} UF/mes",
            delta=f"${best_decision['monthly_savings_uf'] * uf_current:,.0f} CLP/mes",
        )
        m3.metric(
            label="Tiempo de Recuperación (Payback)",
            value=f"{best_decision['payback_months']} meses" if best_decision['payback_months'] else "> Plazo",
            delta="Punto de Equilibrio",
        )
        m4.metric(
            label="Tasa Ofrecida",
            value=f"{best_quote['annual_rate_pct']:.2f}% anual",
            delta=f"{best_quote['annual_rate_pct'] - annual_rate_pct:+.2f}% vs Actual",
            delta_color="inverse",
        )

    st.write("")

    # Desglose de Costos de Cambio
    with st.expander("💼 Desglose Normativo de Gastos de Cambio (Ley N° 21.236 & DL 3475)", expanded=False):
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.markdown(f"""
            - **Comisión de Prepago (LGB Art. 100):** {costs.prepayment_penalty_uf:.2f} UF (${costs.prepayment_penalty_uf * uf_current:,.0f} CLP)  
              *(Tope legal máximo de 1.5 meses de intereses devengados)*
            - **Conservador de Bienes Raíces (CBR):** {costs.cbr_uf:.2f} UF (${costs.cbr_uf * uf_current:,.0f} CLP)  
              *(Incluye beneficio legal del 50% de descuento por subrogación)*
            - **Impuesto de Timbres y Estampillas (D.L. 3475):** {costs.stamp_tax_uf:.2f} UF  
              *(100% EXENTO sobre el capital refinanciado)*
            """)
        with c_col2:
            st.markdown(f"""
            - **Tasación Comercial:** {costs.appraisal_uf:.2f} UF (${costs.appraisal_uf * uf_current:,.0f} CLP)
            - **Estudio de Títulos y Redacción:** {costs.title_deed_uf:.2f} UF (${costs.title_deed_uf * uf_current:,.0f} CLP)
            - **Gastos Notariales Regulados:** {costs.notary_uf:.2f} UF (${costs.notary_uf * uf_current:,.0f} CLP)
            - **COSTO TOTAL OPERACIONAL:** **{costs.total_cost_uf:.2f} UF** (**${costs.total_cost_uf * uf_current:,.0f} CLP**)
            """)

    # Gráfico de barras de VPN por entidad
    opps_for_chart = [
        {
            "institution_name": o["bank_quote"]["bank_name"],
            "evaluation": o["evaluation"],
            "annual_rate_pct": o["bank_quote"]["annual_rate_pct"],
        }
        for o in opportunities
    ]
    st.plotly_chart(create_market_npv_chart(opps_for_chart), use_container_width=True)

    # Tabla comparativa completa
    st.subheader("Tabla Comparativa de Alternativas")
    table_data = []
    for o in opportunities:
        bq = o["bank_quote"]
        ev = o["evaluation"]
        table_data.append({
            "Institución": bq["bank_name"],
            "Tipo de Tasa": bq["loan_type"],
            "Tasa Anual (%)": f"{bq['annual_rate_pct']:.2f}%",
            "Dividendo (UF)": f"{bq['monthly_total_dividend_uf']:.2f} UF",
            "Dividendo (CLP)": f"${bq['monthly_total_dividend_uf'] * uf_current:,.0f}",
            "Ahorro Mensual": f"${ev['monthly_savings_uf'] * uf_current:+,.0f}",
            "VPN en UF": f"{ev['npv_uf']:+,.1f} UF",
            "Payback": f"{ev['payback_months']} meses" if ev['payback_months'] else "> Plazo",
            "Dictamen": ev["recommendation_flag"],
        })

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------
# PESTAÑA 2: Punto de Equilibrio y Trayectoria
# ----------------------------------------------------------------------------
with tab_breakeven:
    st.subheader("Trayectoria de Recuperación y Break-Even Dinámico")
    st.caption("Visualiza el momento exacto en que los ahorros acumulados pagan los costos de cierre y comienzan a generar patrimonio neto.")

    if opportunities:
        bank_names = [o["bank_quote"]["bank_name"] for o in opportunities]
        selected_bank_name = st.selectbox("Seleccionar Banco para Analizar Trayectoria:", bank_names, index=0)

        selected_opp = next(o for o in opportunities if o["bank_quote"]["bank_name"] == selected_bank_name)
        s_quote = selected_opp["bank_quote"]
        s_eval = selected_opp["evaluation"]

        # Generar tabla del crédito nuevo
        s_rate_dec = s_quote["annual_rate_pct"] / 100.0
        s_principal = balance_uf + (costs.total_cost_uf if finance_costs else 0.0) + additional_cash_uf
        s_months = s_quote["term_years"] * 12

        params_new = MortgageParams(
            principal=s_principal,
            annual_rate=s_rate_dec,
            months_remaining=s_months,
            fire_insurance_monthly_uf=s_quote["fire_insurance_uf"],
            life_insurance_rate_monthly=0.00028,
        )
        sched_new = FrenchAmortizer.generate_schedule(params_new)

        # Gráficos Plotly
        st.plotly_chart(
            create_payback_trajectory_chart(
                current_schedule=sched_curr,
                new_schedule=sched_new,
                upfront_costs_uf=costs.total_cost_uf,
                payback_months=s_eval["payback_months"],
                annual_discount_rate=discount_rate_dec,
                institution_name=selected_bank_name,
            ),
            use_container_width=True,
        )

        st.plotly_chart(
            create_amortization_comparison_chart(
                current_schedule=sched_curr,
                new_schedule=sched_new,
                current_label=f"Crédito Actual ({annual_rate_pct:.2f}%)",
                new_label=f"{selected_bank_name} ({s_quote['annual_rate_pct']:.2f}%)",
            ),
            use_container_width=True,
        )


# ----------------------------------------------------------------------------
# PESTAÑA 3: Simulador a Medida y Matriz de Sensibilidad
# ----------------------------------------------------------------------------
with tab_sim:
    st.subheader("Simulador Personalizado de Contraofertas")
    st.caption("Si recibiste una oferta específica de un banco o ejecutivo comercial, modélala aquí.")

    c_sim1, c_sim2, c_sim3 = st.columns(3)
    with c_sim1:
        custom_bank = st.text_input("Nombre de la Entidad Oferente", value="Banco BCI")
    with c_sim2:
        custom_rate = st.slider("Tasa Anual Ofrecida (%)", min_value=2.5, max_value=8.0, value=4.20, step=0.05, format="%.2f")
    with c_sim3:
        custom_term_years = st.slider("Plazo en Años", min_value=5, max_value=30, value=round(months_remaining/12), step=1)

    # Evaluación en tiempo real
    c_rate_dec = custom_rate / 100.0
    c_principal = balance_uf + (costs.total_cost_uf if finance_costs else 0.0) + additional_cash_uf
    c_months = custom_term_years * 12

    c_params = MortgageParams(
        principal=c_principal,
        annual_rate=c_rate_dec,
        months_remaining=c_months,
        fire_insurance_monthly_uf=fire_insurance_uf,
        life_insurance_rate_monthly=0.00028,
    )
    c_sched = FrenchAmortizer.generate_schedule(c_params)

    c_decision = RefinanceAnalyzer.evaluate(
        current_schedule=sched_curr,
        new_schedule=c_sched,
        upfront_costs_uf=costs.total_cost_uf,
        financed_costs=finance_costs,
        annual_discount_rate=discount_rate_dec,
    )

    # Resultados
    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric(
        label="VPN Estimado",
        value=f"{c_decision.npv_uf:+,.1f} UF",
        delta=f"${c_decision.npv_uf * uf_current:+,.0f} CLP",
    )
    sm2.metric(
        label="Ahorro Mensual",
        value=f"{c_decision.monthly_savings_uf:,.2f} UF/mes",
        delta=f"${c_decision.monthly_savings_uf * uf_current:,.0f} CLP/mes",
    )
    sm3.metric(
        label="Payback Estimado",
        value=f"{c_decision.payback_months} meses" if c_decision.payback_months else "> Plazo",
        delta="Recuperación",
    )
    sm4.metric(
        label="Dictamen Patrimonial",
        value=c_decision.recommendation_flag,
    )

    st.info(f"**Análisis:** {c_decision.rationale}")

    st.divider()

    # Matriz 2D de Sensibilidad (Heatmap)
    st.subheader("Matriz de Sensibilidad: Tasa vs Plazo (VPN en UF)")
    st.caption("Mapa de calor que evalúa el impacto patrimonial para diferentes combinaciones de tasas y plazos.")

    st.plotly_chart(
        create_sensitivity_heatmap(
            current_balance_uf=balance_uf,
            current_rate_pct=annual_rate_pct,
            current_months=months_remaining,
            upfront_costs_uf=costs.total_cost_uf,
            annual_discount_rate=discount_rate_dec,
        ),
        use_container_width=True,
    )


# ----------------------------------------------------------------------------
# PESTAÑA 4: Detector de la 'Falacia del Dividendo'
# ----------------------------------------------------------------------------
with tab_fallacy:
    st.subheader("⚠️ La Falacia del Dividendo: Por qué una cuota más baja puede arruinarte")
    st.markdown("""
    Un error recurrente en el mercado chileno es refinanciar extendiendo el plazo de la deuda para conseguir un **dividendo mensual más bajo**.
    Aunque el flujo de caja inmediato parece aliviarse, el deudor termina pagando **mucho más dinero al banco** por concepto de intereses adicionales.
    """)

    # Modelo de Oferta Trampa: Alargar plazo 10 años con 40 bps menos de tasa
    trap_term_years = min(30, round(months_remaining / 12) + 10)
    trap_months = trap_term_years * 12
    trap_rate = max(2.5, annual_rate_pct - 0.40)

    t_params = MortgageParams(
        principal=balance_uf,
        annual_rate=trap_rate / 100.0,
        months_remaining=trap_months,
        fire_insurance_monthly_uf=fire_insurance_uf,
        life_insurance_rate_monthly=0.00028,
    )
    t_sched = FrenchAmortizer.generate_schedule(t_params)

    t_decision = RefinanceAnalyzer.evaluate(
        current_schedule=sched_curr,
        new_schedule=t_sched,
        upfront_costs_uf=costs.total_cost_uf,
        financed_costs=False,
        annual_discount_rate=discount_rate_dec,
    )

    curr_total_cost = sum(row["total_dividend_uf"] for row in sched_curr)
    trap_total_cost = sum(row["total_dividend_uf"] for row in t_sched)
    extra_interest_uf = trap_total_cost - curr_total_cost

    tf1, tf2, tf3 = st.columns(3)
    tf1.metric(
        label="Dividendo Mensual 'Aparente'",
        value=f"{t_sched[0]['total_dividend_uf']:.2f} UF",
        delta=f"{t_sched[0]['total_dividend_uf'] - sched_curr[0]['total_dividend_uf']:.2f} UF (¡Ahorro aparente!)",
        delta_color="normal",
    )
    tf2.metric(
        label="Pérdida Patrimonial (VPN Destruido)",
        value=f"{t_decision.npv_uf:,.1f} UF",
        delta=f"${t_decision.npv_uf * uf_current:,.0f} CLP",
        delta_color="inverse",
    )
    tf3.metric(
        label="Sobrecosto Total de la Deuda",
        value=f"+{extra_interest_uf:,.1f} UF",
        delta=f"+${extra_interest_uf * uf_current:,.0f} CLP MÁS AL BANCO",
        delta_color="inverse",
    )

    st.error(f"🚨 **Veredicto Técnico:** {t_decision.rationale}")

    st.plotly_chart(
        create_dividend_fallacy_chart(
            current_schedule=sched_curr,
            trap_schedule=t_sched,
            current_label=f"Crédito Actual ({months_remaining/12:.0f} años, {annual_rate_pct:.2f}%)",
            trap_label=f"Oferta Trampa ({trap_term_years} años, {trap_rate:.2f}%)",
        ),
        use_container_width=True,
    )


# ----------------------------------------------------------------------------
# PESTAÑA 5: Tabla de Amortización Francesa
# ----------------------------------------------------------------------------
with tab_schedule:
    st.subheader("Tabla de Desarrollo de Amortización Francesa Mes a Mes")
    st.caption("Desglose riguroso de cada cuota: saldo inicial, dividendo financiero, amortización, interés devengado y seguros.")

    sched_view = st.radio(
        "Seleccionar Escenario para Visualizar:",
        ["Crédito Actual", "Mejor Alternativa de Mercado"],
        horizontal=True,
    )

    if sched_view == "Crédito Actual":
        chosen_sched = sched_curr
        title_tag = "actual"
    else:
        if best_opp:
            b_quote = best_opp["bank_quote"]
            b_params = MortgageParams(
                principal=balance_uf + (costs.total_cost_uf if finance_costs else 0.0) + additional_cash_uf,
                annual_rate=b_quote["annual_rate_pct"] / 100.0,
                months_remaining=b_quote["term_years"] * 12,
                fire_insurance_monthly_uf=b_quote["fire_insurance_uf"],
                life_insurance_rate_monthly=0.00028,
            )
            chosen_sched = FrenchAmortizer.generate_schedule(b_params)
            title_tag = f"mercado_{b_quote['bank_name'].lower().replace(' ', '_')}"
        else:
            chosen_sched = sched_curr
            title_tag = "actual"

    df_sched = pd.DataFrame(chosen_sched)
    df_sched.columns = [
        "Mes", "Saldo Inicial (UF)", "Dividendo Financiero (UF)", "Interés (UF)",
        "Amortización (UF)", "Desgravamen (UF)", "Incendio/Sismo (UF)",
        "Dividendo Total (UF)", "Saldo Final (UF)"
    ]

    st.dataframe(df_sched, use_container_width=True, height=400)

    # Botón de Descarga CSV
    csv_bytes = df_sched.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Tabla de Amortización en CSV",
        data=csv_bytes,
        file_name=f"amortizacion_hiporefi_{title_tag}.csv",
        mime="text/csv",
    )
