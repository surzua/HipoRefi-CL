"""Pruebas unitarias e integrales para el módulo de web scraping headless bancario (Hito 9)."""

import pytest
import subprocess
import sys
from datetime import datetime
from fastapi.testclient import TestClient

from src.scrapers.headless_scrapers import (
    ScrapedBankQuote,
    BancoEstadoScraper,
    SantanderScraper,
    BCIScraper,
    ItauScraper,
    HeadlessMarketScraperCoordinator,
)
from src.data.market_store import MarketDataStore
from src.scrapers.market_service import MarketDataService
from src.app.api import app


@pytest.fixture
def memory_store():
    store = MarketDataStore(db_path=":memory:")
    yield store
    store.close()


def test_scraped_bank_quote_dataclass():
    """Valida la estructura, serialización a diccionario y transformación a bank_offers."""
    quote = ScrapedBankQuote(
        bank_id="bancoestado",
        bank_name="BancoEstado",
        loan_type="Tasa Fija (Crédito Habita)",
        term_years=20,
        principal_uf=3200.0,
        property_value_uf=4000.0,
        annual_rate_pct=4.50,
        monthly_financial_dividend_uf=20.089,
        monthly_total_dividend_uf=21.341,
        fire_insurance_uf=0.420,
        life_insurance_uf=0.832,
        cae_pct=4.97,
        source="PLAYWRIGHT_HEADLESS",
    )

    d = quote.to_dict()
    assert d["bank_id"] == "bancoestado"
    assert d["annual_rate_pct"] == 4.50
    assert d["monthly_total_dividend_uf"] == 21.341
    assert d["source"] == "PLAYWRIGHT_HEADLESS"

    offer_dict = quote.to_bank_offer_dict(base_benchmark_rate=4.65)
    assert offer_dict["id"] == "bancoestado-20y-450"
    assert offer_dict["annual_rate"] == 0.045
    assert offer_dict["spread_over_benchmark"] == round(0.045 - 0.0465, 4)
    assert offer_dict["min_ltv"] == 0.80
    assert offer_dict["source"] == "PLAYWRIGHT_HEADLESS"


def test_bancoestado_scraper_parsing():
    """Valida la extracción de dividendos, tasas y CAE con HTML simulado de BancoEstado."""
    scraper = BancoEstadoScraper(timeout_ms=5000, headless=True)

    mock_html = """
    <html>
        <body>
            <div class="simulator-results">
                <h2>Resultado Simulación Hipotecario</h2>
                <div class="row">Tasa Anual: 4.45%</div>
                <div class="row">Dividendo Bruto: 19.98 UF</div>
                <div class="row">Dividendo Total: 21.23 UF</div>
                <div class="row">CAE: 4.88%</div>
            </div>
        </body>
    </html>
    """
    quote = scraper.scrape(
        principal_uf=3200.0,
        term_years=20,
        property_value_uf=4000.0,
        custom_html=mock_html,
    )

    assert quote.bank_id == "bancoestado"
    assert quote.annual_rate_pct == 4.45
    assert quote.cae_pct == 4.88
    assert quote.monthly_total_dividend_uf == 21.23
    assert quote.monthly_financial_dividend_uf == 19.98
    assert quote.source == "PLAYWRIGHT_HEADLESS"


def test_santander_scraper_parsing():
    """Valida la extracción de Santander desde HTML simulado."""
    scraper = SantanderScraper(timeout_ms=5000, headless=True)

    mock_html = """
    <html>
        <body>
            <div class="santander-summary">
                <span class="rate">Tasa Fija: 4.38%</span>
                <span class="div-total">Dividendo con seguros: 21.18 UF</span>
                <span class="cae">CAE: 4.82%</span>
            </div>
        </body>
    </html>
    """
    quote = scraper.scrape(
        principal_uf=3200.0,
        term_years=20,
        property_value_uf=4000.0,
        custom_html=mock_html,
    )

    assert quote.bank_id == "santander"
    assert quote.annual_rate_pct == 4.38
    assert quote.monthly_total_dividend_uf == 21.18
    assert quote.cae_pct == 4.82
    assert quote.source == "PLAYWRIGHT_HEADLESS"


