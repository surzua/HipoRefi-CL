"""Pruebas unitarias e integrales para el módulo Comparador Head-to-Head (Hito 10)."""

import pytest
from fastapi.testclient import TestClient

from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.core.metrics import HeadToHeadComparator, HeadToHeadComparisonResult
from src.app.charts import (
    create_head_to_head_comparison_chart,
    create_head_to_head_trajectory_chart,
)
from src.app.api import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def base_mortgage_setup():
    balance_uf = 3200.0
    current_rate_dec = 0.052  # 5.20%
    months = 180  # 15 años

    params_curr = MortgageParams(
        principal=balance_uf,
        annual_rate=current_rate_dec,
        months_remaining=months,
        fire_insurance_monthly_uf=0.70,
        life_insurance_rate_monthly=0.00028,
    )
    sched_curr = FrenchAmortizer.generate_schedule(params_curr)

    # Banco A: Tasa baja (4.10%), 15 años
    params_a = MortgageParams(
        principal=balance_uf,
        annual_rate=0.041,
        months_remaining=180,
        fire_insurance_monthly_uf=0.70,
        life_insurance_rate_monthly=0.00028,
    )
    sched_a = FrenchAmortizer.generate_schedule(params_a)

    # Banco B: Tasa moderada (4.60%), 15 años
    params_b = MortgageParams(
        principal=balance_uf,
        annual_rate=0.046,
        months_remaining=180,
        fire_insurance_monthly_uf=0.70,
        life_insurance_rate_monthly=0.00028,
    )
    sched_b = FrenchAmortizer.generate_schedule(params_b)

    return {
        "balance_uf": balance_uf,
        "current_rate_pct": 5.20,
        "months": months,
        "sched_curr": sched_curr,
        "sched_a": sched_a,
        "sched_b": sched_b,
    }


def test_head_to_head_comparator_winner_a(base_mortgage_setup):
    """Verifica que el comparador identifique correctamente al Banco A como ganador por menor tasa y mayor VPN."""
    s = base_mortgage_setup
    result = HeadToHeadComparator.compare(
        current_schedule=s["sched_curr"],
        current_balance_uf=s["balance_uf"],
        current_annual_rate_pct=s["current_rate_pct"],
        current_months=s["months"],
        bank_a_name="Santander",
        bank_a_schedule=s["sched_a"],
        bank_a_rate_pct=4.10,
        bank_a_term_years=15,
        bank_a_upfront_costs_uf=45.0,
        bank_b_name="BancoEstado",
        bank_b_schedule=s["sched_b"],
        bank_b_rate_pct=4.60,
        bank_b_term_years=15,
        bank_b_upfront_costs_uf=45.0,
    )

    assert isinstance(result, HeadToHeadComparisonResult)
    assert result.winner_bank == "Santander"
    assert result.npv_diff_uf > 0.0
    assert result.monthly_dividend_diff_uf > 0.0  # Banco A tiene dividendo menor
    assert result.total_cost_diff_uf > 0.0  # Banco A paga menos costo total
    assert "Santander" in result.verdict_rationale

    d = result.to_dict()
    assert d["winner_bank"] == "Santander"
    assert "bank_a" in d and "bank_b" in d
    assert d["bank_a"]["annual_rate_pct"] == 4.10
    assert d["bank_b"]["annual_rate_pct"] == 4.60


def test_head_to_head_comparator_winner_b(base_mortgage_setup):
    """Invierte los bancos y comprueba que gane el Banco B."""
    s = base_mortgage_setup
    result = HeadToHeadComparator.compare(
        current_schedule=s["sched_curr"],
        current_balance_uf=s["balance_uf"],
        current_annual_rate_pct=s["current_rate_pct"],
        current_months=s["months"],
        bank_a_name="Banco Caro",
        bank_a_schedule=s["sched_b"],
        bank_a_rate_pct=4.60,
        bank_a_term_years=15,
        bank_a_upfront_costs_uf=45.0,
        bank_b_name="Banco Barato",
        bank_b_schedule=s["sched_a"],
        bank_b_rate_pct=4.10,
        bank_b_term_years=15,
        bank_b_upfront_costs_uf=45.0,
    )

    assert result.winner_bank == "Banco Barato"
    assert result.npv_diff_uf < 0.0
    assert "Banco Barato" in result.verdict_rationale


