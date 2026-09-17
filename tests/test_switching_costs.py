"""Pruebas unitarias para SwitchingCostCalculator y costos de la Ley 21.236."""

import pytest
from src.core.switching_costs import SwitchingCostCalculator, SwitchingCostBreakdown


def test_prepayment_penalty_lgb_art_100():
    """Valida que la comisión de prepago no exceda 1.5 meses de intereses devengados."""
    balance_uf = 3000.0
    annual_rate = 0.045
    monthly_r = (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0
    expected_penalty = 1.5 * (balance_uf * monthly_r)

    computed_penalty = SwitchingCostCalculator.calculate_prepayment_penalty(balance_uf, annual_rate)
    assert pytest.approx(computed_penalty, rel=1e-5) == expected_penalty
    # Para 3.000 UF al 4.5%, 1.5 meses de intereses ronda ~16.5 UF
    assert 15.0 < computed_penalty < 18.0


def test_cbr_fee_subrogation_discount():
    """Valida la estimación del arancel CBR con descuento del 50% y cotas mínimas y máximas."""
    # Caso 1: Saldo pequeño, aplica piso mínimo de 1.5 UF
    fee_small = SwitchingCostCalculator.calculate_cbr_fee(500.0)
    assert fee_small == 1.5

    # Caso 2: Saldo normal (ej: 4.000 UF -> 4.0 UF)
    fee_normal = SwitchingCostCalculator.calculate_cbr_fee(4000.0)
    assert pytest.approx(fee_normal, abs=0.01) == 4.0

    # Caso 3: Saldo muy grande, aplica tope de 12.0 UF
    fee_huge = SwitchingCostCalculator.calculate_cbr_fee(25000.0)
    assert fee_huge == 12.0


def test_stamp_tax_exemption_dl_3475():
    """
    Valida el D.L. 3475:
    - Exención del 100% de timbres y estampillas si solo se refinancia saldo deudor.
    - Tributación del 0.8% únicamente sobre el capital adicional solicitado.
    """
    balance_uf = 2800.0
    rate = 0.042

    # Escenario 1: Refinanciamiento puro
    costs_pure = SwitchingCostCalculator.calculate_total_costs(balance_uf, rate, additional_cash_uf=0.0)
    assert costs_pure.stamp_tax_uf == 0.0

    # Escenario 2: Refinanciamiento con 500 UF de liquidez adicional
    costs_with_cash = SwitchingCostCalculator.calculate_total_costs(balance_uf, rate, additional_cash_uf=500.0)
    expected_tax = 500.0 * 0.008
    assert pytest.approx(costs_with_cash.stamp_tax_uf, abs=0.01) == expected_tax
    assert costs_with_cash.total_cost_uf == costs_pure.total_cost_uf + expected_tax


def test_total_switching_cost_breakdown():
    """Valida la coherencia de todos los componentes en el breakdown total."""
    balance_uf = 2000.0
    rate = 0.040

    costs = SwitchingCostCalculator.calculate_total_costs(balance_uf, rate)
    sum_components = (
        costs.prepayment_penalty_uf
        + costs.appraisal_uf
        + costs.title_deed_uf
        + costs.notary_uf
        + costs.cbr_uf
        + costs.stamp_tax_uf
    )
    assert pytest.approx(costs.total_cost_uf, abs=0.01) == sum_components
    assert isinstance(costs.to_dict(), dict)