def test_bci_scraper_parsing():
    """Valida la extracción de BCI desde HTML simulado."""
    scraper = BCIScraper(timeout_ms=5000, headless=True)

    mock_html = """
    <html>
        <body>
            <div class="bci-box">
                <p>Tasa Anual Fija: 4.32%</p>
                <p>Dividendo Final: 21.05 UF</p>
                <p>CAE: 4.78%</p>
            </div>
        </body>
    </html>
    """
    quote = scraper.scrape(
        principal_uf=3200.0,
        term_years=20,
        property_value_uf=4000.0,
        custom_html=mock_html,
    )

    assert quote.bank_id == "bci"
    assert quote.annual_rate_pct == 4.32
    assert quote.monthly_total_dividend_uf == 21.05
    assert quote.cae_pct == 4.78
    assert quote.source == "PLAYWRIGHT_HEADLESS"


def test_itau_scraper_parsing():
    """Valida la extracción de Itaú (alianza TOCTOC) con HTML simulado."""
    scraper = ItauScraper(timeout_ms=5000, headless=True)

    mock_html = """
    <html>
        <body>
            <div class="toctoc-results">
                <h2>Opciones de financiamiento Itaú</h2>
                <div class="row">Tasa Anual: 4.90%</div>
                <div class="row">Dividendo Total: 20.75 UF</div>
                <div class="row">Seguro Incendio y Sismo: 0.65 UF</div>
                <div class="row">Seguro Desgravamen: 0.28 UF</div>
            </div>
        </body>
    </html>
    """
    quote = scraper.scrape(
        principal_uf=3200.0,
        term_years=20,
        property_value_uf=4000.0,
        custom_html=mock_html,
    )

    assert quote.bank_id == "itau"
    assert quote.annual_rate_pct == 4.90
    assert quote.monthly_total_dividend_uf == 20.75
    assert quote.source == "TOCTOC_ITAU_HTML"


def test_itau_scraper_live_toctoc():
    """Valida la consulta en vivo de Itaú a través del gateway TOCTOC."""
    scraper = ItauScraper(timeout_ms=10000, headless=True)
    quote = scraper.scrape(
        principal_uf=3200.0,
        term_years=20,
        property_value_uf=4000.0,
    )

    assert quote.bank_id == "itau"
    assert "Itaú" in quote.bank_name
    assert 3.5 <= quote.annual_rate_pct <= 6.5
    assert quote.monthly_total_dividend_uf > 15.0
    assert quote.source in ["TOCTOC_ITAU_LIVE", "HEADLESS_FALLBACK"]


def test_scraper_fallback_generation():
    """Valida que los fallbacks generen cotizaciones cuantitativas válidas y coherentes."""
    be = BancoEstadoScraper()
    st = SantanderScraper()
    bci = BCIScraper()
    itau = ItauScraper()

    q_be = be.generate_fallback_quote(3200.0, 20, 4000.0)
    q_st = st.generate_fallback_quote(3200.0, 20, 4000.0)
    q_bci = bci.generate_fallback_quote(3200.0, 20, 4000.0)
    q_itau = itau.generate_fallback_quote(3200.0, 20, 4000.0)

    for q in [q_be, q_st, q_bci, q_itau]:
        assert q.source == "HEADLESS_FALLBACK"
        assert 3.5 <= q.annual_rate_pct <= 6.0
        assert q.monthly_total_dividend_uf > q.monthly_financial_dividend_uf
        assert q.cae_pct > q.annual_rate_pct
        assert q.fire_insurance_uf > 0
        assert q.life_insurance_uf > 0


def test_coordinator_sync_to_duckdb(memory_store):
    """Valida que el coordinador ejecute scrapers y actualice bank_offers en DuckDB."""
    coordinator = HeadlessMarketScraperCoordinator(headless=True, timeout_ms=5000)

    res = coordinator.sync_to_duckdb(
        store=memory_store,
        principal_uf=3200.0,
        term_years=20,
        bank_ids=["bancoestado", "santander", "bci", "itau"],
    )

    assert res["status"] == "SUCCESS"
    assert res["offers_scraped"] == 4
    assert res["records_saved"] == 4

    # Verificar lectura desde store
    offers = memory_store.get_active_bank_offers(term_years=20)
    offer_banks = [o["bank_name"] for o in offers]
    assert "BancoEstado" in offer_banks
    assert any("Santander" in b for b in offer_banks)
    assert any("BCI" in b or "Crédito e Inversiones" in b for b in offer_banks)
    assert any("Itaú" in b for b in offer_banks)


