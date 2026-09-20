"""Pruebas unitarias para la curva actuarial de desgravamen y reglas de asegurabilidad (LifeInsuranceActuary)."""

import pytest
from src.core.advanced_financial import LifeInsuranceActuary


def test_life_insurance_rate_scaling_by_age():
    """Verifica que la prima mensual escale estrictamente según los tramos de edad de mercado."""
    rate_young = LifeInsuranceActuary.get_monthly_rate_for_age(30)
    rate_mid = LifeInsuranceActuary.get_monthly_rate_for_age(45)
    rate_senior = LifeInsuranceActuary.get_monthly_rate_for_age(55)
    rate_elder = LifeInsuranceActuary.get_monthly_rate_for_age(65)
    rate_late = LifeInsuranceActuary.get_monthly_rate_for_age(72)
    rate_over = LifeInsuranceActuary.get_monthly_rate_for_age(78)

    assert rate_young < rate_mid < rate_senior < rate_elder < rate_late < rate_over


def test_insurability_status_thresholds():
    """Verifica las 4 clasificaciones de asegurabilidad al vencimiento del crédito."""
    # 1. Estándar: <= 70 años (ej. 30 + 25 = 55)
    eval_std = LifeInsuranceActuary.evaluate_insurability(current_age=30, loan_term_years=25)
    assert eval_std.status == "ESTÁNDAR"
    assert eval_std.risk_level == "BAJO"
    assert eval_std.is_insurable is True

    # 2. Observación: 71 a 75 años (ej. 52 + 20 = 72)
    eval_obs = LifeInsuranceActuary.evaluate_insurability(current_age=52, loan_term_years=20)
    assert eval_obs.status == "OBSERVACIÓN"
    assert eval_obs.risk_level == "MEDIO"
    assert eval_obs.is_insurable is True

    # 3. Restricción Médica: 76 a 80 años (ej. 58 + 20 = 78)
    eval_restr = LifeInsuranceActuary.evaluate_insurability(current_age=58, loan_term_years=20)
    assert eval_restr.status == "RESTRICCIÓN_MÉDICA"
    assert eval_restr.risk_level == "ALTO"
    assert eval_restr.is_insurable is True

    # 4. Inasegurable: > 80 años (ej. 62 + 20 = 82)
    eval_unins = LifeInsuranceActuary.evaluate_insurability(current_age=62, loan_term_years=20)
    assert eval_unins.status == "INASEGURABLE"
    assert eval_unins.risk_level == "CRÍTICO"
    assert eval_unins.is_insurable is False


def test_dynamic_vs_flat_schedule_generation():
    """Verifica que el cronograma dinámico recalcule la prima anualmente conforme el deudor envejece."""
    principal = 3000.0
    annual_rate = 0.045
    months = 240  # 20 años
    start_age = 45

    sched, metrics = LifeInsuranceActuary.generate_dynamic_schedule(
        principal=principal,
        annual_rate=annual_rate,
        months=months,
        start_age=start_age,
    )

    assert len(sched) == months
    # La edad en el primer mes debe ser start_age, y en el último mes debe ser start_age + 19
    assert sched[0]["debtor_age"] == start_age
    assert sched[-1]["debtor_age"] == start_age + 19

    # La tasa mensual aplicada en el último año debe ser mayor que en el primero
    assert sched[-1]["life_insurance_rate_monthly"] > sched[0]["life_insurance_rate_monthly"]

    # Comprueba que las métricas registren el diferencial acumulado
    assert metrics["dynamic_total_life_insurance_uf"] > 0
    assert metrics["flat_total_life_insurance_uf"] > 0


def test_insurability_invalid_age():
    """Valida excepciones ante edades fuera de rango legal o plazos inválidos."""
    with pytest.raises(ValueError, match="mayor o igual a 18 años"):
        LifeInsuranceActuary.evaluate_insurability(16, 20)

    with pytest.raises(ValueError, match="positivo"):
        LifeInsuranceActuary.evaluate_insurability(40, 0)
