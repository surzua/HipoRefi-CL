"""Pruebas unitarias para los generadores de visualizaciones y componentes del Dashboard."""

import pytest
import plotly.graph_objects as go

from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.app.charts import (
    create_market_npv_chart,
    create_payback_trajectory_chart,
    create_amortization_comparison_chart,
    create_sensitivity_heatmap,
    create_dividend_fallacy_chart,
)


@pytest.fixture
def sample_schedules():
    """Genera dos tablas de amortización de prueba (actual y nueva)."""
    p_curr = MortgageParams(
        principal=3000.0,
        annual_rate=0.052,
        months_remaining=180,
        fire_insurance_monthly_uf=0.7,
    )
    s_curr = FrenchAmortizer.generate_schedule(p_curr)

    p_new = MortgageParams(
        principal=3000.0,
        annual_rate=0.041,
        months_remaining=180,
        fire_insurance_monthly_uf=0.6,
    )
    s_new = FrenchAmortizer.generate_schedule(p_new)

    return s_curr, s_new


def test_create_market_npv_chart():
    """Verifica que el gráfico de barras de VPN de mercado se genere correctamente."""
    opportunities = [
        {
            "institution_name": "Banco de Chile",
            "annual_rate_pct": 4.10,
            "evaluation": {"npv_uf": 45.2, "recommendation_flag": "RECOMENDADO"},
        },
        {
            "institution_name": "Banco Santander",
            "annual_rate_pct": 4.30,
            "evaluation": {"npv_uf": 25.8, "recommendation_flag": "RECOMENDADO"},
        },
        {
            "institution_name": "Banco Caro",
            "annual_rate_pct": 5.80,
            "evaluation": {"npv_uf": -15.4, "recommendation_flag": "NO_CONVIENE"},
        },
    ]

    fig = create_market_npv_chart(opportunities)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"
    assert len(fig.data[0].x) == 3
    assert fig.data[0].y[0] == 45.2


def test_create_payback_trajectory_chart(sample_schedules):
    """Verifica la generación de la curva de flujo acumulado descontado y punto de equilibrio."""
    s_curr, s_new = sample_schedules
    fig = create_payback_trajectory_chart(
        current_schedule=s_curr,
        new_schedule=s_new,
        upfront_costs_uf=55.0,
        payback_months=24,
        annual_discount_rate=0.025,
        institution_name="Banco de Chile",
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "scatter"
    # El flujo inicial parte descontando los gastos de cambio (-55 UF)
    assert fig.data[0].y[0] < 0


def test_create_amortization_comparison_chart(sample_schedules):
    """Verifica la comparativa de saldo insoluto mes a mes."""
    s_curr, s_new = sample_schedules
    fig = create_amortization_comparison_chart(
        current_schedule=s_curr,
        new_schedule=s_new,
        current_label="Actual",
        new_label="Nuevo",
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert fig.data[0].name == "Actual"
    assert fig.data[1].name == "Nuevo"
    # Ambos terminan en 0 saldo al final del plazo
    assert fig.data[0].y[-1] == 0.0
    assert fig.data[1].y[-1] == 0.0


def test_create_sensitivity_heatmap():
    """Verifica la matriz de calor 2D para diferentes tasas y plazos."""
    fig = create_sensitivity_heatmap(
        current_balance_uf=3000.0,
        current_rate_pct=5.20,
        current_months=180,
        upfront_costs_uf=50.0,
        annual_discount_rate=0.025,
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "heatmap"
    # 7 tasas x 5 plazos
    assert len(fig.data[0].z) == 7
    assert len(fig.data[0].z[0]) == 5


def test_create_dividend_fallacy_chart(sample_schedules):
    """Verifica el gráfico apilado de la falacia del dividendo."""
    s_curr, _ = sample_schedules

    # Escenario trampa: 25 años (300 meses) a menor tasa
    p_trap = MortgageParams(
        principal=3000.0,
        annual_rate=0.048,
        months_remaining=300,
    )
    s_trap = FrenchAmortizer.generate_schedule(p_trap)

    fig = create_dividend_fallacy_chart(
        current_schedule=s_curr,
        trap_schedule=s_trap,
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    # El interés en la oferta trampa debe ser significativamente mayor
    interest_curr = fig.data[1].y[0]
    interest_trap = fig.data[1].y[1]
    assert interest_trap > interest_curr
