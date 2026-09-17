"""Pruebas unitarias y de integración para la persistencia DuckDB y datos de mercado."""

import pytest
from src.data.market_store import MarketDataStore
from src.scrapers.cmf_client import CMFClient
from src.scrapers.bank_simulators import BankSimulatorProvider, BankQuote
from src.scrapers.market_service import MarketDataService
from src.scrapers.bcch_client import CentralBankChileClient


@pytest.fixture
def memory_store():
    """Crea una base de datos DuckDB en memoria aislada para tests."""
    store = MarketDataStore(db_path=":memory:")
    yield store
    store.close()


def test_duckdb_schema_initialization(memory_store):
    """Verifica la creación correcta de tablas e idempotencia de inicialización."""
    # Debe tener schema inicializado
    tables = memory_store.conn.execute("SHOW TABLES;").fetchall()
    table_names = [t[0] for t in tables]
    assert "macro_series" in table_names
    assert "bank_offers" in table_names


def test_duckdb_seed_and_query(memory_store):
    """Verifica que el semillado de datos funcione e inserte registros coherentes."""
    memory_store.seed_default_market_data()

    # 1. UF debe existir y ser un valor positivo realista
    uf = memory_store.get_latest_uf()
    assert uf is not None
    assert 35000.0 < uf < 50000.0

    # 2. Resumen de tasas
    summary = memory_store.get_latest_macro_rates()
    assert "F073.UFF.PRE.Z.D" in summary
    assert "F072.CLP.COL.VIV.Z.M" in summary
    assert "F073.TPM.TCM.G01.Z.D" in summary
    assert summary["F073.TPM.TCM.G01.Z.D"]["value"] == 4.50

    # 3. Ofertas de bancos
    offers_20 = memory_store.get_active_bank_offers(term_years=20)
    assert len(offers_20) > 0
    # Deben estar ordenadas por menor tasa
    rates = [o["annual_rate"] for o in offers_20]
    assert rates == sorted(rates)


def test_cmf_client_benchmarks():
    """Valida los benchmarks oficiales de la CMF para bancos y mutuarias."""
    cmf = CMFClient()
    benchmarks = cmf.get_market_benchmarks()
    assert "bancos_vivienda_uf" in benchmarks
    assert "mutuarias_vivienda_uf" in benchmarks

    rate_bancos = cmf.get_average_rate("bancos")
    rate_mutuarias = cmf.get_average_rate("mutuarias")
    assert 3.5 < rate_bancos < 6.0
    assert 3.0 < rate_mutuarias < 6.0
    # Históricamente las mutuarias suelen tener tasas competitivas
    assert rate_mutuarias <= rate_bancos


def test_bank_simulator_provider():
    """Valida la simulación de cotizaciones bancarias con cálculo de seguros y dividendos."""
    provider = BankSimulatorProvider(base_market_rate_pct=4.65)
    quotes = provider.simulate_all_banks(principal_uf=3000.0, term_years=20)

    assert len(quotes) >= 5
    # Deben estar ordenadas de menor a mayor dividendo total
    dividends = [q.monthly_total_dividend_uf for q in quotes]
    assert dividends == sorted(dividends)

    # Cada cotización debe tener seguros y desglose cuantitativo consistente
    top_quote = quotes[0]
    assert top_quote.monthly_total_dividend_uf > top_quote.monthly_financial_dividend_uf
    assert top_quote.life_insurance_uf > 0.0
    assert top_quote.fire_insurance_uf > 0.0
    assert isinstance(top_quote.to_dict(), dict)


def test_market_service_offline_mode(memory_store):
    """Valida que el servicio funcione de forma autónoma sin credenciales del Banco Central."""
    service = MarketDataService(store=memory_store)

    # Intentar sincronizar sin credenciales del BCCh debe resolver vía API pública o saltar limpiamente sin errores
    sync_res = service.sync_from_central_bank()
    assert sync_res["status"] in ["SUCCESS", "SKIPPED"]

    # Conversión de monedas con la UF vigente
    uf = service.get_current_uf()
    assert uf >= 40000.0  # UF actualizada de la economía chilena
    clp_val = service.convert_uf_to_clp(10.0)
    assert pytest.approx(clp_val, rel=1e-4) == 10.0 * uf
    assert pytest.approx(service.convert_clp_to_uf(clp_val), rel=1e-4) == 10.0


def test_evaluate_refinance_against_market(memory_store):
    """
    Verifica la evaluación cruzada entre la deuda actual del usuario
    y el catálogo de ofertas bancarias del mercado.
    """
    service = MarketDataService(store=memory_store)

    # Caso: Deudor con tasa alta al 5.5% anual con 20 años restantes
    evaluation = service.evaluate_refinance_against_market(
        current_balance_uf=3200.0,
        current_annual_rate=0.055,
        months_remaining=240,
    )

    assert "best_opportunity" in evaluation
    assert evaluation["best_opportunity"] is not None
    # El mejor banco del mercado debe generar un VPN positivo para este cliente
    best_npv = evaluation["best_opportunity"]["evaluation"]["npv_uf"]
    assert best_npv > 0.0
    assert evaluation["best_opportunity"]["evaluation"]["recommendation_flag"] == "RECOMENDADO"
    assert "switching_costs_breakdown" in evaluation


def test_bcch_client_without_credentials():
    """Valida que el cliente del BCCh lance ValueError claro si faltan credenciales."""
    client = CentralBankChileClient(user=None, password=None)
    with pytest.raises(ValueError, match="Credenciales del Banco Central no configuradas"):
        client.fetch_series(CentralBankChileClient.SERIES_UF_DAILY, "2026-01-01", "2026-01-31")
