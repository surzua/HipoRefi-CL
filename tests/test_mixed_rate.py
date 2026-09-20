"""Pruebas unitarias para el modelado de riesgo de tasa mixta vs. fija (MixedRateRiskAnalyzer)."""

import pytest
from src.core.advanced_financial import MixedRateRiskAnalyzer


def test_mixed_rate_scenarios_structure():
    """Valida la generación de los 4 escenarios de estrés y el salto de dividendo al mes K."""
    principal = 3200.0
    total_months = 240
    fixed_months = 36
    initial_rate = 3.90
    baseline_subsequent = 4.80
    pure_fixed_rate = 4.60

    res = MixedRateRiskAnalyzer.evaluate(
        principal_uf=principal,
        total_months=total_months,
        fixed_period_months=fixed_months,
        initial_fixed_rate_pct=initial_rate,
        baseline_subsequent_rate_pct=baseline_subsequent,
        pure_fixed_rate_pct=pure_fixed_rate,
    )

    assert len(res.scenarios) == 4
    scenario_names = [s.scenario_name for s in res.scenarios]
    assert any("Bajista" in name for name in scenario_names)
    assert any("Base" in name for name in scenario_names)
    assert any("Alcista" in name for name in scenario_names)
    assert any("Severo" in name for name in scenario_names)

    # En el escenario alcista y severo, el dividendo post-reinicio debe ser mayor al inicial
    base_scen = next(s for s in res.scenarios if s.rate_change_bps == 0)
    alcista_scen = next(s for s in res.scenarios if s.rate_change_bps == 150)
    severo_scen = next(s for s in res.scenarios if s.rate_change_bps == 300)

    assert alcista_scen.dividend_jump_uf > base_scen.dividend_jump_uf
    assert severo_scen.dividend_jump_uf > alcista_scen.dividend_jump_uf
    assert severo_scen.total_cost_uf > alcista_scen.total_cost_uf


def test_mixed_rate_breakeven_calculation():
    """Verifica que la tasa variable de quiebre (Breakeven Rate) esté en un rango razonable y coherente."""
    res = MixedRateRiskAnalyzer.evaluate(
        principal_uf=3000.0,
        total_months=240,
        fixed_period_months=60,  # 5 años fijos
        initial_fixed_rate_pct=3.80,
        baseline_subsequent_rate_pct=4.80,
        pure_fixed_rate_pct=4.60,
    )

    # Dado que la tasa inicial mixta (3.80%) es menor que la fija pura (4.60%),
    # la tasa posterior debe poder subir por encima de 4.60% para compensar el ahorro acumulado inicial
    assert res.breakeven_variable_rate_pct > 4.60
    assert 4.60 < res.breakeven_variable_rate_pct < 10.0


def test_mixed_rate_invalid_parameters():
    """Valida validación de parámetros erróneos."""
    with pytest.raises(ValueError, match="El capital debe ser positivo"):
        MixedRateRiskAnalyzer.evaluate(0.0, 240, 36, 4.0, 5.0, 4.5)

    with pytest.raises(ValueError, match="período fijo debe ser menor al plazo total"):
        MixedRateRiskAnalyzer.evaluate(1000.0, 120, 120, 4.0, 5.0, 4.5)
