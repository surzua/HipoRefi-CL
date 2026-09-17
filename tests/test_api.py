"""Pruebas unitarias y de integración para la API FastAPI de HipoRefi-CL."""

import pytest
from fastapi.testclient import TestClient

from src.app.api import app
from src.parsers.pdf_reader import PDFReader


@pytest.fixture(scope="module")
def client():
    """Cliente de pruebas para la API."""
    with TestClient(app) as test_client:
        yield test_client


# ============================================================================
# Pruebas de Metadatos y Salud
# ============================================================================

def test_root_endpoint(client):
    """Verifica el endpoint raíz y su mapa de rutas."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "HipoRefi-CL API"
    assert "endpoints" in data
    assert "simulate" in data["endpoints"]


def test_health_endpoints(client):
    """Verifica los endpoints de health check (/health y /api/v1/health)."""
    for endpoint in ["/health", "/api/v1/health"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "hipo-refi-cl-api"
        assert data["database"] == "duckdb_connected"
        assert data["uf_current"] is not None
        assert data["uf_current"] > 30000.0


# ============================================================================
# Pruebas de /api/v1/simulate
# ============================================================================

def test_simulate_mortgage_with_months_and_schedule(client):
    """Simula amortización con especificación directa de meses e inclusión de tabla."""
    payload = {
        "principal": 3200.0,
        "annual_rate_pct": 4.5,
        "months": 240,
        "fire_insurance_monthly_uf": 0.70,
        "life_insurance_rate_monthly": 0.00028,
        "include_schedule": True,
    }
    response = client.post("/api/v1/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["principal_uf"] == 3200.0
    assert data["annual_rate_pct"] == 4.5
    assert data["months"] == 240
    assert data["term_years"] == 20.0
    assert data["monthly_financial_dividend_uf"] > 0
    assert data["initial_total_dividend_uf"] > data["monthly_financial_dividend_uf"]
    assert data["total_interest_uf"] > 0
    assert data["schedule"] is not None
    assert len(data["schedule"]) == 240

    first_row = data["schedule"][0]
    assert first_row["month"] == 1
    assert first_row["start_balance_uf"] == 3200.0

    last_row = data["schedule"][-1]
    assert last_row["month"] == 240
    assert last_row["end_balance_uf"] == 0.0


def test_simulate_mortgage_with_term_years_no_schedule(client):
    """Simula amortización con especificación en años y omisión de la tabla detallada."""
    payload = {
        "principal": 2500.0,
        "annual_rate_pct": 5.0,
        "term_years": 15,
        "include_schedule": False,
    }
    response = client.post("/api/v1/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["months"] == 180
    assert data["term_years"] == 15.0
    assert data["schedule"] is None
    assert data["monthly_financial_dividend_uf"] > 0


def test_simulate_validation_errors(client):
    """Valida que entradas inconsistentes o erróneas retornen 422."""
    # Monto negativo
    r1 = client.post("/api/v1/simulate", json={"principal": -100, "annual_rate_pct": 4.5, "months": 120})
    assert r1.status_code == 422

    # Tasa cero o negativa
    r2 = client.post("/api/v1/simulate", json={"principal": 1000, "annual_rate_pct": 0, "months": 120})
    assert r2.status_code == 422

    # Falta plazo (ni months ni term_years)
    r3 = client.post("/api/v1/simulate", json={"principal": 1000, "annual_rate_pct": 4.5})
    assert r3.status_code == 422


# ============================================================================
# Pruebas de /api/v1/evaluate-refinance
# ============================================================================

def test_evaluate_refinance_market_benchmark(client):
    """Evalúa un crédito actual contra todas las ofertas de mercado disponibles."""
    payload = {
        "current_loan": {
            "balance_uf": 3200.0,
            "annual_rate_pct": 5.20,
            "months_remaining": 180,
            "current_total_dividend_uf": 23.10,
            "fire_insurance_monthly_uf": 0.70,
            "life_insurance_rate_monthly": 0.00028,
        },
        "target_term_years": 15,
        "finance_costs": False,
    }
    response = client.post("/api/v1/evaluate-refinance", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["uf_rate_clp"] > 30000.0
    assert "current_loan_summary" in data
    assert data["current_loan_summary"]["balance_uf"] == 3200.0

    # Desglose de costos de cambio
    costs = data["switching_costs"]
    assert costs["prepayment_penalty_uf"] > 0
    assert costs["cbr_uf"] >= 1.5
    assert costs["stamp_tax_uf"] == 0.0  # Exento D.L. 3475 sin capital fresco
    assert costs["total_cost_uf"] > 0
    assert costs["total_cost_clp"] > 0

    # Oportunidades de mercado
    assert data["best_opportunity"] is not None
    assert len(data["all_opportunities"]) > 0

    # Ranking ordenado por VPN decreciente
    npvs = [opp["evaluation"]["npv_uf"] for opp in data["all_opportunities"]]
    assert npvs == sorted(npvs, reverse=True)


def test_evaluate_refinance_custom_proposal_convenient(client):
    """Evalúa una propuesta favorable con menor tasa (debe recomendar refinanciamiento)."""
    payload = {
        "current_loan": {
            "balance_uf": 3000.0,
            "annual_rate_pct": 5.80,
            "months_remaining": 240,
            "current_total_dividend_uf": 22.50,
        },
        "new_loan": {
            "annual_rate_pct": 4.10,
            "term_years": 20,
            "institution_name": "Banco Test",
        },
        "finance_costs": False,
        "annual_discount_rate_pct": 2.5,
    }
    response = client.post("/api/v1/evaluate-refinance", json=payload)
    assert response.status_code == 200
    data = response.json()

    single_eval = data["single_evaluation"]
    assert single_eval is not None
    assert single_eval["npv_uf"] > 0
    assert single_eval["monthly_savings_uf"] > 0
    assert single_eval["payback_months"] is not None
    assert single_eval["recommendation_flag"] in ["RECOMENDADO", "EVALUAR_CON_CAUTELA"]


def test_evaluate_refinance_custom_proposal_inconvenient(client):
    """Evalúa una propuesta con mayor tasa (debe rechazar refinanciamiento)."""
    payload = {
        "current_loan": {
            "balance_uf": 3000.0,
            "annual_rate_pct": 3.80,
            "months_remaining": 180,
        },
        "new_loan": {
            "annual_rate_pct": 5.50,
            "months": 180,
            "institution_name": "Banco Desfavorable",
        },
    }
    response = client.post("/api/v1/evaluate-refinance", json=payload)
    assert response.status_code == 200
    data = response.json()

    single_eval = data["single_evaluation"]
    assert single_eval is not None
    assert single_eval["npv_uf"] < 0
    assert single_eval["recommendation_flag"] == "NO_CONVIENE"


def test_evaluate_refinance_with_additional_cash_and_custom_costs(client):
    """Verifica el cálculo del impuesto de timbres si se pide capital adicional."""
    payload = {
        "current_loan": {
            "balance_uf": 2000.0,
            "annual_rate_pct": 4.90,
            "months_remaining": 120,
        },
        "new_loan": {
            "annual_rate_pct": 4.20,
            "months": 120,
        },
        "additional_cash_uf": 500.0,  # 500 UF de libre disponibilidad
        "custom_appraisal_uf": 3.5,
        "custom_title_deed_uf": 4.5,
        "custom_notary_uf": 1.2,
    }
    response = client.post("/api/v1/evaluate-refinance", json=payload)
    assert response.status_code == 200
    data = response.json()

    costs = data["switching_costs"]
    # 500 UF * 0.008 = 4.0 UF de impuesto D.L. 3475 sobre capital fresco
    assert pytest.approx(costs["stamp_tax_uf"], 0.01) == 4.0
    assert costs["appraisal_uf"] == 3.5
    assert costs["title_deed_uf"] == 4.5
    assert costs["notary_uf"] == 1.2


# ============================================================================
# Pruebas de /api/v1/extract-statement
# ============================================================================

def test_extract_statement_from_text(client):
    """Prueba la extracción desde un texto en formato JSON."""
    raw_text = (
        "BANCO DE CHILE\n"
        "COMPROBANTE Y CARTOLA DE DIVIDENDO HIPOTECARIO\n"
        "Operación N° 45892019-3\n"
        "Saldo de Capital Insoluto: 3.200,00 UF\n"
        "Tasa de Interés Anual Pactada: 5,20 %\n"
        "Dividendo 60 de 240\n"
        "Dividendo Financiero: 21,50 UF\n"
        "Seguro Desgravamen: 0,90 UF\n"
        "Seguro Incendio y Sismo: 0,70 UF\n"
        "Dividendo Total a Pagar: 23,10 UF\n"
    )
    payload = {
        "text": raw_text,
        "mode": "heuristic",
    }
    response = client.post("/api/v1/extract-statement", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["bank_name"] == "Banco de Chile"
    assert data["operation_number"] == "45892019-3"
    assert data["current_balance_uf"] == 3200.0
    assert data["annual_interest_rate_pct"] == 5.20
    assert data["remaining_installments"] == 180
    assert data["current_total_dividend_uf"] == 23.10
    assert data["current_balance_clp"] is not None


def test_extract_statement_from_upload_pdf(client):
    """Prueba la subida y procesamiento directo de un archivo PDF sintético."""
    statement_lines = [
        "BANCO SANTANDER CHILE",
        "ESTADO DE CUENTA CRÉDITO HIPOTECARIO",
        "Operación N° 98765432-1",
        "Saldo Insoluto: 2.800,50 UF",
        "Tasa Anual: 4,85 %",
        "Cuotas Pendientes: 144 meses",
        "Dividendo Total: 24,15 UF",
    ]
    pdf_bytes = PDFReader.create_synthetic_pdf(statement_lines)

    files = {"file": ("cartola_santander.pdf", pdf_bytes, "application/pdf")}
    data = {"mode": "heuristic"}

    response = client.post("/api/v1/extract-statement/upload", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["bank_name"] == "Banco Santander"
    assert res_data["current_balance_uf"] == 2800.50
    assert res_data["annual_interest_rate_pct"] == 4.85
    assert res_data["remaining_installments"] == 144


def test_extract_statement_upload_invalid_file(client):
    """Rechaza archivos que no sean PDF."""
    files = {"file": ("archivo.txt", b"Texto plano", "text/plain")}
    response = client.post("/api/v1/extract-statement/upload", files=files)
    assert response.status_code == 400
    assert "Solo se aceptan archivos en formato PDF" in response.json()["detail"]


# ============================================================================
# Pruebas de /api/v1/market-rates
# ============================================================================

def test_get_market_rates_overview(client):
    """Verifica la consulta de indicadores macroeconómicos generales."""
    response = client.get("/api/v1/market-rates")
    assert response.status_code == 200
    data = response.json()

    assert data["uf_current"] > 30000.0
    assert data["tpm_current"] == 4.50
    assert "cmf_benchmarks" in data
    assert "latest_macro_rates" in data


def test_get_market_rates_with_bank_quotes(client):
    """Verifica que al solicitar monto y plazo se retornen cotizaciones bancarias."""
    response = client.get("/api/v1/market-rates?principal_uf=2500&term_years=15")
    assert response.status_code == 200
    data = response.json()

    assert data["bank_quotes"] is not None
    assert len(data["bank_quotes"]) > 0
    first_quote = data["bank_quotes"][0]
    assert "bank_name" in first_quote
    assert "annual_rate_pct" in first_quote
    assert "monthly_total_dividend_uf" in first_quote


def test_sync_market_rates(client):
    """Verifica el endpoint de sincronización de tasas."""
    response = client.post("/api/v1/market-rates/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "uf_current" in data
    assert data["sync_result"]["tpm"] == 4.50
