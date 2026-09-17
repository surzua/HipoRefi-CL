"""Modelamiento de costos operacionales de refinanciamiento en Chile (Ley 21.236, DL 3475, LGB Art. 100)."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class SwitchingCostBreakdown:
    prepayment_penalty_uf: float  # Comisión de prepago (máx 1.5 meses de intereses)
    appraisal_uf: float          # Tasación
    title_deed_uf: float         # Estudio de títulos
    notary_uf: float             # Notaría (con arancel regulado Ley 21.236)
    cbr_uf: float                # Conservador de Bienes Raíces (arancel 50% por subrogación)
    stamp_tax_uf: float          # Impuesto D.L. 3475 (0 UF si no hay capital fresco adicional)
    total_cost_uf: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "prepayment_penalty_uf": round(self.prepayment_penalty_uf, 2),
            "appraisal_uf": round(self.appraisal_uf, 2),
            "title_deed_uf": round(self.title_deed_uf, 2),
            "notary_uf": round(self.notary_uf, 2),
            "cbr_uf": round(self.cbr_uf, 2),
            "stamp_tax_uf": round(self.stamp_tax_uf, 2),
            "total_cost_uf": round(self.total_cost_uf, 2),
        }


class SwitchingCostCalculator:
    # Parámetros medios de mercado chileno (en UF)
    BASE_APPRAISAL_UF = 3.0
    BASE_TITLE_DEED_UF = 4.0
    BASE_NOTARY_UF = 1.0

    @classmethod
    def calculate_cbr_fee(cls, balance_uf: float) -> float:
        """
        Arancel estimado CBR con descuento del 50% por Ley de Portabilidad Financiera (subrogación).
        Aproximación empírica y regulatoria: ~0.1% del valor de hipoteca, con cota inferior 1.5 UF y tope ~12 UF.
        """
        fee = balance_uf * 0.0010
        return min(max(1.5, fee), 12.0)

    @classmethod
    def calculate_prepayment_penalty(cls, balance_uf: float, current_annual_rate: float) -> float:
        """
        Comisión de prepago según Ley General de Bancos Art. 100:
        Para créditos de vivienda no superiores a 5.000 UF, máximo 1.5 meses de intereses devengados
        sobre el capital que se prepaga.
        """
        monthly_r = (1.0 + current_annual_rate) ** (1.0 / 12.0) - 1.0
        return 1.5 * (balance_uf * monthly_r)

    @classmethod
    def calculate_total_costs(
        cls,
        balance_uf: float,
        current_annual_rate: float,
        additional_cash_uf: float = 0.0,
        appraisal_uf: float = BASE_APPRAISAL_UF,
        title_deed_uf: float = BASE_TITLE_DEED_UF,
        notary_uf: float = BASE_NOTARY_UF,
    ) -> SwitchingCostBreakdown:
        """
        Calcula el gasto de cierre total en UF para migrar el crédito.
        
        Bajo el D.L. 3475:
        - Si el crédito refinancia exclusivamente el saldo deudor anterior, está 100% EXENTO del impuesto
          de timbres y estampillas.
        - Si se solicita capital adicional ("fines generales"), solo el saldo marginal tributa (máx 0.8%).
        """
        penalty = cls.calculate_prepayment_penalty(balance_uf, current_annual_rate)
        cbr = cls.calculate_cbr_fee(balance_uf)

        # Impuesto de timbres y estampillas
        stamp_tax = additional_cash_uf * 0.008 if additional_cash_uf > 0 else 0.0

        total = penalty + appraisal_uf + title_deed_uf + notary_uf + cbr + stamp_tax

        return SwitchingCostBreakdown(
            prepayment_penalty_uf=penalty,
            appraisal_uf=appraisal_uf,
            title_deed_uf=title_deed_uf,
            notary_uf=notary_uf,
            cbr_uf=cbr,
            stamp_tax_uf=stamp_tax,
            total_cost_uf=total,
        )
