"""Servicio orquestador de datos de mercado, sincronización macro y cotizaciones bancarias."""

import os
import requests
from typing import Dict, Any, List, Optional
from datetime import date

from src.data.market_store import MarketDataStore
from src.scrapers.bcch_client import CentralBankChileClient
from src.scrapers.cmf_client import CMFClient
from src.scrapers.bank_simulators import BankSimulatorProvider, BankQuote
from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator
from src.core.metrics import RefinanceAnalyzer, RefinanceDecision


class MarketDataService:
    """
    Fachada centralizada de datos de mercado.
    Administra la persistencia en DuckDB, la sincronización con fuentes externas
    (Banco Central, CMF) y la generación de ofertas de refinanciamiento.
    """

    def __init__(self, store: Optional[MarketDataStore] = None):
        self.store = store or MarketDataStore()
        self.bcch_client = CentralBankChileClient()
        self.cmf_client = CMFClient()

        # Si DuckDB está vacío, sembramos datos base de partida
        if self.store.get_latest_uf() is None:
            self.store.seed_default_market_data()

    DEFAULT_UF_FALLBACK = 40942.74

    def fetch_public_uf(self) -> Optional[float]:
        """
        Consulta el valor de la UF en tiempo real desde la API pública abierta de indicadores.
        Guarda el valor en DuckDB si la consulta es exitosa.
        """
        try:
            resp = requests.get("https://mindicador.cl/api/uf", timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                serie = data.get("serie", [])
                if serie:
                    latest = serie[0]
                    raw_val = float(latest["valor"])
                    raw_date = str(latest["fecha"]).split("T")[0]

                    self.store.save_macro_series([
                        {
                            "date": raw_date,
                            "series_code": CentralBankChileClient.SERIES_UF_DAILY,
                            "series_name": "Unidad de Fomento (UF)",
                            "value": raw_val,
                            "unit": "CLP",
                            "source": "MINDICADOR_PUBLIC_API",
                        }
                    ])
                    return raw_val
        except Exception:
            pass
        return None

    def sync_from_central_bank(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Intenta sincronizar indicadores clave desde la API oficial del Banco Central.
        Si las credenciales no están configuradas, actualiza la UF vía API pública.
        """
        if not self.bcch_client.user or not self.bcch_client.password:
            public_uf = self.fetch_public_uf()
            if public_uf is not None:
                return {
                    "status": "SUCCESS",
                    "source": "MINDICADOR_PUBLIC_API",
                    "uf": public_uf,
                    "message": f"UF actualizada en tiempo real: ${public_uf:,.2f} CLP (sin requerir credenciales BCCh).",
                }
            return {
                "status": "SKIPPED",
                "message": "Credenciales del Banco Central no configuradas. Operando con catálogo local en DuckDB.",
            }

        today = date.today()
        first_date = today.replace(day=1).isoformat()
        last_date = today.isoformat()

        synced_records = []
        try:
            # 1. UF Diaria
            uf_series = self.bcch_client.fetch_series(
                CentralBankChileClient.SERIES_UF_DAILY, first_date, last_date
            )
            for obs in uf_series.get("obs", []):
                synced_records.append({
                    "date": obs.get("indexDateString"),
                    "series_code": CentralBankChileClient.SERIES_UF_DAILY,
                    "series_name": "Unidad de Fomento (UF)",
                    "value": float(obs.get("value")),
                    "unit": "CLP",
                    "source": "BCCH_API",
                })

            if synced_records:
                saved = self.store.save_macro_series(synced_records)
                return {"status": "SUCCESS", "records_saved": saved}
            return {"status": "NO_DATA", "message": "No se encontraron nuevas observaciones."}

        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def get_current_uf(self, force_refresh: bool = False) -> float:
        """
        Obtiene el valor de la UF más reciente disponible.
        Si el valor almacenado es obsoleto o menor a 39.000, consulta la API en vivo.
        """
        uf = self.store.get_latest_uf()
        if uf is None or uf < 39000.0 or force_refresh:
            live_uf = self.fetch_public_uf()
            if live_uf is not None:
                return live_uf
            if uf is None or uf < 39000.0:
                uf = self.DEFAULT_UF_FALLBACK
        return uf

    def convert_uf_to_clp(self, amount_uf: float) -> float:
        """Convierte un monto en UF a pesos chilenos al valor vigente."""
        return amount_uf * self.get_current_uf()

    def convert_clp_to_uf(self, amount_clp: float) -> float:
        """Convierte pesos chilenos a UF."""
        return amount_clp / self.get_current_uf()

    def get_market_overview(self) -> Dict[str, Any]:
        """Retorna un panorama macroeconómico y tasas hipotecarias promedio."""
        latest_rates = self.store.get_latest_macro_rates()
        cmf_benchmarks = self.cmf_client.get_market_benchmarks()

        return {
            "uf_current": self.get_current_uf(),
            "latest_macro_rates": latest_rates,
            "cmf_benchmarks": {
                k: {
                    "segment": v.segment,
                    "average_rate_pct": v.average_rate_pct,
                    "min_rate_pct": v.min_rate_pct,
                    "max_rate_pct": v.max_rate_pct,
                }
                for k, v in cmf_benchmarks.items()
            },
        }

    def get_bank_quotes(
        self,
        principal_uf: float,
        term_years: int,
        property_value_uf: Optional[float] = None
    ) -> List[BankQuote]:
        """Simula cotizaciones para todos los bancos comerciales."""
        # Obtenemos la tasa de referencia de la CMF o DuckDB
        avg_rate = self.cmf_client.get_average_rate("bancos")
        simulator = BankSimulatorProvider(base_market_rate_pct=avg_rate)
        return simulator.simulate_all_banks(
            principal_uf=principal_uf,
            term_years=term_years,
            property_value_uf=property_value_uf,
        )

    def evaluate_refinance_against_market(
        self,
        current_balance_uf: float,
        current_annual_rate: float,
        months_remaining: int,
        current_total_dividend_uf: Optional[float] = None,
        fire_insurance_uf: float = 0.0,
        life_insurance_rate: float = 0.00028,
        term_years_target: Optional[int] = None,
        finance_costs: bool = False,
    ) -> Dict[str, Any]:
        """
        Evalúa integralmente el crédito actual contra las mejores opciones disponibles
        en el mercado financiero chileno.
        """
        target_term = term_years_target or max(5, round(months_remaining / 12))
        quotes = self.get_bank_quotes(principal_uf=current_balance_uf, term_years=target_term)

        # Generar tabla del crédito actual
        params_current = MortgageParams(
            principal=current_balance_uf,
            annual_rate=current_annual_rate,
            months_remaining=months_remaining,
            fire_insurance_monthly_uf=fire_insurance_uf,
            life_insurance_rate_monthly=life_insurance_rate,
        )
        current_schedule = FrenchAmortizer.generate_schedule(params_current)

        # Gastos operacionales de portabilidad según Ley 21.236
        costs = SwitchingCostCalculator.calculate_total_costs(
            balance_uf=current_balance_uf,
            current_annual_rate=current_annual_rate,
        )

        opportunities = []
        for q in quotes:
            new_rate_decimal = q.annual_rate_pct / 100.0
            new_principal = (
                current_balance_uf + costs.total_cost_uf if finance_costs else current_balance_uf
            )

            params_new = MortgageParams(
                principal=new_principal,
                annual_rate=new_rate_decimal,
                months_remaining=target_term * 12,
                fire_insurance_monthly_uf=q.fire_insurance_uf,
                life_insurance_rate_monthly=0.00028,
            )
            new_schedule = FrenchAmortizer.generate_schedule(params_new)

            decision = RefinanceAnalyzer.evaluate(
                current_schedule=current_schedule,
                new_schedule=new_schedule,
                upfront_costs_uf=costs.total_cost_uf,
                financed_costs=finance_costs,
            )

            opportunities.append({
                "bank_quote": q.to_dict(),
                "evaluation": decision.to_dict(),
                "monthly_dividend_new_uf": q.monthly_total_dividend_uf,
                "monthly_dividend_new_clp": self.convert_uf_to_clp(q.monthly_total_dividend_uf),
                "switching_costs_uf": costs.total_cost_uf,
                "switching_costs_clp": self.convert_uf_to_clp(costs.total_cost_uf),
            })

        # Ordenar por mayor VPN generado para el cliente
        opportunities.sort(key=lambda x: x["evaluation"]["npv_uf"], reverse=True)

        return {
            "current_loan": {
                "balance_uf": current_balance_uf,
                "balance_clp": self.convert_uf_to_clp(current_balance_uf),
                "annual_rate_pct": round(current_annual_rate * 100, 2),
                "months_remaining": months_remaining,
                "current_dividend_uf": (
                    current_total_dividend_uf
                    if current_total_dividend_uf
                    else current_schedule[0]["total_dividend_uf"]
                ),
            },
            "switching_costs_breakdown": costs.to_dict(),
            "best_opportunity": opportunities[0] if opportunities else None,
            "all_opportunities": opportunities,
        }
