"""Pruebas unitarias para RefinanceAnalyzer y decisiones financieras (VPN, Payback)."""

import pytest
from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator
from src.core.metrics import RefinanceAnalyzer


def test_refinance_profitable_scenario():
    """
    Escenario claramente favorable:
    - Saldo: 3.500 UF
    - Tasa actual: 5.2% con 240 meses restantes
    - Nueva oferta: 3.6% con 240 meses restantes
    - Debe resultar en VPN positivo sustancial (>20 UF) y recomendación 'RECOMENDADO'.
    """
    params_current = MortgageParams(principal=3500.0, annual_rate=0.052, months_remaining=240)
    params_new = MortgageParams(principal=3500.0, annual_rate=0.036, months_remaining=240)

    sched_current = FrenchAmortizer.generate_schedule(params_current)
    sched_new = FrenchAmortizer.generate_schedule(params_new)

    costs = SwitchingCostCalculator.calculate_total_costs(3500.0, 0.052)
    decision = RefinanceAnalyzer.evaluate(
        current_schedule=sched_current,
        new_schedule=sched_new,
        upfront_costs_uf=costs.total_cost_uf,
        financed_costs=False,
    )

    assert decision.recommendation_flag == "RECOMENDADO"
    assert decision.npv_uf > 50.0
    assert decision.monthly_savings_uf > 0.0
    assert decision.payback_months is not None
    assert decision.payback_months <= 36


def test_refinance_unfavorable_scenario():
    """
    Escenario desfavorable:
    - Tasa actual es menor que la nueva tasa (ej. deudor que ya tenía tasa fija al 3.2% y le ofrecen 4.5%).
    - Debe resultar en VPN negativo y semáforo 'NO_CONVIENE'.
    """
    params_current = MortgageParams(principal=2000.0, annual_rate=0.032, months_remaining=180)
    params_new = MortgageParams(principal=2000.0, annual_rate=0.045, months_remaining=180)

    sched_current = FrenchAmortizer.generate_schedule(params_current)
    sched_new = FrenchAmortizer.generate_schedule(params_new)

    costs = SwitchingCostCalculator.calculate_total_costs(2000.0, 0.032)
    decision = RefinanceAnalyzer.evaluate(
        current_schedule=sched_current,
        new_schedule=sched_new,
        upfront_costs_uf=costs.total_cost_uf,
    )

    assert decision.recommendation_flag == "NO_CONVIENE"
    assert decision.npv_uf < 0.0


def test_term_extension_fallacy_detection():
    """
    Prueba de 'La Falacia del Dividendo':
    - El cliente tiene 120 meses restantes al 4.8%.
    - El banco le ofrece bajar el dividendo mensual extendiendo el plazo a 300 meses al 4.5%.
    - Aunque el dividendo mensual disminuye en el corto plazo, el costo acumulado de intereses
      durante 300 meses destruye patrimonio neto a largo plazo.
    """
    principal = 2500.0
    params_current = MortgageParams(principal=principal, annual_rate=0.048, months_remaining=120)
    params_new = MortgageParams(principal=principal, annual_rate=0.045, months_remaining=300)

    sched_current = FrenchAmortizer.generate_schedule(params_current)
    sched_new = FrenchAmortizer.generate_schedule(params_new)

    costs = SwitchingCostCalculator.calculate_total_costs(principal, 0.048)
    decision = RefinanceAnalyzer.evaluate(
        current_schedule=sched_current,
        new_schedule=sched_new,
        upfront_costs_uf=costs.total_cost_uf,
    )

    # El ahorro nominal total durante toda la vida debe ser fuertemente negativo
    assert decision.total_lifetime_savings_nominal_uf < 0.0
    assert decision.recommendation_flag in ["NO_CONVIENE", "EVALUAR_CON_CAUTELA"]


def test_financed_costs_scenario():
    """Verifica que financiar los gastos de cierre en el saldo del nuevo crédito funcione correctamente."""
    principal = 2000.0
    rate_current = 0.055
    rate_new = 0.038
    months = 180

    costs = SwitchingCostCalculator.calculate_total_costs(principal, rate_current)
    params_current = MortgageParams(principal=principal, annual_rate=rate_current, months_remaining=months)
    # Al financiar, el capital del nuevo crédito es principal + gastos
    params_new = MortgageParams(
        principal=principal + costs.total_cost_uf,
        annual_rate=rate_new,
        months_remaining=months,
    )

    sched_current = FrenchAmortizer.generate_schedule(params_current)
    sched_new = FrenchAmortizer.generate_schedule(params_new)

    decision = RefinanceAnalyzer.evaluate(
        current_schedule=sched_current,
        new_schedule=sched_new,
        upfront_costs_uf=costs.total_cost_uf,
        financed_costs=True,
    )

    assert decision.npv_uf > 0.0
    assert isinstance(decision.to_dict(), dict)
