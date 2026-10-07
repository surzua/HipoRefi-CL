"""Dashboard Interactivo de Optimización de Refinanciamiento Hipotecario en Chile.

Construido con Streamlit y Plotly. Cumple con la normativa chilena:
Ley N° 21.236 (Portabilidad Financiera), D.L. 3475 (Timbres y Estampillas) y LGB Art. 100.
"""

import sys
from pathlib import Path
import io
import textwrap
import pandas as pd
import streamlit as st

# Asegurar importación de src si se ejecuta como script independiente
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.amortizer import FrenchAmortizer, GermanAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator
from src.core.metrics import RefinanceAnalyzer, HeadToHeadComparator
from src.core.advanced_financial import (
    PrepaymentSimulator,
    MixedRateRiskAnalyzer,
    LifeInsuranceActuary,
)
from src.scrapers.market_service import MarketDataService
from src.parsers.statement_extractor import StatementExtractor
from src.reports.pdf_generator import ExecutiveReportGenerator
from src.app.charts import (
    create_market_npv_chart,
    create_payback_trajectory_chart,
    create_amortization_comparison_chart,
    create_sensitivity_heatmap,
    create_dividend_fallacy_chart,
    create_prepayment_comparison_chart,
    create_mixed_rate_stress_chart,
    create_french_vs_german_chart,
    create_actuarial_insurability_gauge,
    create_head_to_head_comparison_chart,
    create_head_to_head_trajectory_chart,
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

st.html("""
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
        padding: 18px 20px;
        border-left: 5px solid #2980B9;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .badge-recommended {
        background-color: #D4EFDF;
        color: #196F3D;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-block;
    }
    .badge-caution {
        background-color: #FCF3CF;
        color: #B7950B;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-block;
    }
    .badge-not-recommended {
        background-color: #FADBD8;
        color: #943126;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-block;
    }
</style>
""")


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
if "prefer_live_scraped" not in st.session_state:
    st.session_state["prefer_live_scraped"] = False

# Sincronización con Query Params de la URL (Hito 10)
qp = st.query_params
if "sim_id" in qp:
    loaded_sim = market_service.get_saved_simulation_by_id(qp["sim_id"])
    if loaded_sim:
        st.session_state["balance_uf"] = loaded_sim["balance_uf"]
        st.session_state["annual_rate_pct"] = loaded_sim["annual_rate_pct"]
        st.session_state["months_remaining"] = loaded_sim["months_remaining"]
        st.session_state["current_dividend_uf"] = loaded_sim["current_dividend_uf"]
        st.session_state["fire_insurance_uf"] = loaded_sim["fire_insurance_uf"]
        st.session_state["detected_bank"] = loaded_sim["current_bank"]
if "balance" in qp:
    try:
        st.session_state["balance_uf"] = float(qp["balance"])
    except ValueError:
        pass
if "rate" in qp:
    try:
        st.session_state["annual_rate_pct"] = float(qp["rate"])
    except ValueError:
        pass
if "months" in qp:
    try:
        st.session_state["months_remaining"] = int(qp["months"])
    except ValueError:
        pass
if "bank" in qp:
    st.session_state["detected_bank"] = str(qp["bank"])
if "div" in qp:
    try:
        st.session_state["current_dividend_uf"] = float(qp["div"])
    except ValueError:
        pass


@st.dialog("📋 Confirmación y Validación de Cartola Bancaria")
def modal_validation_dialog(extracted_data):
    st.markdown("Revisa los parámetros detectados en el documento. Puedes modificarlos antes de aplicarlos:")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        edit_bank = st.text_input("Banco Acreedor", value=extracted_data.bank_name)
        edit_balance = st.number_input("Saldo Insoluto (UF)", value=float(extracted_data.current_balance_uf), step=50.0)
        edit_rate = st.number_input("Tasa Anual (%)", value=float(extracted_data.annual_interest_rate_pct), step=0.05, format="%.2f")
    with col_d2:
        edit_months = st.number_input("Plazo Restante (Meses)", value=int(extracted_data.remaining_installments), step=6)
        edit_div = st.number_input("Dividendo Mensual (UF)", value=float(extracted_data.current_total_dividend_uf), step=0.5)
        edit_fire = st.number_input("Seguro Incendio y Sismo (UF)", value=float(extracted_data.fire_insurance_uf or 0.70), step=0.05)

    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button("✅ Confirmar y Aplicar al Simulador", type="primary"):
            st.session_state["balance_uf"] = edit_balance
            st.session_state["annual_rate_pct"] = edit_rate
            st.session_state["months_remaining"] = edit_months
            st.session_state["current_dividend_uf"] = edit_div
            st.session_state["fire_insurance_uf"] = edit_fire
            st.session_state["detected_bank"] = edit_bank
            if extracted_data.operation_number:
                st.session_state["operation_number"] = extracted_data.operation_number
            st.session_state["pending_extraction"] = None
            st.session_state["cartola_validated"] = True
            st.rerun()
    with col_cancel:
        if st.button("❌ Descartar"):
            st.session_state["pending_extraction"] = None
            st.rerun()


# ============================================================================
# Encabezado Principal e Indicadores Macroeconómicos
# ============================================================================

st.html('<div class="main-title">🇨🇱 HipoRefi-CL: Motor de Optimización Hipotecaria</div>')
st.html('<div class="sub-title">Evaluación Cuantitativa de Refinanciamiento, Costos Normativos (Ley N° 21.236) y Benchmark de Mercado</div>')

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
        file_sig = f"{uploaded_pdf.name}_{uploaded_pdf.size}"
        if st.session_state.get("last_uploaded_pdf_sig") != file_sig:
            try:
                pdf_bytes = uploaded_pdf.read()
                extracted = extractor.extract_from_pdf(io.BytesIO(pdf_bytes))
                st.session_state["pending_extraction"] = extracted
                st.session_state["last_uploaded_pdf_sig"] = file_sig
            except Exception as e:
                st.error(f"No fue posible procesar el PDF: {e}")

    if st.session_state.get("pending_extraction"):
        modal_validation_dialog(st.session_state["pending_extraction"])

    if st.session_state.get("cartola_validated"):
        st.success(f"✓ Cartola confirmada: {st.session_state.get('detected_bank', '')}")
        if st.session_state.get("operation_number"):
            st.caption(f"Operación: {st.session_state.get('operation_number')}")

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

    st.header("🔗 Compartir Escenario")
    st.caption("Genera una URL parametrizada para compartir o recuperar tu simulación.")
    share_qs = f"?balance={balance_uf:.1f}&rate={annual_rate_pct:.2f}&months={months_remaining}&bank={st.session_state.get('detected_bank', 'Banco')}&div={current_dividend_uf:.2f}"
    if st.button("🔗 Actualizar URL en Navegador"):
        st.query_params["balance"] = str(round(balance_uf, 1))
        st.query_params["rate"] = str(round(annual_rate_pct, 2))
        st.query_params["months"] = str(int(months_remaining))
        st.query_params["bank"] = str(st.session_state.get("detected_bank", "Banco"))
        st.query_params["div"] = str(round(current_dividend_uf, 2))
        st.success("¡URL actualizada en la barra del navegador!")
    st.code(share_qs, language="text")


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
    prefer_live_scraped=st.session_state.get("prefer_live_scraped", False),
)

