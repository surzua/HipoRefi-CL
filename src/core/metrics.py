"""Evaluación cuantitativa de decisiones de refinanciamiento hipotecario."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class RefinanceDecision:
    npv_uf: float
    payback_months: Optional[int]
    monthly_savings_uf: float
    total_lifetime_savings_nominal_uf: float
    recommendation_flag: str  # "RECOMENDADO", "EVALUAR_CON_CAUTELA", "NO_CONVIENE"
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npv_uf": self.npv_uf,
            "payback_months": self.payback_months,
            "monthly_savings_uf": self.monthly_savings_uf,
            "total_lifetime_savings_nominal_uf": self.total_lifetime_savings_nominal_uf,
            "recommendation_flag": self.recommendation_flag,
            "rationale": self.rationale,
        }


class RefinanceAnalyzer:
    DEFAULT_ANNUAL_DISCOUNT_RATE = 0.025  # 2.5% anual real en UF (costo de oportunidad estándar)

    @classmethod
    def evaluate(
        cls,
        current_schedule: List[Dict[str, Any]],
        new_schedule: List[Dict[str, Any]],
        upfront_costs_uf: float,
        financed_costs: bool = False,
        annual_discount_rate: float = DEFAULT_ANNUAL_DISCOUNT_RATE,
    ) -> RefinanceDecision:
        """
        Compara los flujos de dividendos (crédito actual vs. nuevo) y calcula:
        - Valor Presente Neto (VPN / NPV) en UF
        - Payback dinámico descontado
        - Ahorro mensual inicial en UF
        - Ahorro nominal total durante la vida del crédito
        - Clasificación y recomendación patrimonial
        """
        n_current = len(current_schedule)
        n_new = len(new_schedule)
        max_months = max(n_current, n_new)

        if max_months == 0:
            return RefinanceDecision(
                npv_uf=0.0,
                payback_months=None,
                monthly_savings_uf=0.0,
                total_lifetime_savings_nominal_uf=0.0,
                recommendation_flag="NO_CONVIENE",
                rationale="No se proporcionaron tablas de desarrollo válidas para comparar.",
            )

        monthly_discount = (1.0 + annual_discount_rate) ** (1.0 / 12.0) - 1.0

        # Flujos mensuales alineados
        flows_current = np.zeros(max_months)
        flows_new = np.zeros(max_months)

        for i, item in enumerate(current_schedule):
            flows_current[i] = item["total_dividend_uf"]

        for i, item in enumerate(new_schedule):
            flows_new[i] = item["total_dividend_uf"]

        # Delta mensual de flujo de caja (positivo indica menor dividendo en la nueva opción)
        monthly_diff = flows_current - flows_new

        # Factores de descuento mes a mes
        discount_factors = np.array([(1.0 + monthly_discount) ** (-t) for t in range(1, max_months + 1)])

        if financed_costs:
            # Los costos operacionales ya fueron agregados al capital del nuevo crédito
            npv = float(np.sum(monthly_diff * discount_factors))
            cumulative_disc_savings = np.cumsum(monthly_diff * discount_factors)
            payback_months = None
            for month_idx, cum_save in enumerate(cumulative_disc_savings):
                if cum_save >= upfront_costs_uf:
                    payback_months = month_idx + 1
                    break
        else:
            # Costos operacionales pagados al contado en t = 0
            npv = float(-upfront_costs_uf + np.sum(monthly_diff * discount_factors))
            cumulative_disc_savings = np.cumsum(monthly_diff * discount_factors)
            payback_months = None
            for month_idx, cum_save in enumerate(cumulative_disc_savings):
                if cum_save >= upfront_costs_uf:
                    payback_months = month_idx + 1
                    break

        nominal_savings = float(np.sum(monthly_diff))
        initial_monthly_saving = float(monthly_diff[0]) if len(monthly_diff) > 0 else 0.0

        # Evaluación heurística de decisión patrimonial
        if npv > 20.0 and payback_months is not None and payback_months <= 36:
            flag = "RECOMENDADO"
            rationale = (
                f"El refinanciamiento genera una ganancia patrimonial neta (VPN) de {npv:.2f} UF. "
                f"El costo de cambio se recupera en {payback_months} meses y el deudor ahorra "
                f"{initial_monthly_saving:.2f} UF mensuales desde el primer dividendo."
            )
        elif npv > 0.0:
            flag = "EVALUAR_CON_CAUTELA"
            payback_str = f"{payback_months} meses" if payback_months else f"> {max_months} meses"
            rationale = (
                f"El VPN es positivo ({npv:.2f} UF), pero el tiempo de recuperación es moderado a prolongado "
                f"({payback_str}). Si se planea vender la propiedad o prepagar a corto plazo, "
                "los costos de cierre podrían no compensarse."
            )
        else:
            flag = "NO_CONVIENE"
            rationale = (
                f"La operación destruye valor patrimonial (VPN = {npv:.2f} UF). "
                "El diferencial de tasa no logra compensar los costos operacionales y de prepago."
            )

        return RefinanceDecision(
            npv_uf=round(npv, 2),
            payback_months=payback_months,
            monthly_savings_uf=round(initial_monthly_saving, 2),
            total_lifetime_savings_nominal_uf=round(nominal_savings, 2),
            recommendation_flag=flag,
            rationale=rationale,
        )


# ============================================================================
# Comparador Head-to-Head (Hito 10)
# ============================================================================

@dataclass
class HeadToHeadSideResult:
    bank_name: str
    annual_rate_pct: float
    term_years: int
    monthly_dividend_uf: float
    monthly_savings_uf: float
    total_cost_uf: float
    total_interest_uf: float
    npv_uf: float
    payback_months: Optional[int]
    recommendation_flag: str
    schedule_summary: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_name": self.bank_name,
            "annual_rate_pct": round(self.annual_rate_pct, 2),
            "term_years": self.term_years,
            "monthly_dividend_uf": round(self.monthly_dividend_uf, 3),
            "monthly_savings_uf": round(self.monthly_savings_uf, 3),
            "total_cost_uf": round(self.total_cost_uf, 2),
            "total_interest_uf": round(self.total_interest_uf, 2),
            "npv_uf": round(self.npv_uf, 2),
            "payback_months": self.payback_months,
            "recommendation_flag": self.recommendation_flag,
        }


@dataclass
class HeadToHeadComparisonResult:
    current_balance_uf: float
    current_dividend_uf: float
    current_rate_pct: float
    current_months: int
    bank_a: HeadToHeadSideResult
    bank_b: HeadToHeadSideResult
    npv_diff_uf: float  # A - B (positivo: A genera más VPN)
    monthly_dividend_diff_uf: float  # B - A (positivo: A tiene cuota menor)
    total_cost_diff_uf: float  # B - A (positivo: A paga menos en total)
    winner_bank: str  # Nombre del ganador o "EMPATE TÉCNICO"
    verdict_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_balance_uf": round(self.current_balance_uf, 2),
            "current_dividend_uf": round(self.current_dividend_uf, 3),
            "current_rate_pct": round(self.current_rate_pct, 2),
            "current_months": self.current_months,
            "bank_a": self.bank_a.to_dict(),
            "bank_b": self.bank_b.to_dict(),
            "npv_diff_uf": round(self.npv_diff_uf, 2),
            "monthly_dividend_diff_uf": round(self.monthly_dividend_diff_uf, 3),
            "total_cost_diff_uf": round(self.total_cost_diff_uf, 2),
            "winner_bank": self.winner_bank,
            "verdict_rationale": self.verdict_rationale,
        }


class HeadToHeadComparator:
    """Comparador cuantitativo Head-to-Head lado a lado entre dos instituciones u ofertas (Hito 10)."""

    @classmethod
    def compare(
        cls,
        current_schedule: List[Dict[str, Any]],
        current_balance_uf: float,
        current_annual_rate_pct: float,
        current_months: int,
        bank_a_name: str,
        bank_a_schedule: List[Dict[str, Any]],
        bank_a_rate_pct: float,
        bank_a_term_years: int,
        bank_a_upfront_costs_uf: float,
        bank_b_name: str,
        bank_b_schedule: List[Dict[str, Any]],
        bank_b_rate_pct: float,
        bank_b_term_years: int,
        bank_b_upfront_costs_uf: float,
        financed_costs: bool = False,
        annual_discount_rate: float = 0.025,
    ) -> HeadToHeadComparisonResult:
        """
        Ejecuta la evaluación cuantitativa simultánea de dos ofertas frente al crédito actual
        y contrasta directamente ambas alternativas determinando la ganadora patrimonial.
        """
        curr_div = current_schedule[0]["total_dividend_uf"] if current_schedule else 0.0

        eval_a = RefinanceAnalyzer.evaluate(
            current_schedule=current_schedule,
            new_schedule=bank_a_schedule,
            upfront_costs_uf=bank_a_upfront_costs_uf,
            financed_costs=financed_costs,
            annual_discount_rate=annual_discount_rate,
        )

        eval_b = RefinanceAnalyzer.evaluate(
            current_schedule=current_schedule,
            new_schedule=bank_b_schedule,
            upfront_costs_uf=bank_b_upfront_costs_uf,
            financed_costs=financed_costs,
            annual_discount_rate=annual_discount_rate,
        )

        div_a = bank_a_schedule[0]["total_dividend_uf"] if bank_a_schedule else 0.0
        div_b = bank_b_schedule[0]["total_dividend_uf"] if bank_b_schedule else 0.0

        cost_a = sum(r["total_dividend_uf"] for r in bank_a_schedule)
        cost_b = sum(r["total_dividend_uf"] for r in bank_b_schedule)

        int_a = sum(r["interest_uf"] for r in bank_a_schedule)
        int_b = sum(r["interest_uf"] for r in bank_b_schedule)

        side_a = HeadToHeadSideResult(
            bank_name=bank_a_name,
            annual_rate_pct=bank_a_rate_pct,
            term_years=bank_a_term_years,
            monthly_dividend_uf=div_a,
            monthly_savings_uf=eval_a.monthly_savings_uf,
            total_cost_uf=cost_a,
            total_interest_uf=int_a,
            npv_uf=eval_a.npv_uf,
            payback_months=eval_a.payback_months,
            recommendation_flag=eval_a.recommendation_flag,
            schedule_summary=bank_a_schedule[:12],
        )

        side_b = HeadToHeadSideResult(
            bank_name=bank_b_name,
            annual_rate_pct=bank_b_rate_pct,
            term_years=bank_b_term_years,
            monthly_dividend_uf=div_b,
            monthly_savings_uf=eval_b.monthly_savings_uf,
            total_cost_uf=cost_b,
            total_interest_uf=int_b,
            npv_uf=eval_b.npv_uf,
            payback_months=eval_b.payback_months,
            recommendation_flag=eval_b.recommendation_flag,
            schedule_summary=bank_b_schedule[:12],
        )

        npv_diff = eval_a.npv_uf - eval_b.npv_uf
        monthly_div_diff = div_b - div_a  # positivo si A tiene menor dividendo
        total_cost_diff = cost_b - cost_a  # positivo si A es más barato

        if abs(npv_diff) < 0.5 and abs(monthly_div_diff) < 0.05:
            winner = "EMPATE TÉCNICO"
            rationale = (
                f"Ambas entidades presentan condiciones equivalentes (diferencia de VPN de {abs(npv_diff):.2f} UF). "
                "Se recomienda negociar exención o subsidio de gastos operacionales o comparar comisiones de cuenta corriente."
            )
        elif npv_diff > 0:
            winner = bank_a_name
            rationale = (
                f"🏆 **{bank_a_name}** es la opción ganadora con una ventaja patrimonial neta de **+{npv_diff:.2f} UF** de VPN "
                f"frente a {bank_b_name}. "
                + (f"Además su dividendo mensual es {monthly_div_diff:.2f} UF más económico." if monthly_div_diff > 0 else
                   f"Aunque su dividendo es {-monthly_div_diff:.2f} UF mayor, amortiza capital más velozmente generando menor costo financiero total.")
            )
        else:
            winner = bank_b_name
            rationale = (
                f"🏆 **{bank_b_name}** es la opción ganadora con una ventaja patrimonial neta de **+{-npv_diff:.2f} UF** de VPN "
                f"frente a {bank_a_name}. "
                + (f"Además su dividendo mensual es {-monthly_div_diff:.2f} UF más económico." if monthly_div_diff < 0 else
                   f"Aunque su dividendo es {monthly_div_diff:.2f} UF mayor, compensa ampliamente con menor interés total pagado.")
            )

        return HeadToHeadComparisonResult(
            current_balance_uf=current_balance_uf,
            current_dividend_uf=curr_div,
            current_rate_pct=current_annual_rate_pct,
            current_months=current_months,
            bank_a=side_a,
            bank_b=side_b,
            npv_diff_uf=npv_diff,
            monthly_dividend_diff_uf=monthly_div_diff,
            total_cost_diff_uf=total_cost_diff,
            winner_bank=winner,
            verdict_rationale=rationale,
        )
