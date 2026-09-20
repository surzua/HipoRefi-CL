"""Pruebas unitarias para el simulador de prepagos y abonos extraordinarios (PrepaymentSimulator)."""

import pytest
from src.core.advanced_financial import PrepaymentSimulator


def test_prepayment_penalty_lgb_art_100():
    """Valida el cálculo de la comisión máxima de 1.5 meses de intereses devengados."""
    amount_uf = 500.0
    annual_rate = 0.048  # r_mensual ~ 0.003914
    penalty = PrepaymentSimulator.calculate_penalty(amount_uf, annual_rate, penalty_months=1.5)

    r_monthly = (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0
    expected_penalty = 1.5 * (amount_uf * r_monthly)
    assert pytest.approx(penalty, rel=1e-4) == expected_penalty


def test_prepayment_reduce_term_option():
    """Valida la opción de reducción de plazo: ahorra meses manteniendo cuota similar."""
    balance_uf = 3000.0
    annual_rate = 0.045
    months = 240
    prepay_amount = 500.0

    res = PrepaymentSimulator.simulate(
        balance_uf=balance_uf,
        annual_rate=annual_rate,
        months_remaining=months,
        prepayment_amount_uf=prepay_amount,
    )

    assert res.new_balance_uf == 2500.0
    assert res.prepayment_penalty_uf > 0
    assert res.total_cash_outlay_uf == prepay_amount + res.prepayment_penalty_uf

    term_opt = res.reduce_term_option
    assert term_opt.modality == "REDUCE_TERM"
    assert term_opt.new_months < months
    assert term_opt.months_saved > 0
    assert term_opt.interest_savings_uf > 0
    assert term_opt.npv_uf > 0


def test_prepayment_reduce_dividend_option():
    """Valida la opción de reducción de dividendo: mantiene plazo y reduce cuota mensual."""
    balance_uf = 3000.0
    annual_rate = 0.045
    months = 240
    prepay_amount = 500.0

    res = PrepaymentSimulator.simulate(
        balance_uf=balance_uf,
        annual_rate=annual_rate,
        months_remaining=months,
        prepayment_amount_uf=prepay_amount,
    )

    div_opt = res.reduce_dividend_option
    assert div_opt.modality == "REDUCE_DIVIDEND"
    assert div_opt.new_months == months
    assert div_opt.months_saved == 0
    assert div_opt.monthly_dividend_saving_uf > 0
    assert div_opt.interest_savings_uf > 0
    # Reducción de plazo siempre ahorra más intereses nominales que reducción de dividendo
    assert res.reduce_term_option.interest_savings_uf > div_opt.interest_savings_uf


def test_prepayment_full_payoff():
    """Valida el escenario de prepago del 100% del saldo (extinción total de la deuda)."""
    balance_uf = 1500.0
    annual_rate = 0.04
    months = 120

    res = PrepaymentSimulator.simulate(
        balance_uf=balance_uf,
        annual_rate=annual_rate,
        months_remaining=months,
        prepayment_amount_uf=balance_uf,
    )

    assert res.new_balance_uf == 0.0
    assert res.reduce_term_option.new_months == 0
    assert res.reduce_term_option.months_saved == months
    assert res.reduce_term_option.interest_savings_uf == res.original_total_interest_uf


def test_prepayment_invalid_inputs():
    """Verifica manejo de errores de validación de entradas."""
    with pytest.raises(ValueError, match="saldo insoluto debe ser mayor a 0"):
        PrepaymentSimulator.simulate(0.0, 0.04, 120, 100.0)

    with pytest.raises(ValueError, match="plazo restante en meses debe ser mayor a 0"):
        PrepaymentSimulator.simulate(1000.0, 0.04, 0, 100.0)

    with pytest.raises(ValueError, match="abono extraordinario debe ser mayor a 0"):
        PrepaymentSimulator.simulate(1000.0, 0.04, 120, 0.0)

    with pytest.raises(ValueError, match="no puede exceder el saldo"):
        PrepaymentSimulator.simulate(1000.0, 0.04, 120, 1500.0)
