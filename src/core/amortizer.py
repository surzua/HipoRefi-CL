"""Motor de amortización francesa para créditos hipotecarios en Chile."""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class MortgageParams:
    principal: float  # Saldo insoluto o monto inicial en UF
    annual_rate: float  # Tasa anual nominal o efectiva anual (ej: 0.045 para 4.5%)
    months_remaining: int  # Plazo restante en meses
    fire_insurance_monthly_uf: float = 0.0  # Monto mensual en UF (incendio/sismo)
    life_insurance_rate_monthly: float = 0.00028  # Prima por mil mensual sobre saldo insoluto


class FrenchAmortizer:
    @staticmethod
    def monthly_interest_rate(annual_rate: float) -> float:
        """
        Calcula la tasa mensual efectiva bajo convención chilena estándar:
        r = (1 + i_a)^(1/12) - 1
        """
        return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0

    @classmethod
    def calculate_financial_dividend(cls, principal: float, annual_rate: float, months: int) -> float:
        """Calcula el dividendo financiero puro (sin seguros) en UF mediante fórmula francesa."""
        if months <= 0:
            raise ValueError("El número de meses debe ser positivo.")
        if principal < 0:
            raise ValueError("El saldo de capital no puede ser negativo.")
        if principal == 0:
            return 0.0

        r = cls.monthly_interest_rate(annual_rate)
        if r == 0:
            return principal / months
        factor = (1.0 + r) ** months
        return principal * (r * factor) / (factor - 1.0)

    @classmethod
    def generate_schedule(cls, params: MortgageParams) -> List[Dict[str, Any]]:
        """
        Genera la tabla de desarrollo mes a mes con desglose completo:
        - Saldo inicial
        - Dividendo financiero
        - Interés devengado
        - Amortización de capital
        - Seguro de desgravamen
        - Seguro de incendio y sismo
        - Dividendo total
        - Saldo final
        """
        if params.months_remaining <= 0:
            raise ValueError("El plazo en meses debe ser mayor a 0.")
        if params.principal <= 0:
            return []

        r = cls.monthly_interest_rate(params.annual_rate)
        d_f = cls.calculate_financial_dividend(params.principal, params.annual_rate, params.months_remaining)

        schedule = []
        current_balance = params.principal

        for month in range(1, params.months_remaining + 1):
            interest = current_balance * r
            amortization = d_f - interest

            # Ajuste de cierre para el último mes para absorber residuos de redondeo
            if month == params.months_remaining:
                amortization = current_balance
                d_f = amortization + interest
                end_balance = 0.0
            else:
                end_balance = current_balance - amortization

            # Seguros del período
            life_ins = current_balance * params.life_insurance_rate_monthly
            fire_ins = params.fire_insurance_monthly_uf
            total_dividend = d_f + life_ins + fire_ins

            schedule.append({
                "month": month,
                "start_balance_uf": round(current_balance, 4),
                "financial_dividend_uf": round(d_f, 4),
                "interest_uf": round(interest, 4),
                "amortization_uf": round(amortization, 4),
                "life_insurance_uf": round(life_ins, 4),
                "fire_insurance_uf": round(fire_ins, 4),
                "total_dividend_uf": round(total_dividend, 4),
                "end_balance_uf": round(max(0.0, end_balance), 4),
            })
            current_balance = end_balance

        return schedule