opportunities = market_eval.get("all_opportunities", [])
best_opp = market_eval.get("best_opportunity")


# ============================================================================
# Pestañas Principales de la Aplicación
# ============================================================================

tab_market, tab_h2h, tab_breakeven, tab_sim, tab_fallacy, tab_schedule, tab_advanced, tab_saved = st.tabs([
    "🏆 Comparador de Mercado",
    "🥊 Comparador Head-to-Head",
    "📈 Punto de Equilibrio & Payback",
    "🎛️ Simulador a Medida & Sensibilidad",
    "⚠️ Detector de la 'Falacia del Dividendo'",
    "📋 Tabla de Amortización",
    "🔬 Módulo Financiero Avanzado",
    "💾 Simulaciones Guardadas",
])


# ----------------------------------------------------------------------------
# PESTAÑA 1: Comparador de Mercado
# ----------------------------------------------------------------------------
with tab_market:
    st.subheader("Benchmark de Mercado: Bancos y Mutuarias de Chile")
    st.caption("Comparación de tu crédito actual contra las tasas comerciales vigentes y cotizadores públicos en vivo.")

    col_sync1, col_sync2 = st.columns([2, 1])
    with col_sync1:
        live_mode = st.toggle(
            "🤖 Priorizar Cotizaciones en Vivo (Playwright Headless)",
            value=st.session_state.get("prefer_live_scraped", False),
            key="toggle_prefer_live_scraped",
            help="Utiliza cotizaciones reales extraídas directamente de los simuladores web de BancoEstado, Santander y BCI guardadas en DuckDB.",
        )
        if live_mode != st.session_state.get("prefer_live_scraped", False):
            st.session_state["prefer_live_scraped"] = live_mode
            st.rerun()

    with col_sync2:
        if st.button("🔄 Sincronizar en Vivo Ahora", help="Ejecuta Playwright headless en segundo plano y actualiza DuckDB."):
            with st.spinner("Ejecutando simuladores bancarios con Playwright..."):
                target_years = max(5, round(months_remaining / 12))
                sync_res = market_service.sync_from_live_scrapers(
                    principal_uf=balance_uf,
                    term_years=target_years,
                    headless=True,
                )
                st.session_state["prefer_live_scraped"] = True
                st.success(f"¡Sincronización completada! {sync_res['records_saved']} ofertas actualizadas.")
                st.rerun()

    if best_opp:
        best_quote = best_opp["bank_quote"]
        best_decision = best_opp["evaluation"]
        is_live_source = "PLAYWRIGHT" in best_quote.get("source", "").upper()

        # Tarjeta destacada de la mejor oportunidad
        live_badge = (
            '<span style="background-color: #E8F8F5; color: #117A65; padding: 4px 10px; border-radius: 12px; font-weight: bold; margin-right: 8px;">🤖 En Vivo (Playwright)</span>'
            if is_live_source else ''
        )
        badge_class = "badge-recommended" if best_decision["recommendation_flag"] == "RECOMENDADO" else "badge-caution"

        st.html(f"""
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap;">
                <h3 style="margin: 0; color: #1B4F72; flex: 1 1 auto; min-width: 250px;">🥇 Mejor Alternativa: {best_quote['bank_name']}</h3>
                <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
                    {live_badge}
                    <span class="{badge_class}">
                        {best_decision['recommendation_flag']}
                    </span>
                </div>
            </div>
            <p style="margin-top: 10px; margin-bottom: 0; color: #2C3E50; font-size: 1rem;">{best_decision['rationale']}</p>
        </div>
        """)

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

        # Generación del Dictamen Ejecutivo en PDF para la mejor alternativa
        market_opps_report = []
        for o in opportunities:
            bq_item = o["bank_quote"]
            ev_item = o["evaluation"]
            market_opps_report.append({
                "bank_name": bq_item["bank_name"],
                "annual_rate_pct": bq_item["annual_rate_pct"],
                "monthly_dividend_uf": bq_item["monthly_total_dividend_uf"],
                "monthly_savings_clp": ev_item["monthly_savings_uf"] * uf_current,
                "npv_uf": ev_item["npv_uf"],
                "payback_months": ev_item["payback_months"],
                "recommendation_flag": ev_item["recommendation_flag"],
            })

        pdf_payload_best = {
            "client_name": st.session_state.get("client_name", "Titular del Crédito"),
            "operation_number": st.session_state.get("operation_number"),
            "current_bank": st.session_state.get("detected_bank", "Banco Acreedor Actual"),
            "uf_value": uf_current,
            "current_balance_uf": balance_uf,
            "current_rate_pct": annual_rate_pct,
            "months_remaining": months_remaining,
            "current_total_dividend_uf": current_dividend_uf,
            "current_dividend_clp": current_dividend_uf * uf_current,
            "target_bank": best_quote["bank_name"],
            "new_rate_pct": best_quote["annual_rate_pct"],
            "new_months": best_quote["term_years"] * 12,
            "new_dividend_uf": best_quote["monthly_total_dividend_uf"],
            "new_dividend_clp": best_quote["monthly_total_dividend_uf"] * uf_current,
            "recommendation_flag": best_decision["recommendation_flag"],
            "rationale": best_decision["rationale"],
            "npv_uf": best_decision["npv_uf"],
            "npv_clp": best_decision["npv_uf"] * uf_current,
            "monthly_savings_uf": best_decision["monthly_savings_uf"],
            "monthly_savings_clp": best_decision["monthly_savings_uf"] * uf_current,
            "payback_months": best_decision["payback_months"],
            "discount_rate_pct": discount_rate_pct,
            "switching_costs": costs.to_dict(),
            "market_opportunities": market_opps_report,
        }

        try:
            pdf_bytes_best = ExecutiveReportGenerator.generate_pdf(pdf_payload_best)
            st.download_button(
                label="📥 Descargar Dictamen Ejecutivo en PDF (Ley N° 21.236)",
                data=pdf_bytes_best,
                file_name=f"dictamen_portabilidad_{best_quote['bank_name'].lower().replace(' ', '_')}.pdf",
                mime="application/pdf",
                help="Genera un dictamen formal en PDF listo para imprimir o presentar ante el banco.",
            )
        except Exception as e:
            st.warning(f"No fue posible generar el informe PDF: {e}")

    st.write("")

    # Desglose de Costos de Cambio
    with st.expander("💼 Desglose Normativo de Gastos de Cambio (Ley N° 21.236 & DL 3475)", expanded=False):
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.markdown(textwrap.dedent(f"""
            - **Comisión de Prepago (LGB Art. 100):** {costs.prepayment_penalty_uf:.2f} UF (${costs.prepayment_penalty_uf * uf_current:,.0f} CLP)  
              *(Tope legal máximo de 1.5 meses de intereses devengados)*
            - **Conservador de Bienes Raíces (CBR):** {costs.cbr_uf:.2f} UF (${costs.cbr_uf * uf_current:,.0f} CLP)  
              *(Incluye beneficio legal del 50% de descuento por subrogación)*
            - **Impuesto de Timbres y Estampillas (D.L. 3475):** {costs.stamp_tax_uf:.2f} UF  
              *(100% EXENTO sobre el capital refinanciado)*
            """).strip())
        with c_col2:
            st.markdown(textwrap.dedent(f"""
            - **Tasación Comercial:** {costs.appraisal_uf:.2f} UF (${costs.appraisal_uf * uf_current:,.0f} CLP)
            - **Estudio de Títulos y Redacción:** {costs.title_deed_uf:.2f} UF (${costs.title_deed_uf * uf_current:,.0f} CLP)
            - **Gastos Notariales Regulados:** {costs.notary_uf:.2f} UF (${costs.notary_uf * uf_current:,.0f} CLP)
            - **COSTO TOTAL OPERACIONAL:** **{costs.total_cost_uf:.2f} UF** (**${costs.total_cost_uf * uf_current:,.0f} CLP**)
            """).strip())

    # Gráfico de barras de VPN por entidad
    opps_for_chart = [
        {
            "institution_name": o["bank_quote"]["bank_name"],
            "evaluation": o["evaluation"],
            "annual_rate_pct": o["bank_quote"]["annual_rate_pct"],
        }
        for o in opportunities
    ]
    st.plotly_chart(create_market_npv_chart(opps_for_chart))

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
            "CAE (%)": f"{bq.get('estimated_cae_pct', 0.0):.2f}%",
            "Dividendo (UF)": f"{bq['monthly_total_dividend_uf']:.2f} UF",
            "Dividendo (CLP)": f"${bq['monthly_total_dividend_uf'] * uf_current:,.0f}",
            "Ahorro Mensual": f"${ev['monthly_savings_uf'] * uf_current:+,.0f}",
            "VPN en UF": f"{ev['npv_uf']:+,.1f} UF",
            "Payback": f"{ev['payback_months']} meses" if ev['payback_months'] else "> Plazo",
            "Dictamen": ev["recommendation_flag"],
            "Fuente": "🤖 Playwright Live" if "PLAYWRIGHT" in bq.get("source", "").upper() else "📐 Modelo CMF",
        })

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, hide_index=True)