def test_market_service_live_scraped_priority(memory_store):
    """Valida que MarketDataService priorice ofertas en vivo cuando prefer_live_scraped=True."""
    # Insertar una oferta con tasa preferente marcada como PLAYWRIGHT_HEADLESS
    memory_store.save_bank_offers([{
        "id": "bancoestado-20y-410",
        "bank_name": "BancoEstado",
        "loan_type": "Tasa Fija (Scraped)",
        "term_years": 20,
        "annual_rate": 0.0410,  # 4.10%
        "spread_over_benchmark": -0.0055,
        "min_ltv": 0.80,
        "fire_insurance_rate_monthly": 0.00015,
        "life_insurance_rate_monthly": 0.00026,
        "source": "PLAYWRIGHT_HEADLESS",
        "updated_at": datetime.now(),
    }])

    service = MarketDataService(store=memory_store)

    live_offers = service.get_live_bank_offers(term_years=20)
    assert len(live_offers) == 1
    assert live_offers[0]["bank_name"] == "BancoEstado"

    # Cotizaciones sin prefer_live_scraped
    default_quotes = service.get_bank_quotes(principal_uf=3200.0, term_years=20, prefer_live_scraped=False)
    be_default = next(q for q in default_quotes if q.bank_id == "bancoestado")
    assert be_default.source == "SIMULATOR_ENGINE"

    # Cotizaciones con prefer_live_scraped
    live_quotes = service.get_bank_quotes(principal_uf=3200.0, term_years=20, prefer_live_scraped=True)
    be_live = next(q for q in live_quotes if q.bank_id == "bancoestado")
    assert be_live.source == "PLAYWRIGHT_HEADLESS"
    assert be_live.annual_rate_pct == 4.10


def test_cli_sync_live_market_dry_run():
    """Valida la ejecución del script CLI `sync_live_market.py` con argumentos --dry-run y --json."""
    cmd = [
        sys.executable,
        "scripts/sync_live_market.py",
        "--principal", "3200",
        "--term", "20",
        "--banks", "bancoestado",
        "--dry-run",
        "--json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f"Error: {result.stderr}"
    assert '"status": "SUCCESS"' in result.stdout
    assert '"bank_id": "bancoestado"' in result.stdout


def test_api_scrape_sync_and_live_offers():
    """Valida los endpoints POST /scrape-sync y GET /live-offers en la API FastAPI."""
    client = TestClient(app)

    # 1. POST /api/v1/market-rates/scrape-sync
    resp_sync = client.post(
        "/api/v1/market-rates/scrape-sync",
        json={
            "principal_uf": 3200.0,
            "term_years": 20,
            "banks": ["bancoestado", "santander"],
            "headless": True,
        },
    )
    assert resp_sync.status_code == 200
    data_sync = resp_sync.json()
    assert data_sync["status"] == "SUCCESS"
    assert data_sync["offers_scraped"] == 2
    assert len(data_sync["quotes"]) == 2

    # 2. GET /api/v1/market-rates/live-offers
    resp_offers = client.get("/api/v1/market-rates/live-offers?term_years=20")
    assert resp_offers.status_code == 200
    data_offers = resp_offers.json()
    assert data_offers["count"] >= 2
    assert any("BancoEstado" in o["bank_name"] for o in data_offers["offers"])


def test_html_parsing_native_regex_fallback_when_bs4_unavailable(monkeypatch):
    """Valida que _extract_text_from_html extraiga correctamente texto y números incluso sin BeautifulSoup."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "bs4" in name:
            raise ImportError("Mock No module named 'bs4'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    scraper = BancoEstadoScraper(timeout_ms=5000, headless=True)
    mock_html = """
    <html>
        <body>
            <div class="simulator-results">
                <h2>Resultado Simulación Hipotecario</h2>
                <div class="row">Tasa Anual: 4.45%</div>
                <div class="row">Dividendo Bruto: 19.98 UF</div>
                <div class="row">Dividendo Total: 21.23 UF</div>
                <div class="row">CAE: 4.88%</div>
            </div>
        </body>
    </html>
    """
    quote = scraper.scrape(
        principal_uf=3200.0,
        term_years=20,
        property_value_uf=4000.0,
        custom_html=mock_html,
    )

    assert quote.annual_rate_pct == 4.45
    assert quote.cae_pct == 4.88
    assert quote.monthly_total_dividend_uf == 21.23
    assert quote.source == "PLAYWRIGHT_HEADLESS"

