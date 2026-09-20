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


class GermanAmortizer:
    """
    Motor de amortización alemana (cuota decreciente con amortización fija de capital).
    Utilizado en Chile por ciertas instituciones (ej. líneas específicas de BancoEstado)
    donde el deudor abona una cuota de capital constante cada mes y el interés disminuye con el saldo.
    """

    @staticmethod
    def monthly_interest_rate(annual_rate: float) -> float:
        """
        Calcula la tasa mensual efectiva bajo convención chilena estándar:
        r = (1 + i_a)^(1/12) - 1
        """
        return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0

    @classmethod
    def calculate_fixed_principal_amortization(cls, principal: float, months: int) -> float:
        """Calcula la amortización constante mensual de capital en UF."""
        if months <= 0:
            raise ValueError("El número de meses debe ser positivo.")
        if principal < 0:
            raise ValueError("El saldo de capital no puede ser negativo.")
        if principal == 0:
            return 0.0
        return principal / months

    @classmethod
    def calculate_initial_financial_dividend(cls, principal: float, annual_rate: float, months: int) -> float:
        """Calcula el dividendo financiero inicial (más alto del período) en UF."""
        if principal <= 0 or months <= 0:
            return 0.0
        fixed_amort = cls.calculate_fixed_principal_amortization(principal, months)
        r = cls.monthly_interest_rate(annual_rate)
        return fixed_amort + (principal * r)

    @classmethod
    def generate_schedule(cls, params: MortgageParams) -> List[Dict[str, Any]]:
        """
        Genera la tabla de desarrollo mes a mes para el sistema alemán:
        - Amortización de capital constante = Saldo Inicial / N
        - Intereses devengados decrecientes mes a mes
        - Dividendo decreciente
        - Seguros correspondientes
        """
        if params.months_remaining <= 0:
            raise ValueError("El plazo en meses debe ser mayor a 0.")
        if params.principal <= 0:
            return []

        r = cls.monthly_interest_rate(params.annual_rate)
        fixed_amort = params.principal / params.months_remaining

        schedule = []
        current_balance = params.principal

        for month in range(1, params.months_remaining + 1):
            interest = current_balance * r

            if month == params.months_remaining:
                amortization = current_balance
                end_balance = 0.0
            else:
                amortization = fixed_amort
                end_balance = current_balance - amortization

            d_f = amortization + interest
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

    @classmethod
    def compare_french_vs_german(cls, params: MortgageParams) -> Dict[str, Any]:
        """
        Compara los dos sistemas de amortización bajo idénticas condiciones de capital, tasa y plazo.
        """
        sched_french = FrenchAmortizer.generate_schedule(params)
        sched_german = cls.generate_schedule(params)

        french_total_interest = sum(r["interest_uf"] for r in sched_french)
        german_total_interest = sum(r["interest_uf"] for r in sched_german)
        interest_savings_uf = french_total_interest - german_total_interest

        french_initial_div = sched_french[0]["total_dividend_uf"] if sched_french else 0.0
        german_initial_div = sched_german[0]["total_dividend_uf"] if sched_german else 0.0
        german_final_div = sched_german[-1]["total_dividend_uf"] if sched_german else 0.0

        return {
            "french_initial_total_dividend_uf": round(french_initial_div, 4),
            "german_initial_total_dividend_uf": round(german_initial_div, 4),
            "german_final_total_dividend_uf": round(german_final_div, 4),
            "initial_dividend_diff_uf": round(german_initial_div - french_initial_div, 4),
            "french_total_interest_uf": round(french_total_interest, 4),
            "german_total_interest_uf": round(german_total_interest, 4),
            "interest_savings_uf": round(interest_savings_uf, 4),
            "interest_savings_pct": round((interest_savings_uf / french_total_interest * 100.0) if french_total_interest > 0 else 0.0, 2),
            "french_total_cost_uf": round(sum(r["total_dividend_uf"] for r in sched_french), 4),
            "german_total_cost_uf": round(sum(r["total_dividend_uf"] for r in sched_german), 4),
        }