# ----------------------------------------------------------------------------
# PESTAÑA 2: Comparador Head-to-Head (Hito 10)
# ----------------------------------------------------------------------------
with tab_h2h:
    st.subheader("🥊 Comparador Lado a Lado Head-to-Head: Banco A vs. Banco B")
    st.caption("Enfrenta directamente dos ofertas bancarias específicas para evaluar dividendo, ahorro, VPN, costos y dictamen de dominancia patrimonial.")

    avail_bank_names = [o["bank_quote"]["bank_name"] for o in opportunities] if opportunities else [
        "Santander", "BancoEstado", "BCI", "Scotiabank", "Banco de Chile", "Mutuaria Security"
    ]

    col_h_left, col_h_right = st.columns(2)
    with col_h_left:
        st.markdown("### 🏦 Entidad A")
        bank_a_sel = st.selectbox("Seleccionar Banco A:", avail_bank_names, index=0, key="h2h_bank_a_sel")

        opp_a = next((o for o in opportunities if o["bank_quote"]["bank_name"] == bank_a_sel), None)
        def_rate_a = opp_a["bank_quote"]["annual_rate_pct"] if opp_a else 4.25
        def_term_a = opp_a["bank_quote"]["term_years"] if opp_a else max(5, round(months_remaining / 12))
        def_fire_a = opp_a["bank_quote"]["fire_insurance_uf"] if opp_a else fire_insurance_uf

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            rate_a = st.number_input("Tasa Anual Banco A (%)", min_value=1.0, max_value=15.0, value=float(def_rate_a), step=0.05, format="%.2f", key="h2h_rate_a")
        with col_a2:
            term_a_years = st.number_input("Plazo Banco A (Años)", min_value=5, max_value=40, value=int(def_term_a), step=1, key="h2h_term_a")

    with col_h_right:
        st.markdown("### 🏛️ Entidad B")
        idx_b = min(1, len(avail_bank_names) - 1)
        bank_b_sel = st.selectbox("Seleccionar Banco B:", avail_bank_names, index=idx_b, key="h2h_bank_b_sel")

        opp_b = next((o for o in opportunities if o["bank_quote"]["bank_name"] == bank_b_sel), None)
        def_rate_b = opp_b["bank_quote"]["annual_rate_pct"] if opp_b else 4.50
        def_term_b = opp_b["bank_quote"]["term_years"] if opp_b else max(5, round(months_remaining / 12))
        def_fire_b = opp_b["bank_quote"]["fire_insurance_uf"] if opp_b else fire_insurance_uf

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            rate_b = st.number_input("Tasa Anual Banco B (%)", min_value=1.0, max_value=15.0, value=float(def_rate_b), step=0.05, format="%.2f", key="h2h_rate_b")
        with col_b2:
            term_b_years = st.number_input("Plazo Banco B (Años)", min_value=5, max_value=40, value=int(def_term_b), step=1, key="h2h_term_b")

    p_principal_new = balance_uf + (costs.total_cost_uf if finance_costs else 0.0) + additional_cash_uf
    sched_a = FrenchAmortizer.generate_schedule(MortgageParams(
        principal=p_principal_new,
        annual_rate=rate_a / 100.0,
        months_remaining=int(term_a_years * 12),
        fire_insurance_monthly_uf=def_fire_a,
        life_insurance_rate_monthly=0.00028,
    ))
    sched_b = FrenchAmortizer.generate_schedule(MortgageParams(
        principal=p_principal_new,
        annual_rate=rate_b / 100.0,
        months_remaining=int(term_b_years * 12),
        fire_insurance_monthly_uf=def_fire_b,
        life_insurance_rate_monthly=0.00028,
    ))

    h2h_res = HeadToHeadComparator.compare(
        current_schedule=sched_curr,
        current_balance_uf=balance_uf,
        current_annual_rate_pct=annual_rate_pct,
        current_months=months_remaining,
        bank_a_name=bank_a_sel,
        bank_a_schedule=sched_a,
        bank_a_rate_pct=rate_a,
        bank_a_term_years=int(term_a_years),
        bank_a_upfront_costs_uf=costs.total_cost_uf,
        bank_b_name=bank_b_sel,
        bank_b_schedule=sched_b,
        bank_b_rate_pct=rate_b,
        bank_b_term_years=int(term_b_years),
        bank_b_upfront_costs_uf=costs.total_cost_uf,
        financed_costs=finance_costs,
        annual_discount_rate=discount_rate_dec,
    )

    st.write("")
    winner_color = "#2980B9" if h2h_res.winner_bank == bank_a_sel else "#27AE60" if h2h_res.winner_bank == bank_b_sel else "#7F8C8D"
    st.html(f"""
    <div style="background-color: #F8F9F9; border-radius: 10px; padding: 18px; border-left: 6px solid {winner_color}; margin-bottom: 20px;">
        <h3 style="margin: 0; color: #1B4F72;">{h2h_res.verdict_rationale}</h3>
        <p style="margin-top: 8px; margin-bottom: 0; color: #566573; font-size: 0.95rem;">
            Diferencia de VPN: <b>{h2h_res.npv_diff_uf:+.2f} UF</b> (${h2h_res.npv_diff_uf * uf_current:+,.0f} CLP) |
            Diferencia de Dividendo Mensual: <b>{h2h_res.monthly_dividend_diff_uf:+.2f} UF/mes</b> (${h2h_res.monthly_dividend_diff_uf * uf_current:+,.0f} CLP/mes) |
            Diferencia en Costo Total: <b>{h2h_res.total_cost_diff_uf:+.2f} UF</b>
        </p>
    </div>
    """)

    col_kpi_a, col_kpi_b = st.columns(2)
    with col_kpi_a:
        st.html(f"""
        <div style="background-color: #EBF5FB; border-radius: 8px; padding: 12px; border-left: 4px solid #2980B9;">
            <h4 style="margin: 0; color: #1B4F72;">📊 Resultados {bank_a_sel}</h4>
        </div>
        """)
        ma1, ma2, ma3 = st.columns(3)
        ma1.metric("Dividendo Mensual", f"{h2h_res.bank_a.monthly_dividend_uf:.2f} UF", f"${h2h_res.bank_a.monthly_dividend_uf * uf_current:,.0f} CLP")
        ma2.metric("Ahorro Mensual", f"{h2h_res.bank_a.monthly_savings_uf:+.2f} UF", f"${h2h_res.bank_a.monthly_savings_uf * uf_current:+,.0f} CLP")
        ma3.metric("Ganancia VPN", f"{h2h_res.bank_a.npv_uf:+.1f} UF", f"${h2h_res.bank_a.npv_uf * uf_current:+,.0f} CLP")
        ma4, ma5, ma6 = st.columns(3)
        ma4.metric("Payback Descontado", f"{h2h_res.bank_a.payback_months} meses" if h2h_res.bank_a.payback_months else "> Plazo")
        ma5.metric("Interés Total", f"{h2h_res.bank_a.total_interest_uf:,.1f} UF")
        ma6.metric("Dictamen", h2h_res.bank_a.recommendation_flag)

    with col_kpi_b:
        st.html(f"""
        <div style="background-color: #EAFAF1; border-radius: 8px; padding: 12px; border-left: 4px solid #27AE60;">
            <h4 style="margin: 0; color: #196F3D;">📊 Resultados {bank_b_sel}</h4>
        </div>
        """)
        mb1, mb2, mb3 = st.columns(3)
        mb1.metric("Dividendo Mensual", f"{h2h_res.bank_b.monthly_dividend_uf:.2f} UF", f"${h2h_res.bank_b.monthly_dividend_uf * uf_current:,.0f} CLP")
        mb2.metric("Ahorro Mensual", f"{h2h_res.bank_b.monthly_savings_uf:+.2f} UF", f"${h2h_res.bank_b.monthly_savings_uf * uf_current:+,.0f} CLP")
        mb3.metric("Ganancia VPN", f"{h2h_res.bank_b.npv_uf:+.1f} UF", f"${h2h_res.bank_b.npv_uf * uf_current:+,.0f} CLP")
        mb4, mb5, mb6 = st.columns(3)
        mb4.metric("Payback Descontado", f"{h2h_res.bank_b.payback_months} meses" if h2h_res.bank_b.payback_months else "> Plazo")
        mb5.metric("Interés Total", f"{h2h_res.bank_b.total_interest_uf:,.1f} UF")
        mb6.metric("Dictamen", h2h_res.bank_b.recommendation_flag)

    st.write("")
    curr_metrics_dict = {
        "monthly_dividend_uf": current_dividend_uf,
        "annual_rate_pct": annual_rate_pct,
    }
    st.plotly_chart(
        create_head_to_head_comparison_chart(
            bank_a_name=bank_a_sel,
            a_metrics=h2h_res.bank_a.to_dict(),
            bank_b_name=bank_b_sel,
            b_metrics=h2h_res.bank_b.to_dict(),
            current_metrics=curr_metrics_dict,
        )
    )

    st.plotly_chart(
        create_head_to_head_trajectory_chart(
            current_label=f"Crédito Actual ({annual_rate_pct:.2f}%)",
            sched_curr=sched_curr,
            bank_a_name=f"{bank_a_sel} ({rate_a:.2f}%)",
            sched_a=sched_a,
            bank_b_name=f"{bank_b_sel} ({rate_b:.2f}%)",
            sched_b=sched_b,
        )
    )

    with st.expander("📋 Tabla Comparativa Cuota a Cuota (Primeros 12 Meses)", expanded=False):
        comp_rows = []
        for i in range(min(12, len(sched_curr), len(sched_a), len(sched_b))):
            r_c = sched_curr[i]
            r_a = sched_a[i]
            r_b = sched_b[i]
            comp_rows.append({
                "Mes": r_c["month"],
                "Dividendo Actual (UF)": f"{r_c['total_dividend_uf']:.2f}",
                f"Dividendo {bank_a_sel} (UF)": f"{r_a['total_dividend_uf']:.2f}",
                f"Dividendo {bank_b_sel} (UF)": f"{r_b['total_dividend_uf']:.2f}",
                f"Ahorro {bank_a_sel} (CLP)": f"${(r_c['total_dividend_uf'] - r_a['total_dividend_uf']) * uf_current:+,.0f}",
                f"Ahorro {bank_b_sel} (CLP)": f"${(r_c['total_dividend_uf'] - r_b['total_dividend_uf']) * uf_current:+,.0f}",
                "Ventaja A vs B (UF)": f"{r_b['total_dividend_uf'] - r_a['total_dividend_uf']:+.2f}",
            })
        st.dataframe(pd.DataFrame(comp_rows))


