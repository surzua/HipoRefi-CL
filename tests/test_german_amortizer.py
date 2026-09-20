"""Pruebas unitarias para el motor de amortización alemana (GermanAmortizer)."""

import pytest
from src.core.amortizer import GermanAmortizer, MortgageParams


def test_german_amortizer_fixed_capital():
    """Verifica que la amortización de capital sea estrictamente constante mes a mes."""
    principal = 2400.0
    months = 240
    annual_rate = 0.045

    params = MortgageParams(
        principal=principal,
        annual_rate=annual_rate,
        months_remaining=months,
        fire_insurance_monthly_uf=0.5,
        life_insurance_rate_monthly=0.00028,
    )

    sched = GermanAmortizer.generate_schedule(params)
    assert len(sched) == months

    expected_fixed_amort = principal / months
    for row in sched[:-1]:
        assert pytest.approx(row["amortization_uf"], rel=1e-3) == expected_fixed_amort

    # Saldo final debe extinguirse exactamente a cero
    assert sched[-1]["end_balance_uf"] == 0.0


def test_german_amortizer_decreasing_dividend():
    """Verifica que el dividendo financiero e intereses decrezcan monotonicamente mes a mes."""
    params = MortgageParams(
        principal=3000.0,
        annual_rate=0.05,
        months_remaining=120,
    )
    sched = GermanAmortizer.generate_schedule(params)

    for i in range(len(sched) - 1):
        assert sched[i]["interest_uf"] > sched[i + 1]["interest_uf"]
        assert sched[i]["financial_dividend_uf"] > sched[i + 1]["financial_dividend_uf"]


def test_german_vs_french_interest_savings():
    """Verifica que el sistema alemán pague menos intereses totales que el sistema francés."""
    params = MortgageParams(
        principal=3200.0,
        annual_rate=0.048,
        months_remaining=240,
        fire_insurance_monthly_uf=0.7,
        life_insurance_rate_monthly=0.00028,
    )

    comp = GermanAmortizer.compare_french_vs_german(params)

    assert comp["german_total_interest_uf"] < comp["french_total_interest_uf"]
    assert comp["interest_savings_uf"] > 0
    assert comp["interest_savings_pct"] > 0

    # El primer dividendo alemán debe ser mayor que el francés
    assert comp["german_initial_total_dividend_uf"] > comp["french_initial_total_dividend_uf"]
    # El dividendo final alemán debe ser menor que el francés
    assert comp["german_final_total_dividend_uf"] < comp["french_initial_total_dividend_uf"]


def test_german_invalid_params():
    """Verifica manejo de excepciones ante parámetros inválidos."""
    with pytest.raises(ValueError, match="positivo"):
        GermanAmortizer.calculate_fixed_principal_amortization(1000.0, 0)

    with pytest.raises(ValueError, match="negativo"):
        GermanAmortizer.calculate_fixed_principal_amortization(-100.0, 120)

    with pytest.raises(ValueError, match="mayor a 0"):
        GermanAmortizer.generate_schedule(MortgageParams(principal=1000.0, annual_rate=0.04, months_remaining=0))
