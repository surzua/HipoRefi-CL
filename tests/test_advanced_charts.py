"""Pruebas unitarias para las nuevas visualizaciones Plotly del Hito 8."""

import plotly.graph_objects as go
from src.core.amortizer import FrenchAmortizer, GermanAmortizer, MortgageParams
from src.core.advanced_financial import MixedRateRiskAnalyzer
from src.app.charts import (
    create_prepayment_comparison_chart,
    create_mixed_rate_stress_chart,
    create_french_vs_german_chart,
    create_actuarial_insurability_gauge,
)


def test_chart_prepayment_comparison():
    """Valida la generación del gráfico comparativo de prepago."""
    params = MortgageParams(principal=2000.0, annual_rate=0.045, months_remaining=120)
    sched_base = FrenchAmortizer.generate_schedule(params)

    params_term = MortgageParams(principal=1500.0, annual_rate=0.045, months_remaining=80)
    sched_term = FrenchAmortizer.generate_schedule(params_term)

    params_div = MortgageParams(principal=1500.0, annual_rate=0.045, months_remaining=120)
    sched_div = FrenchAmortizer.generate_schedule(params_div)

    fig = create_prepayment_comparison_chart(sched_base, sched_term, sched_div)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3


def test_chart_mixed_rate_stress():
    """Valida la generación del gráfico de estrés de tasa mixta."""
    res = MixedRateRiskAnalyzer.evaluate(
        principal_uf=3000.0,
        total_months=180,
        fixed_period_months=36,
        initial_fixed_rate_pct=3.9,
        baseline_subsequent_rate_pct=4.8,
        pure_fixed_rate_pct=4.6,
    )
    fig = create_mixed_rate_stress_chart(
        pure_fixed_dividend=res.pure_fixed_dividend_uf,
        scenarios=res.scenarios,
        fixed_period_months=36,
        total_months=180,
    )
    assert isinstance(fig, go.Figure)
    # 1 línea pura fija + 4 escenarios = 5 trazas
    assert len(fig.data) == 5


def test_chart_french_vs_german():
    """Valida el gráfico comparativo Francés vs Alemán."""
    params = MortgageParams(principal=2500.0, annual_rate=0.045, months_remaining=120)
    s_french = FrenchAmortizer.generate_schedule(params)
    s_german = GermanAmortizer.generate_schedule(params)

    fig = create_french_vs_german_chart(s_french, s_german)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2


def test_chart_actuarial_insurability_gauge():
    """Valida el velocímetro / indicador de asegurabilidad."""
    fig = create_actuarial_insurability_gauge(72, "OBSERVACIÓN")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