# ----------------------------------------------------------------------------
# PESTAÑA 3: Punto de Equilibrio y Trayectoria
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
            )
        )

        st.plotly_chart(
            create_amortization_comparison_chart(
                current_schedule=sched_curr,
                new_schedule=sched_new,
                current_label=f"Crédito Actual ({annual_rate_pct:.2f}%)",
                new_label=f"{selected_bank_name} ({s_quote['annual_rate_pct']:.2f}%)",
            )
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

    # Generación de PDF para la simulación a medida
    pdf_payload_custom = {
        "client_name": st.session_state.get("client_name", "Titular del Crédito"),
        "operation_number": st.session_state.get("operation_number"),
        "current_bank": st.session_state.get("detected_bank", "Banco Acreedor Actual"),
        "uf_value": uf_current,
        "current_balance_uf": balance_uf,
        "current_rate_pct": annual_rate_pct,
        "months_remaining": months_remaining,
        "current_total_dividend_uf": current_dividend_uf,
        "current_dividend_clp": current_dividend_uf * uf_current,
        "target_bank": custom_bank,
        "new_rate_pct": custom_rate,
        "new_months": c_months,
        "new_dividend_uf": c_sched[0]["total_dividend_uf"] if c_sched else 0.0,
        "new_dividend_clp": (c_sched[0]["total_dividend_uf"] if c_sched else 0.0) * uf_current,
        "recommendation_flag": c_decision.recommendation_flag,
        "rationale": c_decision.rationale,
        "npv_uf": c_decision.npv_uf,
        "npv_clp": c_decision.npv_uf * uf_current,
        "monthly_savings_uf": c_decision.monthly_savings_uf,
        "monthly_savings_clp": c_decision.monthly_savings_uf * uf_current,
        "payback_months": c_decision.payback_months,
        "discount_rate_pct": discount_rate_pct,
        "switching_costs": costs.to_dict(),
        "market_opportunities": [
            {
                "bank_name": custom_bank,
                "annual_rate_pct": custom_rate,
                "monthly_dividend_uf": c_sched[0]["total_dividend_uf"] if c_sched else 0.0,
                "monthly_savings_clp": c_decision.monthly_savings_uf * uf_current,
                "npv_uf": c_decision.npv_uf,
                "payback_months": c_decision.payback_months,
                "recommendation_flag": c_decision.recommendation_flag,
            }
        ],
    }
    try:
        pdf_bytes_custom = ExecutiveReportGenerator.generate_pdf(pdf_payload_custom)
        st.download_button(
            label=f"📥 Descargar Dictamen en PDF de esta Contraoferta ({custom_bank})",
            data=pdf_bytes_custom,
            file_name=f"dictamen_contraoferta_{custom_bank.lower().replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.warning(f"No fue posible generar el informe PDF personalizado: {e}")

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
        )
    )


