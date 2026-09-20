"""Modelamiento y simulación de cotizaciones de créditos hipotecarios bancarios en Chile."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from src.core.amortizer import FrenchAmortizer, MortgageParams


@dataclass
class BankQuote:
    bank_id: str
    bank_name: str
    loan_type: str
    term_years: int
    annual_rate_pct: float
    monthly_financial_dividend_uf: float
    monthly_total_dividend_uf: float
    life_insurance_uf: float
    fire_insurance_uf: float
    estimated_cae_pct: float
    spread_vs_market_pct: float
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_id": self.bank_id,
            "bank_name": self.bank_name,
            "loan_type": self.loan_type,
            "term_years": self.term_years,
            "annual_rate_pct": round(self.annual_rate_pct, 2),
            "monthly_financial_dividend_uf": round(self.monthly_financial_dividend_uf, 3),
            "monthly_total_dividend_uf": round(self.monthly_total_dividend_uf, 3),
            "life_insurance_uf": round(self.life_insurance_uf, 3),
            "fire_insurance_uf": round(self.fire_insurance_uf, 3),
            "estimated_cae_pct": round(self.estimated_cae_pct, 2),
            "spread_vs_market_pct": round(self.spread_vs_market_pct, 2),
            "source": self.source,
        }


class BankSimulatorProvider:
    """
    Proveedor y simulador de cotizaciones de la banca chilena.
    Combina perfiles de spreads comerciales con cálculo cuantitativo exacto.
    """

    # Perfiles comerciales estándar de bancos y mutuarias en Chile
    # Tasa = Tasa Base CMF/Mercado + Spread de entidad
    BANK_PROFILES = [
        {
            "id": "bchile",
            "name": "Banco de Chile",
            "loan_types": ["Tasa Fija", "Tasa Mixta (3 años fija)"],
            "spread_pct": -0.30,  # -30 bps respecto al promedio
            "fire_rate_monthly": 0.00014,
            "life_rate_monthly": 0.00028,
        },
        {
            "id": "santander",
            "name": "Banco Santander",
            "loan_types": ["Tasa Fija", "Tasa Mixta (5 años fija)"],
            "spread_pct": -0.25,
            "fire_rate_monthly": 0.00015,
            "life_rate_monthly": 0.00027,
        },
        {
            "id": "bci",
            "name": "BCI",
            "loan_types": ["Tasa Fija"],
            "spread_pct": -0.28,
            "fire_rate_monthly": 0.00014,
            "life_rate_monthly": 0.00028,
        },
        {
            "id": "scotiabank",
            "name": "Scotiabank",
            "loan_types": ["Tasa Fija"],
            "spread_pct": -0.24,
            "fire_rate_monthly": 0.00016,
            "life_rate_monthly": 0.00029,
        },
        {
            "id": "bancoestado",
            "name": "BancoEstado",
            "loan_types": ["Tasa Fija (Crédito Habita)"],
            "spread_pct": -0.15,
            "fire_rate_monthly": 0.00015,
            "life_rate_monthly": 0.00026,
        },
        {
            "id": "itau",
            "name": "Banco Itaú",
            "loan_types": ["Tasa Fija"],
            "spread_pct": -0.20,
            "fire_rate_monthly": 0.00015,
            "life_rate_monthly": 0.00028,
        },
        {
            "id": "mutuaria_security",
            "name": "Mutuaria Security",
            "loan_types": ["Mutuo Endosable Fijo"],
            "spread_pct": -0.45,  # Mutuarias típicamente más agresivas en tasa
            "fire_rate_monthly": 0.00013,
            "life_rate_monthly": 0.00025,
        },
    ]

    def __init__(self, base_market_rate_pct: float = 4.65):
        self.base_market_rate_pct = base_market_rate_pct

    def simulate_bank_quote(
        self,
        bank_profile: Dict[str, Any],
        principal_uf: float,
        term_years: int,
        property_value_uf: Optional[float] = None,
        loan_type: Optional[str] = None,
    ) -> BankQuote:
        """Calcula una cotización completa con seguros para una entidad específica."""
        property_val = property_value_uf or (principal_uf / 0.80)  # LTV estándar 80%
        months = term_years * 12

        # Tasa nominal anual ofrecida por la entidad
        rate_pct = max(2.5, self.base_market_rate_pct + bank_profile["spread_pct"])
        rate_decimal = rate_pct / 100.0

        # Seguros del primer período
        fire_ins_uf = property_val * 0.70 * bank_profile["fire_rate_monthly"]  # 70% valor construcción
        life_rate = bank_profile["life_rate_monthly"]

        params = MortgageParams(
            principal=principal_uf,
            annual_rate=rate_decimal,
            months_remaining=months,
            fire_insurance_monthly_uf=fire_ins_uf,
            life_insurance_rate_monthly=life_rate,
        )

        schedule = FrenchAmortizer.generate_schedule(params)
        first_month = schedule[0]

        # CAE aproximada: incorpora la tasa del crédito más el costo de seguros
        annual_insurance_pct = ((fire_ins_uf + first_month["life_insurance_uf"]) * 12 / principal_uf) * 100.0
        estimated_cae = rate_pct + annual_insurance_pct

        return BankQuote(
            bank_id=bank_profile["id"],
            bank_name=bank_profile["name"],
            loan_type=loan_type or bank_profile["loan_types"][0],
            term_years=term_years,
            annual_rate_pct=rate_pct,
            monthly_financial_dividend_uf=first_month["financial_dividend_uf"],
            monthly_total_dividend_uf=first_month["total_dividend_uf"],
            life_insurance_uf=first_month["life_insurance_uf"],
            fire_insurance_uf=first_month["fire_insurance_uf"],
            estimated_cae_pct=estimated_cae,
            spread_vs_market_pct=bank_profile["spread_pct"],
            source="SIMULATOR_ENGINE",
        )

    def simulate_all_banks(
        self,
        principal_uf: float,
        term_years: int,
        property_value_uf: Optional[float] = None
    ) -> List[BankQuote]:
        """Simula y ordena cotizaciones para todas las entidades bancarias del mercado."""
        quotes = []
        for profile in self.BANK_PROFILES:
            quote = self.simulate_bank_quote(
                bank_profile=profile,
                principal_uf=principal_uf,
                term_years=term_years,
                property_value_uf=property_value_uf,
            )
            quotes.append(quote)

        # Ordenar por dividendo total mensual más conveniente
        quotes.sort(key=lambda q: q.monthly_total_dividend_uf)
        return quotes
