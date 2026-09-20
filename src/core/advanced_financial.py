"""Módulo Financiero y Normativo Avanzado de HipoRefi-CL (Hito 8).

Implementa:
1. PrepaymentSimulator: Inyección de capital, optimización reducción de plazo vs. cuota,
   comisión de prepago (Art. 100 LGB) y valor presente neto (VPN).
2. MixedRateRiskAnalyzer: Modelado de riesgo tasa mixta vs. fija, matrices de estrés
   (Base, Bajista -150 bps, Alcista +150 bps, Severo +300 bps) y tasa de quiebre (Breakeven Rate).
3. LifeInsuranceActuary: Curva actuarial de desgravamen por tramos etarios, cálculo dinámico
   y reglas de asegurabilidad técnica al vencimiento (>70, >75, >80 años).
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import math
import numpy as np

from src.core.amortizer import FrenchAmortizer, MortgageParams


# ============================================================================
# 1. Abonos Extraordinarios y Prepagos Parciales (LGB Art. 100)
# ============================================================================

@dataclass
class PrepaymentOptionResult:
    """Resultado cuantitativo de una modalidad de prepago parcial."""
    modality: str  # "REDUCE_TERM" o "REDUCE_DIVIDEND"
    new_months: int
    months_saved: int
    new_monthly_dividend_uf: float
    monthly_dividend_saving_uf: float
    total_interest_paid_uf: float
    interest_savings_uf: float
    interest_savings_pct: float
    total_cost_uf: float
    npv_uf: float  # Valor Presente Neto considerando desembolso inicial y descuento
    schedule_summary: List[Dict[str, Any]]


@dataclass
class PrepaymentEvaluation:
    """Evaluación comparativa completa de un abono extraordinario."""
    original_balance_uf: float
    prepayment_amount_uf: float
    prepayment_penalty_uf: float  # Art. 100 LGB
    total_cash_outlay_uf: float  # prepay + penalty
    new_balance_uf: float
    original_months: int
    original_dividend_uf: float
    original_total_interest_uf: float
    reduce_term_option: PrepaymentOptionResult
    reduce_dividend_option: PrepaymentOptionResult
    best_recommendation: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_balance_uf": round(self.original_balance_uf, 4),
            "prepayment_amount_uf": round(self.prepayment_amount_uf, 4),
            "prepayment_penalty_uf": round(self.prepayment_penalty_uf, 4),
            "total_cash_outlay_uf": round(self.total_cash_outlay_uf, 4),
            "new_balance_uf": round(self.new_balance_uf, 4),
            "original_months": self.original_months,
            "original_dividend_uf": round(self.original_dividend_uf, 4),
            "original_total_interest_uf": round(self.original_total_interest_uf, 4),
            "reduce_term_option": {
                "modality": self.reduce_term_option.modality,
                "new_months": self.reduce_term_option.new_months,
                "months_saved": self.reduce_term_option.months_saved,
                "new_monthly_dividend_uf": round(self.reduce_term_option.new_monthly_dividend_uf, 4),
                "monthly_dividend_saving_uf": round(self.reduce_term_option.monthly_dividend_saving_uf, 4),
                "total_interest_paid_uf": round(self.reduce_term_option.total_interest_paid_uf, 4),
                "interest_savings_uf": round(self.reduce_term_option.interest_savings_uf, 4),
                "interest_savings_pct": round(self.reduce_term_option.interest_savings_pct, 2),
                "total_cost_uf": round(self.reduce_term_option.total_cost_uf, 4),
                "npv_uf": round(self.reduce_term_option.npv_uf, 2),
            },
            "reduce_dividend_option": {
                "modality": self.reduce_dividend_option.modality,
                "new_months": self.reduce_dividend_option.new_months,
                "months_saved": self.reduce_dividend_option.months_saved,
                "new_monthly_dividend_uf": round(self.reduce_dividend_option.new_monthly_dividend_uf, 4),
                "monthly_dividend_saving_uf": round(self.reduce_dividend_option.monthly_dividend_saving_uf, 4),
                "total_interest_paid_uf": round(self.reduce_dividend_option.total_interest_paid_uf, 4),
                "interest_savings_uf": round(self.reduce_dividend_option.interest_savings_uf, 4),
                "interest_savings_pct": round(self.reduce_dividend_option.interest_savings_pct, 2),
                "total_cost_uf": round(self.reduce_dividend_option.total_cost_uf, 4),
                "npv_uf": round(self.reduce_dividend_option.npv_uf, 2),
            },
            "best_recommendation": self.best_recommendation,
            "rationale": self.rationale,
        }


class PrepaymentSimulator:
    """
    Simulador de prepagos parciales y abonos extraordinarios.
    Modela el impacto financiero bajo la Ley General de Bancos Art. 100.
    """

    @classmethod
    def calculate_penalty(
        cls,
        prepayment_amount_uf: float,
        annual_rate: float,
        penalty_months: float = 1.5,
    ) -> float:
        """
        Calcula la comisión de prepago según LGB Art. 100:
        Máximo 1.5 meses de intereses devengados sobre el capital prepagado.
        """
        r = FrenchAmortizer.monthly_interest_rate(annual_rate)
        return penalty_months * (prepayment_amount_uf * r)

    @classmethod
    def simulate(
        cls,
        balance_uf: float,
        annual_rate: float,
        months_remaining: int,
        prepayment_amount_uf: float,
        fire_insurance_monthly_uf: float = 0.0,
        life_insurance_rate_monthly: float = 0.00028,
        annual_discount_rate: float = 0.025,
        penalty_months: float = 1.5,
    ) -> PrepaymentEvaluation:
        """
        Evalúa el impacto de un abono extraordinario en las dos modalidades estándar:
        1. Reducción de Plazo (manteniendo dividendo actual).
        2. Reducción de Dividendo (manteniendo plazo actual).
        """
        if balance_uf <= 0:
            raise ValueError("El saldo insoluto debe ser mayor a 0.")
        if months_remaining <= 0:
            raise ValueError("El plazo restante en meses debe ser mayor a 0.")
        if prepayment_amount_uf <= 0:
            raise ValueError("El monto del abono extraordinario debe ser mayor a 0.")
        if prepayment_amount_uf > balance_uf:
            raise ValueError("El abono no puede exceder el saldo insoluto total.")

        penalty_uf = cls.calculate_penalty(prepayment_amount_uf, annual_rate, penalty_months)
        total_cash_outlay_uf = prepayment_amount_uf + penalty_uf
        new_balance_uf = balance_uf - prepayment_amount_uf

        # Escenario Base (sin prepago)
        params_base = MortgageParams(
            principal=balance_uf,
            annual_rate=annual_rate,
            months_remaining=months_remaining,
            fire_insurance_monthly_uf=fire_insurance_monthly_uf,
            life_insurance_rate_monthly=life_insurance_rate_monthly,
        )
        sched_base = FrenchAmortizer.generate_schedule(params_base)
        base_dividend_uf = sched_base[0]["total_dividend_uf"] if sched_base else 0.0
        base_interest_uf = sum(r["interest_uf"] for r in sched_base)
        base_flows = [r["total_dividend_uf"] for r in sched_base]

        monthly_discount = (1.0 + annual_discount_rate) ** (1.0 / 12.0) - 1.0

        # Modalidad 1: Reducción de Plazo
        if new_balance_uf == 0:
            term_new_months = 0
            term_months_saved = months_remaining
            term_new_div = 0.0
            term_interest_paid = 0.0
            term_interest_saved = base_interest_uf
            term_cost = 0.0
            sched_term: List[Dict[str, Any]] = []
            term_flows = [0.0] * months_remaining
        else:
            r_monthly = FrenchAmortizer.monthly_interest_rate(annual_rate)
            d_f_target = sched_base[0]["financial_dividend_uf"]

            arg = d_f_target / (d_f_target - new_balance_uf * r_monthly)
            calculated_n = math.log(arg) / math.log(1.0 + r_monthly)
            term_new_months = max(1, math.ceil(calculated_n))
            term_months_saved = max(0, months_remaining - term_new_months)

            params_term = MortgageParams(
                principal=new_balance_uf,
                annual_rate=annual_rate,
                months_remaining=term_new_months,
                fire_insurance_monthly_uf=fire_insurance_monthly_uf,
                life_insurance_rate_monthly=life_insurance_rate_monthly,
            )
            sched_term = FrenchAmortizer.generate_schedule(params_term)
            term_new_div = sched_term[0]["total_dividend_uf"] if sched_term else 0.0
            term_interest_paid = sum(r["interest_uf"] for r in sched_term)
            term_interest_saved = base_interest_uf - term_interest_paid
            term_cost = sum(r["total_dividend_uf"] for r in sched_term)

            term_flows = [r["total_dividend_uf"] for r in sched_term]
            if len(term_flows) < months_remaining:
                term_flows.extend([0.0] * (months_remaining - len(term_flows)))

        diff_term = np.array(base_flows) - np.array(term_flows)
        disc_factors = np.array([(1.0 + monthly_discount) ** (-t) for t in range(1, months_remaining + 1)])
        npv_term = -total_cash_outlay_uf + float(np.sum(diff_term * disc_factors))

        option_term = PrepaymentOptionResult(
            modality="REDUCE_TERM",
            new_months=term_new_months,
            months_saved=term_months_saved,
            new_monthly_dividend_uf=term_new_div,
            monthly_dividend_saving_uf=max(0.0, base_dividend_uf - term_new_div),
            total_interest_paid_uf=term_interest_paid,
            interest_savings_uf=term_interest_saved,
            interest_savings_pct=(term_interest_saved / base_interest_uf * 100.0) if base_interest_uf > 0 else 0.0,
            total_cost_uf=term_cost,
            npv_uf=npv_term,
            schedule_summary=sched_term[:12],
        )

        # Modalidad 2: Reducción de Dividendo
        if new_balance_uf == 0:
            div_new_div = 0.0
            div_interest_paid = 0.0
            div_interest_saved = base_interest_uf
            div_cost = 0.0
            sched_div: List[Dict[str, Any]] = []
            div_flows = [0.0] * months_remaining
        else:
            params_div = MortgageParams(
                principal=new_balance_uf,
                annual_rate=annual_rate,
                months_remaining=months_remaining,
                fire_insurance_monthly_uf=fire_insurance_monthly_uf,
                life_insurance_rate_monthly=life_insurance_rate_monthly,
            )
            sched_div = FrenchAmortizer.generate_schedule(params_div)
            div_new_div = sched_div[0]["total_dividend_uf"] if sched_div else 0.0
            div_interest_paid = sum(r["interest_uf"] for r in sched_div)
            div_interest_saved = base_interest_uf - div_interest_paid
            div_cost = sum(r["total_dividend_uf"] for r in sched_div)
            div_flows = [r["total_dividend_uf"] for r in sched_div]

        diff_div = np.array(base_flows) - np.array(div_flows)
        npv_div = -total_cash_outlay_uf + float(np.sum(diff_div * disc_factors))

        option_div = PrepaymentOptionResult(
            modality="REDUCE_DIVIDEND",
            new_months=months_remaining,
            months_saved=0,
            new_monthly_dividend_uf=div_new_div,
            monthly_dividend_saving_uf=base_dividend_uf - div_new_div,
            total_interest_paid_uf=div_interest_paid,
            interest_savings_uf=div_interest_saved,
            interest_savings_pct=(div_interest_saved / base_interest_uf * 100.0) if base_interest_uf > 0 else 0.0,
            total_cost_uf=div_cost,
            npv_uf=npv_div,
            schedule_summary=sched_div[:12],
        )

        if term_interest_saved > div_interest_saved and npv_term >= npv_div:
            best_rec = "REDUCE_TERM"
            rationale = (
                f"La opción de **Reducción de Plazo** es cuantitativamente superior: "
                f"permite ahorrar {term_interest_saved:.2f} UF en intereses ({term_interest_saved - div_interest_saved:.2f} UF más que reducir cuota) "
                f"y acorta el crédito en {term_months_saved} meses ({term_months_saved / 12:.1f} años). "
                f"El VPN de la inyección de capital es de {npv_term:.2f} UF."
            )
        else:
            best_rec = "REDUCE_DIVIDEND"
            rationale = (
                f"La opción de **Reducción de Dividendo** se recomienda si se busca alivio inmediato de flujo de caja: "
                f"el dividendo mensual disminuye en {base_dividend_uf - div_new_div:.2f} UF mensuales "
                f"manteniendo un ahorro neto de intereses de {div_interest_saved:.2f} UF y un VPN de {npv_div:.2f} UF."
            )

        return PrepaymentEvaluation(
            original_balance_uf=balance_uf,
            prepayment_amount_uf=prepayment_amount_uf,
            prepayment_penalty_uf=penalty_uf,
            total_cash_outlay_uf=total_cash_outlay_uf,
            new_balance_uf=new_balance_uf,
            original_months=months_remaining,
            original_dividend_uf=base_dividend_uf,
            original_total_interest_uf=base_interest_uf,
            reduce_term_option=option_term,
            reduce_dividend_option=option_div,
            best_recommendation=best_rec,
            rationale=rationale,
        )


# ============================================================================
# 2. Modelado de Riesgo: Tasa Mixta vs. Fija (Matrices de Estrés)
# ============================================================================

@dataclass
class StressScenarioResult:
    scenario_name: str
    rate_change_bps: int
    variable_annual_rate_pct: float
    initial_dividend_uf: float
    subsequent_dividend_uf: float
    dividend_jump_uf: float
    dividend_jump_pct: float
    total_cost_uf: float
    total_interest_uf: float
    npv_vs_fixed_uf: float
    monthly_dividends_sample: List[float]


@dataclass
class MixedRateStressResponseData:
    principal_uf: float
    total_months: int
    fixed_period_months: int
    initial_fixed_rate_pct: float
    baseline_subsequent_rate_pct: float
    pure_fixed_rate_pct: float
    pure_fixed_dividend_uf: float
    pure_fixed_total_interest_uf: float
    pure_fixed_total_cost_uf: float
    breakeven_variable_rate_pct: float
    scenarios: List[StressScenarioResult]
    recommendation_summary: str


class MixedRateRiskAnalyzer:
    """
    Analizador de riesgo y estrés financiero para créditos hipotecarios con tasa mixta en Chile.
    Contrasta el beneficio de corto plazo de una tasa inicial reducida (3 o 5 años)
    frente a la exposición a volatilidad de tasas de interés (TPM/TAB) en el período variable.
    """

    @classmethod
    def evaluate(
        cls,
        principal_uf: float,
        total_months: int,
        fixed_period_months: int,
        initial_fixed_rate_pct: float,
        baseline_subsequent_rate_pct: float,
        pure_fixed_rate_pct: float,
        fire_insurance_monthly_uf: float = 0.0,
        life_insurance_rate_monthly: float = 0.00028,
        annual_discount_rate_pct: float = 2.5,
    ) -> MixedRateStressResponseData:
        """
        Ejecuta simulación de tasa mixta con 4 escenarios de estrés:
        1. Base: Tasa esperada de mercado
        2. Bajista: -150 bps
        3. Alcista: +150 bps
        4. Severo: +300 bps
        Calcula además la tasa variable posterior de quiebre patrimonial (Breakeven Rate).
        """
        if principal_uf <= 0:
            raise ValueError("El capital debe ser positivo.")
        if total_months <= 0 or fixed_period_months <= 0:
            raise ValueError("Los meses deben ser positivos.")
        if fixed_period_months >= total_months:
            raise ValueError("El período fijo debe ser menor al plazo total.")

        disc_monthly = (1.0 + (annual_discount_rate_pct / 100.0)) ** (1.0 / 12.0) - 1.0

        # 1. Crédito 100% Fijo de Referencia
        pure_fixed_dec = pure_fixed_rate_pct / 100.0
        params_fixed = MortgageParams(
            principal=principal_uf,
            annual_rate=pure_fixed_dec,
            months_remaining=total_months,
            fire_insurance_monthly_uf=fire_insurance_monthly_uf,
            life_insurance_rate_monthly=life_insurance_rate_monthly,
        )
        sched_fixed = FrenchAmortizer.generate_schedule(params_fixed)
        pure_fixed_div = sched_fixed[0]["total_dividend_uf"] if sched_fixed else 0.0
        pure_fixed_interest = sum(r["interest_uf"] for r in sched_fixed)
        pure_fixed_cost = sum(r["total_dividend_uf"] for r in sched_fixed)
        fixed_flows = np.array([r["total_dividend_uf"] for r in sched_fixed])
        disc_factors = np.array([(1.0 + disc_monthly) ** (-t) for t in range(1, total_months + 1)])

        # 2. Simulación de los primeros K meses a tasa mixta fija
        initial_rate_dec = initial_fixed_rate_pct / 100.0
        params_initial = MortgageParams(
            principal=principal_uf,
            annual_rate=initial_rate_dec,
            months_remaining=total_months,
            fire_insurance_monthly_uf=fire_insurance_monthly_uf,
            life_insurance_rate_monthly=life_insurance_rate_monthly,
        )
        sched_k = FrenchAmortizer.generate_schedule(params_initial)[:fixed_period_months]
        balance_at_k = sched_k[-1]["end_balance_uf"]
        initial_div_uf = sched_k[0]["total_dividend_uf"]

        # Escenarios de estrés
        scenarios_cfg = [
            ("Bajista (-150 bps)", -150),
            ("Escenario Base", 0),
            ("Alcista (+150 bps)", 150),
            ("Estrés Severo (+300 bps)", 300),
        ]

        scenario_results: List[StressScenarioResult] = []
        remaining_months = total_months - fixed_period_months

        for name, delta_bps in scenarios_cfg:
            subsequent_rate_pct = max(0.5, baseline_subsequent_rate_pct + (delta_bps / 100.0))
            subsequent_rate_dec = subsequent_rate_pct / 100.0

            params_sub = MortgageParams(
                principal=balance_at_k,
                annual_rate=subsequent_rate_dec,
                months_remaining=remaining_months,
                fire_insurance_monthly_uf=fire_insurance_monthly_uf,
                life_insurance_rate_monthly=life_insurance_rate_monthly,
            )
            sched_sub = FrenchAmortizer.generate_schedule(params_sub)

            subsequent_div_uf = sched_sub[0]["total_dividend_uf"] if sched_sub else 0.0
            jump_uf = subsequent_div_uf - initial_div_uf
            jump_pct = (jump_uf / initial_div_uf * 100.0) if initial_div_uf > 0 else 0.0

            combined_flows = [r["total_dividend_uf"] for r in sched_k] + [r["total_dividend_uf"] for r in sched_sub]
            combined_interest = sum(r["interest_uf"] for r in sched_k) + sum(r["interest_uf"] for r in sched_sub)
            combined_cost = sum(combined_flows)

            diff_flows = fixed_flows - np.array(combined_flows)
            npv_vs_fixed = float(np.sum(diff_flows * disc_factors))

            sample_divs = combined_flows

            scenario_results.append(StressScenarioResult(
                scenario_name=name,
                rate_change_bps=delta_bps,
                variable_annual_rate_pct=round(subsequent_rate_pct, 2),
                initial_dividend_uf=round(initial_div_uf, 4),
                subsequent_dividend_uf=round(subsequent_div_uf, 4),
                dividend_jump_uf=round(jump_uf, 4),
                dividend_jump_pct=round(jump_pct, 2),
                total_cost_uf=round(combined_cost, 4),
                total_interest_uf=round(combined_interest, 4),
                npv_vs_fixed_uf=round(npv_vs_fixed, 2),
                monthly_dividends_sample=sample_divs,
            ))

        # 3. Cálculo de la Tasa de Quiebre (Breakeven Variable Rate)
        def npv_diff_for_sub_rate(test_rate_pct: float) -> float:
            r_dec = test_rate_pct / 100.0
            p_test = MortgageParams(
                principal=balance_at_k,
                annual_rate=r_dec,
                months_remaining=remaining_months,
                fire_insurance_monthly_uf=fire_insurance_monthly_uf,
                life_insurance_rate_monthly=life_insurance_rate_monthly,
            )
            s_test = FrenchAmortizer.generate_schedule(p_test)
            c_flows = np.array([r["total_dividend_uf"] for r in sched_k] + [r["total_dividend_uf"] for r in s_test])
            return float(np.sum((fixed_flows - c_flows) * disc_factors))

        low = 1.0
        high = 20.0
        breakeven_rate = baseline_subsequent_rate_pct

        f_low = npv_diff_for_sub_rate(low)
        f_high = npv_diff_for_sub_rate(high)

        if f_low * f_high <= 0:
            for _ in range(40):
                mid = (low + high) / 2.0
                f_mid = npv_diff_for_sub_rate(mid)
                if abs(f_mid) < 0.01:
                    breakeven_rate = mid
                    break
                if f_low * f_mid < 0:
                    high = mid
                    f_high = f_mid
                else:
                    low = mid
                    f_low = f_mid
            breakeven_rate = (low + high) / 2.0
        elif f_low < 0:
            breakeven_rate = low
        else:
            breakeven_rate = high

        if breakeven_rate < baseline_subsequent_rate_pct:
            summary = (
                f"ALTO RIESGO: La tasa variable posterior de quiebre es {breakeven_rate:.2f}%, menor a la tasa esperada ({baseline_subsequent_rate_pct:.2f}%). "
                f"La tasa fija pura al {pure_fixed_rate_pct:.2f}% ofrece mayor protección patrimonial."
            )
        else:
            margin = breakeven_rate - baseline_subsequent_rate_pct
            summary = (
                f"OPCIÓN VIABLE CON MARGEN DE SEGURIDAD: La tasa variable posterior puede subir hasta {breakeven_rate:.2f}% "
                f"(un margen de +{margin:.2f}% o +{margin * 100:.0f} bps sobre la tasa base) antes de que la tasa mixta "
                f"destruya el ahorro acumulado durante los primeros {fixed_period_months} meses frente a la fija pura."
            )

        return MixedRateStressResponseData(
            principal_uf=round(principal_uf, 4),
            total_months=total_months,
            fixed_period_months=fixed_period_months,
            initial_fixed_rate_pct=round(initial_fixed_rate_pct, 2),
            baseline_subsequent_rate_pct=round(baseline_subsequent_rate_pct, 2),
            pure_fixed_rate_pct=round(pure_fixed_rate_pct, 2),
            pure_fixed_dividend_uf=round(pure_fixed_div, 4),
            pure_fixed_total_interest_uf=round(pure_fixed_interest, 4),
            pure_fixed_total_cost_uf=round(pure_fixed_cost, 4),
            breakeven_variable_rate_pct=round(breakeven_rate, 2),
            scenarios=scenario_results,
            recommendation_summary=summary,
        )


# ============================================================================
# 3. Curva Actuarial de Desgravamen y Reglas de Asegurabilidad por Edad
# ============================================================================

@dataclass
class InsurabilityEvaluation:
    current_age: int
    loan_term_years: int
    maturity_age: int
    initial_monthly_rate: float
    final_monthly_rate: float
    status: str  # "ESTÁNDAR", "OBSERVACIÓN", "RESTRICCIÓN_MÉDICA", "INASEGURABLE"
    risk_level: str  # "BAJO", "MEDIO", "ALTO", "CRÍTICO"
    is_insurable: bool
    medical_requirements: List[str]
    regulatory_alert: str
    age_bracket_table: List[Dict[str, Any]]


class LifeInsuranceActuary:
    """
    Motor actuarial y normativo de seguro de desgravamen para hipotecas en Chile.
    Modela la estructura de costos según tramos de edad observados en pólizas colectivas licitadas
    y valida las reglas de asegurabilidad al término del crédito (políticas CMF y aseguradoras).
    """

    AGE_BRACKETS = [
        (0, 39, 0.00024, "18 a 39 años"),
        (40, 49, 0.00038, "40 a 49 años"),
        (50, 59, 0.00065, "50 a 59 años"),
        (60, 69, 0.00140, "60 a 69 años"),
        (70, 74, 0.00260, "70 a 74 años"),
        (75, 120, 0.00450, "75 años o más"),
    ]

    @classmethod
    def get_monthly_rate_for_age(cls, age: int) -> float:
        """Retorna la tasa mensual estimada de desgravamen para la edad especificada."""
        for min_age, max_age, rate, _ in cls.AGE_BRACKETS:
            if min_age <= age <= max_age:
                return rate
        return 0.00028

    @classmethod
    def evaluate_insurability(cls, current_age: int, loan_term_years: int) -> InsurabilityEvaluation:
        """
        Valida la condición de asegurabilidad técnica al vencimiento del crédito.
        """
        if current_age < 18:
            raise ValueError("La edad del deudor debe ser mayor o igual a 18 años.")
        if loan_term_years <= 0:
            raise ValueError("El plazo del crédito debe ser positivo.")

        maturity_age = current_age + loan_term_years
        initial_rate = cls.get_monthly_rate_for_age(current_age)
        final_rate = cls.get_monthly_rate_for_age(maturity_age)

        bracket_table = []
        for _, _, rate, label in cls.AGE_BRACKETS:
            bracket_table.append({
                "bracket_label": label,
                "monthly_rate_pct": round(rate * 100.0, 4),
                "monthly_rate_per_thousand": round(rate * 1000.0, 3),
            })

        if maturity_age <= 70:
            status = "ESTÁNDAR"
            risk = "BAJO"
            insurable = True
            reqs = ["Declaración Personal de Salud (DPS) estándar."]
            alert = (
                f"Asegurabilidad normal. El deudor culminará el crédito a los {maturity_age} años, "
                "dentro del rango estándar del mercado hipotecario chileno."
            )
        elif maturity_age <= 75:
            status = "OBSERVACIÓN"
            risk = "MEDIO"
            insurable = True
            reqs = [
                "Declaración Personal de Salud (DPS) ampliada.",
                "Informe médico tratante si registra enfermedades preexistentes.",
            ]
            alert = (
                f"Atención por edad: El crédito finaliza a los {maturity_age} años. "
                "La prima de desgravamen se incrementará progresivamente y la aseguradora "
                "podría requerir exámenes preventivos según el monto financiado."
            )
        elif maturity_age <= 80:
            status = "RESTRICCIÓN_MÉDICA"
            risk = "ALTO"
            insurable = True
            reqs = [
                "Exámenes médicos presenciales obligatorios (perfil bioquímico, ECG de esfuerzo, hemograma).",
                "Evaluación de preexistencias y posible sobreprima actuarial (50% - 100% sobre tasa base).",
                "Facultad de la aseguradora para limitar coberturas de invalidez.",
            ]
            alert = (
                f"Restricción técnica: Edad al término del crédito de {maturity_age} años. "
                "El seguro exige exámenes rigurosos y existe riesgo de rechazo o aplicación de sobreprimas elevadas. "
                "Se recomienda considerar reducción de plazo o incorporar un codeudor solidario asegurable."
            )
        else:
            status = "INASEGURABLE"
            risk = "CRÍTICO"
            insurable = False
            reqs = [
                "Excede la edad máxima de cobertura (usualmente 75 u 80 años en pólizas colectivas de la banca chilena).",
                "Rechazo automático de póliza de desgravamen estándar.",
                "Exigencia indispensable de codeudor más joven para viabilizar el crédito.",
            ]
            alert = (
                f"OPERACIÓN INVIABLE BAJO POLÍTICA ESTÁNDAR: Con una edad al término de {maturity_age} años, "
                "el titular queda excluido de la póliza de seguro de desgravamen obligatoria. "
                "Para obtener financiamiento es indispensable reducir el plazo o estructurar la deuda con un codeudor."
            )

        return InsurabilityEvaluation(
            current_age=current_age,
            loan_term_years=loan_term_years,
            maturity_age=maturity_age,
            initial_monthly_rate=initial_rate,
            final_monthly_rate=final_rate,
            status=status,
            risk_level=risk,
            is_insurable=insurable,
            medical_requirements=reqs,
            regulatory_alert=alert,
            age_bracket_table=bracket_table,
        )

    @classmethod
    def generate_dynamic_schedule(
        cls,
        principal: float,
        annual_rate: float,
        months: int,
        start_age: int,
        fire_insurance_monthly_uf: float = 0.0,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """
        Genera una tabla de amortización francesa donde la tasa de seguro de desgravamen
        recalcula anualmente conforme el deudor avanza en edad durante el crédito.
        """
        r = FrenchAmortizer.monthly_interest_rate(annual_rate)
        d_f = FrenchAmortizer.calculate_financial_dividend(principal, annual_rate, months)

        schedule = []
        current_balance = principal
        total_life_ins = 0.0

        for month in range(1, months + 1):
            age_in_month = start_age + ((month - 1) // 12)
            monthly_life_rate = cls.get_monthly_rate_for_age(age_in_month)

            interest = current_balance * r
            if month == months:
                amortization = current_balance
                end_balance = 0.0
                d_f = amortization + interest
            else:
                amortization = d_f - interest
                end_balance = current_balance - amortization

            life_ins = current_balance * monthly_life_rate
            total_life_ins += life_ins
            fire_ins = fire_insurance_monthly_uf
            total_dividend = d_f + life_ins + fire_ins

            schedule.append({
                "month": month,
                "debtor_age": age_in_month,
                "start_balance_uf": round(current_balance, 4),
                "financial_dividend_uf": round(d_f, 4),
                "interest_uf": round(interest, 4),
                "amortization_uf": round(amortization, 4),
                "life_insurance_rate_monthly": round(monthly_life_rate, 6),
                "life_insurance_uf": round(life_ins, 4),
                "fire_insurance_uf": round(fire_ins, 4),
                "total_dividend_uf": round(total_dividend, 4),
                "end_balance_uf": round(max(0.0, end_balance), 4),
            })
            current_balance = end_balance

        flat_rate = 0.00028
        params_flat = MortgageParams(
            principal=principal,
            annual_rate=annual_rate,
            months_remaining=months,
            fire_insurance_monthly_uf=fire_insurance_monthly_uf,
            life_insurance_rate_monthly=flat_rate,
        )
        sched_flat = FrenchAmortizer.generate_schedule(params_flat)
        flat_total_life_ins = sum(r["life_insurance_uf"] for r in sched_flat)

        metrics = {
            "dynamic_total_life_insurance_uf": round(total_life_ins, 4),
            "flat_total_life_insurance_uf": round(flat_total_life_ins, 4),
            "insurance_cost_difference_uf": round(total_life_ins - flat_total_life_ins, 4),
        }

        return schedule, metrics