# ----------------------------------------------------------------------------
# PESTAÑA 4: Detector de la 'Falacia del Dividendo'
# ----------------------------------------------------------------------------
with tab_fallacy:
    st.subheader("⚠️ La Falacia del Dividendo: Por qué una cuota más baja puede arruinarte")
    st.markdown(textwrap.dedent("""
    Un error recurrente en el mercado chileno es refinanciar extendiendo el plazo de la deuda para conseguir un **dividendo mensual más bajo**.
    Aunque el flujo de caja inmediato parece aliviarse, el deudor termina pagando **mucho más dinero al banco** por concepto de intereses adicionales.
    """).strip())

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
        )
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

    st.dataframe(df_sched, height=400)

    # Botón de Descarga CSV
    csv_bytes = df_sched.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Tabla de Amortización en CSV",
        data=csv_bytes,
        file_name=f"amortizacion_hiporefi_{title_tag}.csv",
        mime="text/csv",
    )


# ----------------------------------------------------------------------------
# PESTAÑA 6: Módulo Financiero y Normativo Avanzado (Hito 8)
# ----------------------------------------------------------------------------
with tab_advanced:
    st.subheader("🔬 Módulo Financiero y Normativo Avanzado")
    st.caption("Herramientas cuantitativas especializadas: Prepagos Parciales (LGB Art. 100), Estrés de Tasa Mixta, Curva Actuarial de Seguros y Amortización Alemana.")

    sub_tab_prepay, sub_tab_mixed, sub_tab_actuary, sub_tab_german = st.tabs([
        "💰 Abonos Extraordinarios (Prepagos)",
        "⚖️ Tasa Mixta vs. Fija (Estrés)",
        "🛡️ Desgravamen Actuarial & Edad",
        "🇩🇪 Amortización Alemana vs. Francesa",
    ])

    # ------------------------------------------------------------------------
    # SUB-PESTAÑA 1: Prepagos y Abonos Extraordinarios
    # ------------------------------------------------------------------------
    with sub_tab_prepay:
        st.markdown("### 💰 Simulador de Abonos Extraordinarios y Prepagos Parciales")
        st.markdown(
            "Permite evaluar el impacto de inyectar liquidez al crédito hipotecario, "
            "comparando las dos modalidades de la banca chilena bajo el marco regulatorio del **Art. 100 de la Ley General de Bancos**."
        )

        col_pre1, col_pre2, col_pre3 = st.columns(3)
        with col_pre1:
            prepay_input_uf = st.number_input(
                "Monto del Abono Extraordinario (UF)",
                min_value=10.0,
                max_value=float(balance_uf),
                value=min(300.0, float(balance_uf * 0.1)),
                step=25.0,
                help="Monto de capital a amortizar anticipadamente.",
            )
            st.caption(f"Equivalente a **${prepay_input_uf * uf_current:,.0f} CLP** ({prepay_input_uf / balance_uf * 100.1:.1f}% del saldo).")

        with col_pre2:
            penalty_months_input = st.number_input(
                "Comisión de Prepago (Meses de interés devengado)",
                min_value=0.0,
                max_value=3.0,
                value=1.5,
                step=0.25,
                help="LGB Art. 100 fija un tope máximo de 1.5 meses de intereses para créditos de vivienda de hasta 5.000 UF.",
            )

        with col_pre3:
            prepay_eval = PrepaymentSimulator.simulate(
                balance_uf=balance_uf,
                annual_rate=current_rate_dec,
                months_remaining=months_remaining,
                prepayment_amount_uf=prepay_input_uf,
                fire_insurance_monthly_uf=fire_insurance_uf,
                life_insurance_rate_monthly=0.00028,
                annual_discount_rate=discount_rate_dec,
                penalty_months=penalty_months_input,
            )
            st.metric(
                label="Comisión Legal de Prepago (LGB Art. 100)",
                value=f"{prepay_eval.prepayment_penalty_uf:.2f} UF",
                delta=f"${prepay_eval.prepayment_penalty_uf * uf_current:,.0f} CLP",
                delta_color="inverse",
            )

        st.info(f"💡 Desembolso total en t=0 (Capital + Comisión): **{prepay_eval.total_cash_outlay_uf:.2f} UF** (${prepay_eval.total_cash_outlay_uf * uf_current:,.0f} CLP). Saldo restante: **{prepay_eval.new_balance_uf:.2f} UF**.")

        # Comparativa lado a lado: Reducir Plazo vs Reducir Dividendo
        opt_t = prepay_eval.reduce_term_option
        opt_d = prepay_eval.reduce_dividend_option

        col_opt_a, col_opt_b = st.columns(2)
        with col_opt_a:
            st.html("""
            <div style="background-color: #EBF5FB; border-radius: 8px; padding: 16px; border-left: 5px solid #2980B9;">
                <h4 style="margin: 0; color: #1B4F72;">Opción A: Reducir Plazo</h4>
                <p style="color: #566573; font-size: 0.9rem; margin-top: 4px; margin-bottom: 0;">Mantiene el dividendo mensual y acorta el vencimiento del crédito.</p>
            </div>
            """)
            m_a1, m_a2 = st.columns(2)
            m_a1.metric("Nuevo Plazo", f"{opt_t.new_months} meses", f"-{opt_t.months_saved} meses ({opt_t.months_saved/12:.1f} años)")
            m_a2.metric("Ahorro Intereses", f"{opt_t.interest_savings_uf:,.1f} UF", f"${opt_t.interest_savings_uf * uf_current:,.0f} CLP")
            m_a3, m_a4 = st.columns(2)
            m_a3.metric("Nuevo Dividendo", f"{opt_t.new_monthly_dividend_uf:.2f} UF")
            m_a4.metric("Ganancia Patrimonial (VPN)", f"{opt_t.npv_uf:+,.1f} UF", f"${opt_t.npv_uf * uf_current:+,.0f} CLP")

        with col_opt_b:
            st.html("""
            <div style="background-color: #EAFAF1; border-radius: 8px; padding: 16px; border-left: 5px solid #27AE60;">
                <h4 style="margin: 0; color: #196F3D;">Opción B: Reducir Dividendo</h4>
                <p style="color: #566573; font-size: 0.9rem; margin-top: 4px; margin-bottom: 0;">Mantiene el plazo restante original y reduce la cuota mensual.</p>
            </div>
            """)
            m_b1, m_b2 = st.columns(2)
            m_b1.metric("Alivio Mensual", f"-{opt_d.monthly_dividend_saving_uf:.2f} UF/mes", f"-${opt_d.monthly_dividend_saving_uf * uf_current:,.0f} CLP/mes")
            m_b2.metric("Ahorro Intereses", f"{opt_d.interest_savings_uf:,.1f} UF", f"${opt_d.interest_savings_uf * uf_current:,.0f} CLP")
            m_b3, m_b4 = st.columns(2)
            m_b3.metric("Nuevo Dividendo", f"{opt_d.new_monthly_dividend_uf:.2f} UF")
            m_b4.metric("Ganancia Patrimonial (VPN)", f"{opt_d.npv_uf:+,.1f} UF", f"${opt_d.npv_uf * uf_current:+,.0f} CLP")

        # Recomendación técnica
        st.success(f"🎯 **Dictamen Cuantitativo**: {prepay_eval.rationale}")

        # Gráfico comparativo de flujos
        p_term_params = MortgageParams(
            principal=prepay_eval.new_balance_uf,
            annual_rate=current_rate_dec,
            months_remaining=opt_t.new_months,
            fire_insurance_monthly_uf=fire_insurance_uf,
            life_insurance_rate_monthly=0.00028,
        )
        sched_p_term = FrenchAmortizer.generate_schedule(p_term_params) if opt_t.new_months > 0 else []

        p_div_params = MortgageParams(
            principal=prepay_eval.new_balance_uf,
            annual_rate=current_rate_dec,
            months_remaining=months_remaining,
            fire_insurance_monthly_uf=fire_insurance_uf,
            life_insurance_rate_monthly=0.00028,
        )
        sched_p_div = FrenchAmortizer.generate_schedule(p_div_params)

        fig_prepay = create_prepayment_comparison_chart(sched_curr, sched_p_term, sched_p_div)
        st.plotly_chart(fig_prepay)

    # ------------------------------------------------------------------------
    # SUB-PESTAÑA 2: Modelado de Riesgo de Tasa Mixta vs. Fija
    # ------------------------------------------------------------------------
    with sub_tab_mixed:
        st.markdown("### ⚖️ Modelado de Riesgo: Tasa Mixta vs. Tasa Fija")
        st.markdown(
            "Las ofertas con tasa fija a 3 o 5 años ofrecen dividendos iniciales atractivos, pero transfieren "
            "el riesgo de variaciones en la Tasa de Política Monetaria (TPM) o costo de fondeo a partir del mes 37 o 61. "
            "Esta herramienta proyecta escenarios de estrés y calcula la **Tasa de Quiebre (*Breakeven Rate*)**."
        )

        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        with c_m1:
            initial_mixed_rate_pct = st.number_input(
                "Tasa Fija Inicial (%)",
                min_value=1.0,
                max_value=15.0,
                value=3.90,
                step=0.10,
                help="Tasa promocional o fija durante los primeros K meses.",
            )
        with c_m2:
            fixed_period_months = st.selectbox(
                "Período Inicial Fijo",
                [36, 60],
                index=0,
                format_func=lambda x: f"{x} meses ({x//12} años)",
                help="Duración del tramo a tasa fija (típicamente 3 o 5 años en la banca chilena).",
            )
        with c_m3:
            baseline_subsequent_pct = st.number_input(
                "Tasa Variable Esperada Post-Fijo (%)",
                min_value=1.0,
                max_value=15.0,
                value=4.80,
                step=0.10,
                help="Tasa esperada de mercado (spread + índice base) para el resto del crédito.",
            )
        with c_m4:
            pure_fixed_rate_pct = st.number_input(
                "Tasa de Crédito 100% Fijo Puro (%)",
                min_value=1.0,
                max_value=15.0,
                value=4.60,
                step=0.10,
                help="Alternativa de crédito a tasa fija durante todo el plazo.",
            )

        mixed_eval = MixedRateRiskAnalyzer.evaluate(
            principal_uf=balance_uf,
            total_months=months_remaining,
            fixed_period_months=fixed_period_months,
            initial_fixed_rate_pct=initial_mixed_rate_pct,
            baseline_subsequent_rate_pct=baseline_subsequent_pct,
            pure_fixed_rate_pct=pure_fixed_rate_pct,
            fire_insurance_monthly_uf=fire_insurance_uf,
            life_insurance_rate_monthly=0.00028,
            annual_discount_rate_pct=discount_rate_pct,
        )

        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        col_kpi1.metric(
            label="Tasa Variable de Quiebre (Breakeven)",
            value=f"{mixed_eval.breakeven_variable_rate_pct:.2f}%",
            delta=f"{mixed_eval.breakeven_variable_rate_pct - baseline_subsequent_pct:+.2f}% vs Base",
            help="Umbral de tasa variable por sobre el cual el crédito mixto destruye el ahorro inicial frente al crédito 100% fijo.",
        )
        col_kpi2.metric(
            label="Dividendo Fijo Puro",
            value=f"{mixed_eval.pure_fixed_dividend_uf:.2f} UF/mes",
            delta=f"${mixed_eval.pure_fixed_dividend_uf * uf_current:,.0f} CLP",
        )
        init_diff = mixed_eval.scenarios[1].initial_dividend_uf - mixed_eval.pure_fixed_dividend_uf
        col_kpi3.metric(
            label=f"Dividendo Inicial Tramo Fijo (Meses 1-{fixed_period_months})",
            value=f"{mixed_eval.scenarios[1].initial_dividend_uf:.2f} UF/mes",
            delta=f"{init_diff:+.2f} UF/mes",
            delta_color="inverse",
        )

        st.info(f"📋 **Análisis Patrimonial**: {mixed_eval.recommendation_summary}")

        # Tabla de escenarios de estrés
        sc_data = []
        for s in mixed_eval.scenarios:
            sc_data.append({
                "Escenario": s.scenario_name,
                "Tasa Variable Post-Fijo": f"{s.variable_annual_rate_pct:.2f}%",
                "Dividendo Inicial (1-K)": f"{s.initial_dividend_uf:.2f} UF",
                "Dividendo Post-Reinicio": f"{s.subsequent_dividend_uf:.2f} UF",
                "Salto de Dividendo": f"{s.dividend_jump_uf:+.2f} UF ({s.dividend_jump_pct:+.1f}%)",
                "Costo Total Crédito": f"{s.total_cost_uf:,.1f} UF",
                "VPN vs. Fijo Puro (UF)": f"{s.npv_vs_fixed_uf:+.2f} UF",
                "VPN vs. Fijo Puro (CLP)": f"${s.npv_vs_fixed_uf * uf_current:+,.0f} CLP",
            })
        st.dataframe(pd.DataFrame(sc_data), height=180)

        # Gráfico interactivo de trayectorias
        fig_mixed = create_mixed_rate_stress_chart(
            pure_fixed_dividend=mixed_eval.pure_fixed_dividend_uf,
            scenarios=mixed_eval.scenarios,
            fixed_period_months=fixed_period_months,
            total_months=months_remaining,
        )
        st.plotly_chart(fig_mixed)

    # ------------------------------------------------------------------------
    # SUB-PESTAÑA 3: Desgravamen Actuarial & Edad
    # ------------------------------------------------------------------------
    with sub_tab_actuary:
        st.markdown("### 🛡️ Curva Actuarial de Desgravamen y Reglas de Asegurabilidad por Edad")
        st.markdown(
            "En Chile, el seguro de desgravamen hipotecario está regulado por la CMF y licitado colectivamente. "
            "Las primas mensuales escalan fuertemente con la edad del titular y existen topes máximos de permanencia (75 a 80 años)."
        )

        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            debtor_age = st.slider("Edad Actual del Deudor (Años)", min_value=18, max_value=85, value=42, step=1)
            loan_years = st.slider("Plazo Solicitado (Años)", min_value=5, max_value=35, value=min(25, max(5, int(months_remaining / 12))), step=1)

            ins_eval = LifeInsuranceActuary.evaluate_insurability(debtor_age, loan_years)

            if ins_eval.status == "ESTÁNDAR":
                st.success(f"✅ **Estado de Asegurabilidad**: {ins_eval.status} (Riesgo {ins_eval.risk_level})\n\n{ins_eval.regulatory_alert}")
            elif ins_eval.status == "OBSERVACIÓN":
                st.warning(f"⚠️ **Estado de Asegurabilidad**: {ins_eval.status} (Riesgo {ins_eval.risk_level})\n\n{ins_eval.regulatory_alert}")
            elif ins_eval.status == "RESTRICCIÓN_MÉDICA":
                st.error(f"🚨 **Estado de Asegurabilidad**: {ins_eval.status} (Riesgo {ins_eval.risk_level})\n\n{ins_eval.regulatory_alert}")
            else:
                st.error(f"⛔ **Estado de Asegurabilidad**: {ins_eval.status} (Riesgo {ins_eval.risk_level})\n\n{ins_eval.regulatory_alert}")

            st.markdown("#### Requisitos Médicos y de Suscripción Esperados:")
            for req in ins_eval.medical_requirements:
                st.markdown(f"- {req}")

        with col_act2:
            fig_gauge = create_actuarial_insurability_gauge(ins_eval.maturity_age, ins_eval.status)
            st.plotly_chart(fig_gauge)

            st.markdown("#### Escala de Primas de Mercado por Tramo Etario:")
            st.dataframe(pd.DataFrame(ins_eval.age_bracket_table), height=200)

        # Análisis Dinámico vs Tasa Plana
        st.markdown("---")
        st.markdown("#### Comparación de Costo de Desgravamen: Tasa Plana vs. Escalamiento Dinámico por Edad")
        sched_dyn, dyn_metrics = LifeInsuranceActuary.generate_dynamic_schedule(
            principal=balance_uf,
            annual_rate=current_rate_dec,
            months=loan_years * 12,
            start_age=debtor_age,
            fire_insurance_monthly_uf=fire_insurance_uf,
        )
        col_dyn1, col_dyn2, col_dyn3 = st.columns(3)
        col_dyn1.metric("Desgravamen Tasa Plana (0.028% mensual)", f"{dyn_metrics['flat_total_life_insurance_uf']:,.2f} UF", f"${dyn_metrics['flat_total_life_insurance_uf'] * uf_current:,.0f} CLP")
        col_dyn2.metric("Desgravamen Dinámico (Escala Actuarial)", f"{dyn_metrics['dynamic_total_life_insurance_uf']:,.2f} UF", f"${dyn_metrics['dynamic_total_life_insurance_uf'] * uf_current:,.0f} CLP")
        col_dyn3.metric("Sobrecosto Actuarial Acumulado", f"{dyn_metrics['insurance_cost_difference_uf']:+,.2f} UF", f"${dyn_metrics['insurance_cost_difference_uf'] * uf_current:+,.0f} CLP", delta_color="inverse")

    # ------------------------------------------------------------------------
    # SUB-PESTAÑA 4: Amortización Alemana vs. Francesa
    # ------------------------------------------------------------------------
    with sub_tab_german:
        st.markdown("### 🇩🇪 Sistema de Amortización Alemán (Cuota Decreciente)")
        st.markdown(
            "A diferencia del sistema francés (cuota constante), el **sistema alemán** amortiza una cantidad fija de capital cada mes. "
            "El dividendo inicial es más alto (exigiendo mayor renta demostrable), pero decrece mes a mes y genera un **ahorro significativo de intereses totales**."
        )

        german_comp = GermanAmortizer.compare_french_vs_german(params_curr)

        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        col_g1.metric(
            "Dividendo Inicial Alemán",
            f"{german_comp['german_initial_total_dividend_uf']:.2f} UF/mes",
            f"+{german_comp['initial_dividend_diff_uf']:.2f} UF (+${german_comp['initial_dividend_diff_uf'] * uf_current:,.0f} CLP)",
            delta_color="inverse",
            help="El primer dividendo es más alto debido a la amortización constante de capital.",
        )
        col_g2.metric(
            "Dividendo Final Alemán",
            f"{german_comp['german_final_total_dividend_uf']:.2f} UF/mes",
            f"{german_comp['german_final_total_dividend_uf'] - german_comp['french_initial_total_dividend_uf']:.2f} UF vs Francés",
            help="El dividendo del último mes es el más bajo del crédito.",
        )
        col_g3.metric(
            "Ahorro Total de Intereses",
            f"{german_comp['interest_savings_uf']:,.1f} UF",
            f"${german_comp['interest_savings_uf'] * uf_current:,.0f} CLP ({german_comp['interest_savings_pct']:.1f}%)",
            delta_color="normal",
            help="Intereses ahorrados durante todo el crédito eligiendo el sistema alemán.",
        )
        col_g4.metric(
            "Dividendo Francés (Constante)",
            f"{german_comp['french_initial_total_dividend_uf']:.2f} UF/mes",
            f"${german_comp['french_initial_total_dividend_uf'] * uf_current:,.0f} CLP",
        )

        # Gráfico comparativo Francés vs Alemán
        sched_german = GermanAmortizer.generate_schedule(params_curr)
        fig_fg = create_french_vs_german_chart(sched_curr, sched_german)
        st.plotly_chart(fig_fg)

        # Tabla comparativa de los primeros 12 meses
        st.markdown("#### Detalle Comparativo Primeros 12 Meses:")
        comp_rows = []
        for i in range(min(12, len(sched_curr))):
            f_r = sched_curr[i]
            g_r = sched_german[i]
            comp_rows.append({
                "Mes": f_r["month"],
                "Dividendo Francés (UF)": f"{f_r['total_dividend_uf']:.2f}",
                "Amort. Francés (UF)": f"{f_r['amortization_uf']:.2f}",
                "Interés Francés (UF)": f"{f_r['interest_uf']:.2f}",
                "Dividendo Alemán (UF)": f"{g_r['total_dividend_uf']:.2f}",
                "Amort. Alemán (UF)": f"{g_r['amortization_uf']:.2f}",
                "Interés Alemán (UF)": f"{g_r['interest_uf']:.2f}",
                "Diferencia Dividendo (UF)": f"{g_r['total_dividend_uf'] - f_r['total_dividend_uf']:+.2f}",
            })
        st.dataframe(pd.DataFrame(comp_rows), height=250)