def test_head_to_head_comparator_technical_tie(base_mortgage_setup):
    """Comprueba que si ambas opciones son idénticas se declare empate técnico."""
    s = base_mortgage_setup
    result = HeadToHeadComparator.compare(
        current_schedule=s["sched_curr"],
        current_balance_uf=s["balance_uf"],
        current_annual_rate_pct=s["current_rate_pct"],
        current_months=s["months"],
        bank_a_name="Banco Alpha",
        bank_a_schedule=s["sched_a"],
        bank_a_rate_pct=4.10,
        bank_a_term_years=15,
        bank_a_upfront_costs_uf=45.0,
        bank_b_name="Banco Beta",
        bank_b_schedule=s["sched_a"],
        bank_b_rate_pct=4.10,
        bank_b_term_years=15,
        bank_b_upfront_costs_uf=45.0,
    )

    assert result.winner_bank == "EMPATE TÉCNICO"
    assert abs(result.npv_diff_uf) < 0.01


def test_head_to_head_api_endpoint(client):
    """Prueba el endpoint POST /api/v1/compare/head-to-head con parámetros válidos."""
    payload = {
        "balance_uf": 3200.0,
        "current_annual_rate_pct": 5.20,
        "current_months_remaining": 180,
        "current_dividend_uf": 23.10,
        "current_fire_insurance_uf": 0.70,
        "bank_a": {
            "bank_name": "Santander",
            "annual_rate_pct": 4.15,
            "term_years": 15,
            "fire_insurance_monthly_uf": 0.65,
            "life_insurance_rate_monthly": 0.00028,
        },
        "bank_b": {
            "bank_name": "BCI",
            "annual_rate_pct": 4.40,
            "term_years": 15,
            "fire_insurance_monthly_uf": 0.70,
            "life_insurance_rate_monthly": 0.00028,
        },
        "annual_discount_rate_pct": 2.5,
        "finance_costs": False,
        "additional_cash_uf": 0.0,
    }

    response = client.post("/api/v1/compare/head-to-head", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["winner_bank"] == "Santander"
    assert data["npv_diff_uf"] > 0.0
    assert "bank_a" in data and "bank_b" in data
    assert data["bank_a"]["bank_name"] == "Santander"
    assert data["bank_b"]["bank_name"] == "BCI"


def test_head_to_head_api_validation_error(client):
    """Prueba que el endpoint valide correctamente datos erróneos."""
    payload = {
        "balance_uf": -100.0,  # Inválido
        "current_annual_rate_pct": 5.20,
        "current_months_remaining": 180,
        "current_dividend_uf": 23.10,
        "bank_a": {
            "bank_name": "Santander",
            "annual_rate_pct": 4.15,
            "term_years": 15,
        },
        "bank_b": {
            "bank_name": "BCI",
            "annual_rate_pct": 4.40,
            "term_years": 15,
        },
    }
    response = client.post("/api/v1/compare/head-to-head", json=payload)
    assert response.status_code == 422


def test_head_to_head_charts_generation(base_mortgage_setup):
    """Verifica que los gráficos comparativos de Plotly se generen correctamente."""
    s = base_mortgage_setup
    a_metrics = {"monthly_dividend_uf": 21.0, "annual_rate_pct": 4.10, "npv_uf": 140.0}
    b_metrics = {"monthly_dividend_uf": 21.8, "annual_rate_pct": 4.60, "npv_uf": 80.0}
    curr_metrics = {"monthly_dividend_uf": 23.1, "annual_rate_pct": 5.20}

    fig_comp = create_head_to_head_comparison_chart(
        bank_a_name="Santander",
        a_metrics=a_metrics,
        bank_b_name="BancoEstado",
        b_metrics=b_metrics,
        current_metrics=curr_metrics,
    )
    assert fig_comp is not None
    assert len(fig_comp.data) == 3

    fig_traj = create_head_to_head_trajectory_chart(
        current_label="Actual",
        sched_curr=s["sched_curr"],
        bank_a_name="Santander",
        sched_a=s["sched_a"],
        bank_b_name="BancoEstado",
        sched_b=s["sched_b"],
    )
    assert fig_traj is not None
    assert len(fig_traj.data) == 3
