"""Pruebas de integración para los endpoints REST del Hito 8 en FastAPI."""

from fastapi.testclient import TestClient
from src.app.api import app

client = TestClient(app)


def test_api_simulate_german():
    """Valida el endpoint POST /api/v1/simulate/german."""
    payload = {
        "principal": 3000.0,
        "annual_rate_pct": 4.5,
        "term_years": 20,
        "include_schedule": True,
    }
    response = client.post("/api/v1/simulate/german", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["principal_uf"] == 3000.0
    assert data["months"] == 240
    assert data["fixed_principal_amortization_uf"] == 3000.0 / 240
    assert data["initial_total_dividend_uf"] > data["final_total_dividend_uf"]
    assert "comparison_with_french" in data
    assert data["comparison_with_french"]["interest_savings_uf"] > 0
    assert len(data["schedule"]) == 240


def test_api_prepayment_simulate():
    """Valida el endpoint POST /api/v1/prepayment/simulate."""
    payload = {
        "balance_uf": 3200.0,
        "annual_rate_pct": 5.0,
        "months_remaining": 180,
        "prepayment_amount_uf": 400.0,
        "penalty_months": 1.5,
    }
    response = client.post("/api/v1/prepayment/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["original_balance_uf"] == 3200.0
    assert data["prepayment_amount_uf"] == 400.0
    assert data["new_balance_uf"] == 2800.0
    assert data["prepayment_penalty_uf"] > 0
    assert data["reduce_term_option"]["months_saved"] > 0
    assert data["reduce_dividend_option"]["monthly_dividend_saving_uf"] > 0
    assert data["best_recommendation"] in ["REDUCE_TERM", "REDUCE_DIVIDEND"]


def test_api_mixed_rate_stress():
    """Valida el endpoint POST /api/v1/mixed-rate/stress-test."""
    payload = {
        "principal_uf": 3500.0,
        "total_months": 240,
        "fixed_period_months": 36,
        "initial_fixed_rate_pct": 3.9,
        "baseline_subsequent_rate_pct": 4.8,
        "pure_fixed_rate_pct": 4.6,
    }
    response = client.post("/api/v1/mixed-rate/stress-test", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["principal_uf"] == 3500.0
    assert data["fixed_period_months"] == 36
    assert len(data["scenarios"]) == 4
    assert data["breakeven_variable_rate_pct"] > 0


def test_api_insurability_check():
    """Valida el endpoint POST /api/v1/insurability/check."""
    payload = {
        "current_age": 45,
        "loan_term_years": 25,
    }
    response = client.post("/api/v1/insurability/check", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["current_age"] == 45
    assert data["loan_term_years"] == 25
    assert data["maturity_age"] == 70
    assert data["status"] == "ESTÁNDAR"
    assert data["is_insurable"] is True
    assert len(data["age_bracket_table"]) > 0


def test_api_root_metadata_includes_advanced_endpoints():
    """Verifica que el endpoint raíz '/' exponga los nuevos endpoints en su metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "simulate_german" in data["endpoints"]
    assert "prepayment_simulate" in data["endpoints"]
    assert "mixed_rate_stress" in data["endpoints"]
    assert "insurability_check" in data["endpoints"]