# ----------------------------------------------------------------------------
# PESTAÑA 8: Persistencia de Simulaciones (Hito 10)
# ----------------------------------------------------------------------------
with tab_saved:
    st.subheader("💾 Historial de Simulaciones Guardadas en DuckDB")
    st.caption("Guarda escenarios de evaluación para auditoría técnica, negociación bancaria o seguimiento a lo largo del tiempo.")

    with st.form("form_save_current_sim"):
        st.markdown("#### Guardar Escenario Actual:")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            save_title = st.text_input("Título del Escenario", value=f"Evaluación {st.session_state.get('detected_bank', 'Actual')} vs Mercado")
            save_client = st.text_input("Titular del Crédito", value=st.session_state.get("client_name", "Titular del Crédito"))
        with col_s2:
            target_b_name = best_opp["bank_quote"]["bank_name"] if best_opp else "Banco Destino"
            target_b_rate = best_opp["bank_quote"]["annual_rate_pct"] if best_opp else 4.25
            target_b_term = best_opp["bank_quote"]["term_years"] if best_opp else round(months_remaining / 12)
            st.write(f"Mejor alternativa detectada: **{target_b_name} ({target_b_rate:.2f}%)**")
            save_submit = st.form_submit_button("💾 Guardar esta Simulación en DuckDB", type="primary")

        if save_submit:
            sim_record = {
                "title": save_title,
                "client_name": save_client,
                "current_bank": st.session_state.get("detected_bank", "Banco Actual"),
                "balance_uf": balance_uf,
                "annual_rate_pct": annual_rate_pct,
                "months_remaining": months_remaining,
                "current_dividend_uf": current_dividend_uf,
                "fire_insurance_uf": fire_insurance_uf,
                "target_bank": target_b_name,
                "target_rate_pct": target_b_rate,
                "target_term_years": target_b_term,
                "npv_uf": best_decision["npv_uf"] if best_opp else 0.0,
                "monthly_savings_uf": best_decision["monthly_savings_uf"] if best_opp else 0.0,
                "payback_months": best_decision["payback_months"] if best_opp else None,
                "recommendation_flag": best_decision["recommendation_flag"] if best_opp else "RECOMENDADO",
                "metadata_json": {
                    "operation_number": st.session_state.get("operation_number"),
                    "uf_value": uf_current,
                    "switching_costs_uf": costs.total_cost_uf,
                },
            }
            saved_id = market_service.save_simulation(sim_record)
            st.success(f"✓ Simulación guardada con éxito (ID: `{saved_id}`).")
            st.rerun()

    st.divider()

    saved_list = market_service.get_saved_simulations(limit=20)
    if not saved_list:
        st.info("Aún no tienes simulaciones guardadas en la base de datos DuckDB.")
    else:
        st.markdown(f"#### Simulaciones Registradas ({len(saved_list)}):")
        for sim_item in saved_list:
            with st.container():
                col_info, col_actions = st.columns([3, 1])
                with col_info:
                    st.markdown(textwrap.dedent(f"""
                    **{sim_item['title']}** — *{sim_item['client_name']}* (`{sim_item['created_at'][:19]}`)  
                    🏛️ **Actual:** {sim_item['current_bank']} ({sim_item['annual_rate_pct']:.2f}%, {sim_item['balance_uf']:,.1f} UF)  
                    🎯 **Destino:** {sim_item['target_bank']} ({sim_item['target_rate_pct']:.2f}%, {sim_item['target_term_years']} años)  
                    💰 **VPN:** {sim_item['npv_uf']:+,.1f} UF | **Ahorro:** {sim_item['monthly_savings_uf']:+,.2f} UF/mes | **Payback:** {sim_item['payback_months'] or '> Plazo'} meses
                    """).strip())
                with col_actions:
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if st.button("📂 Cargar", key=f"load_{sim_item['id']}"):
                            st.session_state["balance_uf"] = sim_item["balance_uf"]
                            st.session_state["annual_rate_pct"] = sim_item["annual_rate_pct"]
                            st.session_state["months_remaining"] = sim_item["months_remaining"]
                            st.session_state["current_dividend_uf"] = sim_item["current_dividend_uf"]
                            st.session_state["fire_insurance_uf"] = sim_item["fire_insurance_uf"]
                            st.session_state["detected_bank"] = sim_item["current_bank"]
                            st.query_params["sim_id"] = sim_item["id"]
                            st.success("¡Parámetros cargados!")
                            st.rerun()
                    with col_act2:
                        if st.button("🗑️", key=f"del_{sim_item['id']}", help="Eliminar simulación"):
                            market_service.delete_saved_simulation(sim_item["id"])
                            st.rerun()
                st.divider()

