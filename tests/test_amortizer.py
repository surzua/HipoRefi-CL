"""Pruebas unitarias para el motor de amortización francesa (FrenchAmortizer)."""

import pytest
from src.core.amortizer import FrenchAmortizer, MortgageParams


def test_monthly_interest_rate_effective():
    """Valida la convención efectiva mensual: r = (1 + i)^(1/12) - 1."""
    annual_rate = 0.045  # 4.5% anual
    expected_r = (1.0 + 0.045) ** (1.0 / 12.0) - 1.0
    computed_r = FrenchAmortizer.monthly_interest_rate(annual_rate)
    assert pytest.approx(computed_r, rel=1e-7) == expected_r
    # Debe ser cercana a 0.045 / 12 = 0.00375 pero ligeramente menor
    assert computed_r < (0.045 / 12.0)


def test_financial_dividend_formula():
    """Valida la cuota pura calculada contra un caso estándar de 2.000 UF a 20 años al 4.0%."""
    principal = 2000.0
    annual_rate = 0.040
    months = 240  # 20 años

    r = (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0
    factor = (1.0 + r) ** months
    expected_df = principal * (r * factor) / (factor - 1.0)

    computed_df = FrenchAmortizer.calculate_financial_dividend(principal, annual_rate, months)
    assert pytest.approx(computed_df, rel=1e-5) == expected_df
    # Para 2.000 UF a 20 años al 4%, la cuota pura está en torno a ~12.0 UF
    assert 11.5 < computed_df < 12.5


def test_invalid_parameters():
    """Verifica el rechazo de parámetros matemáticamente inválidos."""
    with pytest.raises(ValueError, match="El número de meses debe ser positivo"):
        FrenchAmortizer.calculate_financial_dividend(1000.0, 0.04, 0)

    with pytest.raises(ValueError, match="El saldo de capital no puede ser negativo"):
        FrenchAmortizer.calculate_financial_dividend(-500.0, 0.04, 120)


def test_amortization_schedule_full_properties():
    """
    Verifica las propiedades fundamentales del sistema francés:
    1. El saldo final al mes N debe ser exactamente 0.0.
    2. La suma de todas las amortizaciones de capital debe igualar el capital inicial.
    3. El saldo insoluto debe ser estrictamente decreciente mes a mes.
    4. La porción de interés es decreciente en el tiempo.
    5. La porción de amortización de capital es creciente en el tiempo.
    6. Los seguros se suman correctamente al dividendo total.
    """
    params = MortgageParams(
        principal=2500.0,
        annual_rate=0.042,
        months_remaining=180,  # 15 años restantes
        fire_insurance_monthly_uf=0.45,
        life_insurance_rate_monthly=0.00028,
    )

    schedule = FrenchAmortizer.generate_schedule(params)
    assert len(schedule) == 180

    # 1. Saldo final cero
    assert schedule[-1]["end_balance_uf"] == 0.0

    # 2. Conservación del capital (suma amortizaciones == saldo original)
    total_amortized = sum(item["amortization_uf"] for item in schedule)
    assert pytest.approx(total_amortized, abs=0.05) == params.principal

    # 3, 4 y 5. Dinámica de cuotas e intereses
    for i in range(len(schedule) - 1):
        curr = schedule[i]
        nxt = schedule[i + 1]

        # Saldo decreciente
        assert curr["end_balance_uf"] > nxt["end_balance_uf"]

        # Interés decreciente
        assert curr["interest_uf"] >= nxt["interest_uf"]

        # Amortización de capital creciente (excepto posible ajuste de cierre en el último mes)
        if i < len(schedule) - 2:
            assert curr["amortization_uf"] <= nxt["amortization_uf"]

        # Consistencia de la cuota total con seguros
        expected_total = curr["financial_dividend_uf"] + curr["life_insurance_uf"] + curr["fire_insurance_uf"]
        assert pytest.approx(curr["total_dividend_uf"], abs=0.01) == expected_total
