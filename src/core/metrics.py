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
