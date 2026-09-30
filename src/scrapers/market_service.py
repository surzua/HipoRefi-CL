"""Servicio orquestador de datos de mercado, sincronización macro y cotizaciones bancarias."""

import requests
from typing import Dict, Any, List, Optional
from datetime import date

from src.data.market_store import MarketDataStore
from src.scrapers.bcch_client import CentralBankChileClient
from src.scrapers.cmf_client import CMFClient
from src.scrapers.bank_simulators import BankSimulatorProvider, BankQuote
from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator
from src.core.metrics import RefinanceAnalyzer


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
    DEFAULT_TPM_FALLBACK = 4.50

    def fetch_public_macro_data(self) -> Dict[str, Optional[float]]:
        """
        Consulta indicadores macroeconómicos clave (UF y TPM) en tiempo real desde mindicador.cl.
        Guarda los valores en DuckDB.
        """
        results: Dict[str, Optional[float]] = {"uf": None, "tpm": None}
        today_str = date.today().isoformat()
        records = []

        try:
            resp = requests.get("https://mindicador.cl/api", timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                if "uf" in data and "valor" in data["uf"]:
                    val = float(data["uf"]["valor"])
                    results["uf"] = val
                    records.append({
                        "date": today_str,
                        "series_code": CentralBankChileClient.SERIES_UF_DAILY,
                        "series_name": "Unidad de Fomento (UF)",
                        "value": val,
                        "unit": "CLP",
                        "source": "MINDICADOR_PUBLIC_API",
                    })
                if "tpm" in data and "valor" in data["tpm"]:
                    val = float(data["tpm"]["valor"])
                    results["tpm"] = val
                    records.append({
                        "date": today_str,
                        "series_code": CentralBankChileClient.SERIES_TPM,
                        "series_name": "Tasa de Política Monetaria (TPM)",
                        "value": val,
                        "unit": "PERCENT",
                        "source": "MINDICADOR_PUBLIC_API",
                    })
        except Exception:
            pass

        # Fallback individual si el endpoint agregado no respondió
        if results["uf"] is None:
            try:
                r_uf = requests.get("https://mindicador.cl/api/uf", timeout=5)
                if r_uf.status_code == 200:
                    serie = r_uf.json().get("serie", [])
                    if serie:
                        val = float(serie[0]["valor"])
                        results["uf"] = val
                        records.append({
                            "date": today_str,
                            "series_code": CentralBankChileClient.SERIES_UF_DAILY,
                            "series_name": "Unidad de Fomento (UF)",
                            "value": val,
                            "unit": "CLP",
                            "source": "MINDICADOR_PUBLIC_API",
                        })
            except Exception:
                pass

        if results["tpm"] is None:
            try:
                r_tpm = requests.get("https://mindicador.cl/api/tpm", timeout=5)
                if r_tpm.status_code == 200:
                    serie = r_tpm.json().get("serie", [])
                    if serie:
                        val = float(serie[0]["valor"])
                        results["tpm"] = val
                        records.append({
                            "date": today_str,
                            "series_code": CentralBankChileClient.SERIES_TPM,
                            "series_name": "Tasa de Política Monetaria (TPM)",
                            "value": val,
                            "unit": "PERCENT",
                            "source": "MINDICADOR_PUBLIC_API",
                        })
            except Exception:
                pass

        if records:
            self.store.save_macro_series(records)

        return results

    def fetch_public_uf(self) -> Optional[float]:
        """Consulta el valor de la UF en tiempo real desde la API pública abierta de indicadores."""
        return self.fetch_public_macro_data().get("uf")

    def get_current_tpm(self) -> float:
        """Obtiene la Tasa de Política Monetaria (TPM) más reciente disponible."""
        rates = self.store.get_latest_macro_rates()
        if CentralBankChileClient.SERIES_TPM in rates:
            val = float(rates[CentralBankChileClient.SERIES_TPM]["value"])
            if val == 4.50:
                return val
        live_tpm = self.fetch_public_macro_data().get("tpm")
        return live_tpm if live_tpm is not None else self.DEFAULT_TPM_FALLBACK

    def sync_from_central_bank(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Intenta sincronizar indicadores clave desde la API oficial del Banco Central.
        Si las credenciales no están configuradas, actualiza UF y TPM vía API pública.
        """
        if not self.bcch_client.user or not self.bcch_client.password:
            public_macro = self.fetch_public_macro_data()
            public_uf = public_macro.get("uf") or self.get_current_uf()
            public_tpm = public_macro.get("tpm") or self.get_current_tpm()
            return {
                "status": "SUCCESS",
                "source": "MINDICADOR_PUBLIC_API",
                "uf": public_uf,
                "tpm": public_tpm,
                "message": f"Indicadores actualizados en tiempo real: UF ${public_uf:,.2f} CLP, TPM {public_tpm:.2f}% (sin requerir credenciales BCCh).",
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

            # 2. TPM
            tpm_series = self.bcch_client.fetch_series(
                CentralBankChileClient.SERIES_TPM, first_date, last_date
            )
            for obs in tpm_series.get("obs", []):
                synced_records.append({
                    "date": obs.get("indexDateString"),
                    "series_code": CentralBankChileClient.SERIES_TPM,
                    "series_name": "Tasa de Política Monetaria (TPM)",
                    "value": float(obs.get("value")),
                    "unit": "PERCENT",
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
        tpm_val = self.get_current_tpm()
        if CentralBankChileClient.SERIES_TPM in latest_rates:
            latest_rates[CentralBankChileClient.SERIES_TPM]["value"] = tpm_val

        return {
            "uf_current": self.get_current_uf(),
            "tpm_current": tpm_val,
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

    def get_live_bank_offers(self, term_years: Optional[int] = None) -> List[Dict[str, Any]]:
        """Consulta ofertas en DuckDB provenientes de web scrapers headless."""
        all_offers = self.store.get_active_bank_offers(term_years=term_years)
        return [
            o for o in all_offers
            if "PLAYWRIGHT" in o.get("source", "").upper() or "HEADLESS" in o.get("source", "").upper()
        ]

    def sync_from_live_scrapers(
        self,
        principal_uf: float = 3200.0,
        term_years: int = 20,
        property_value_uf: Optional[float] = None,
        banks: Optional[List[str]] = None,
        headless: bool = True,
    ) -> Dict[str, Any]:
        """
        Ejecuta los scrapers headless de Playwright para cotizadores bancarios y
        guarda las ofertas extraídas en DuckDB.
        """
        from src.scrapers.headless_scrapers import HeadlessMarketScraperCoordinator
        coordinator = HeadlessMarketScraperCoordinator(headless=headless)
        avg_rate = self.cmf_client.get_average_rate("bancos")
        result = coordinator.sync_to_duckdb(
            store=self.store,
            principal_uf=principal_uf,
            term_years=term_years,
            property_value_uf=property_value_uf,
            bank_ids=banks,
            base_benchmark_rate=avg_rate,
        )
        return result

    def get_bank_quotes(
        self,
        principal_uf: float,
        term_years: int,
        property_value_uf: Optional[float] = None,
        prefer_live_scraped: bool = False,
    ) -> List[BankQuote]:
        """
        Simula cotizaciones para todos los bancos comerciales.
        Si prefer_live_scraped es True y hay ofertas de scrapers en DuckDB, las incorpora con prioridad.
        """
        avg_rate = self.cmf_client.get_average_rate("bancos")
        simulator = BankSimulatorProvider(base_market_rate_pct=avg_rate)
        simulated_quotes = simulator.simulate_all_banks(
            principal_uf=principal_uf,
            term_years=term_years,
            property_value_uf=property_value_uf,
        )

        if not prefer_live_scraped:
            return simulated_quotes

        live_offers = self.get_live_bank_offers(term_years=term_years)
        if not live_offers:
            return simulated_quotes

        prop_val = property_value_uf or (principal_uf / 0.80)
        quotes_dict = {q.bank_id: q for q in simulated_quotes}

        for off in live_offers:
            bank_name = off["bank_name"]
            bank_id = off["id"].split("-")[0]
            rate_pct = round(off["annual_rate"] * 100.0, 2)
            rate_dec = off["annual_rate"]
            months = term_years * 12
            fire_rate = off.get("fire_insurance_rate_monthly", 0.00015)
            life_rate = off.get("life_insurance_rate_monthly", 0.00028)
            fire_uf = prop_val * 0.70 * fire_rate

            params = MortgageParams(
                principal=principal_uf,
                annual_rate=rate_dec,
                months_remaining=months,
                fire_insurance_monthly_uf=fire_uf,
                life_insurance_rate_monthly=life_rate,
            )
            schedule = FrenchAmortizer.generate_schedule(params)
            first_m = schedule[0]

            annual_ins_pct = ((fire_uf + first_m["life_insurance_uf"]) * 12 / principal_uf) * 100.0
            cae_pct = round(rate_pct + annual_ins_pct, 2)

            scraped_quote = BankQuote(
                bank_id=bank_id,
                bank_name=bank_name,
                loan_type=off.get("loan_type", "Tasa Fija"),
                term_years=term_years,
                annual_rate_pct=rate_pct,
                monthly_financial_dividend_uf=first_m["financial_dividend_uf"],
                monthly_total_dividend_uf=first_m["total_dividend_uf"],
                life_insurance_uf=first_m["life_insurance_uf"],
                fire_insurance_uf=first_m["fire_insurance_uf"],
                estimated_cae_pct=cae_pct,
                spread_vs_market_pct=round(off.get("spread_over_benchmark", 0.0) * 100.0, 2),
                source=off.get("source", "PLAYWRIGHT_HEADLESS"),
            )
            quotes_dict[bank_id] = scraped_quote

        quotes = list(quotes_dict.values())
        quotes.sort(key=lambda q: q.monthly_total_dividend_uf)
        return quotes

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
        prefer_live_scraped: bool = False,
    ) -> Dict[str, Any]:
        """
        Evalúa integralmente el crédito actual contra las mejores opciones disponibles
        en el mercado financiero chileno.
        """
        target_term = term_years_target or max(5, round(months_remaining / 12))
        quotes = self.get_bank_quotes(
            principal_uf=current_balance_uf,
            term_years=target_term,
            prefer_live_scraped=prefer_live_scraped,
        )


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
