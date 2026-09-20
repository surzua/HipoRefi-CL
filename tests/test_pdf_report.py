"""Pruebas unitarias y de integración para el generador de informes PDF (Hito 7)."""

import io
import pytest
from pypdf import PdfReader
from fastapi.testclient import TestClient

from src.reports.pdf_generator import ExecutiveReportGenerator
from src.app.api import app


@pytest.fixture
def sample_report_payload():
    """Datos de prueba representativos de una evaluación de refinanciamiento."""
    return {
        "client_name": "Sebastián Urzúa",
        "operation_number": "45892019-3",
        "current_bank": "Banco de Chile",
        "uf_value": 40967.24,
        "current_balance_uf": 3200.0,
        "current_rate_pct": 5.20,
        "months_remaining": 180,
        "current_total_dividend_uf": 26.34,
        "current_dividend_clp": 1079077.0,
        "target_bank": "Mutuaria Security",
        "new_rate_pct": 4.23,
        "new_months": 180,
        "new_dividend_uf": 25.08,
        "new_dividend_clp": 1027458.0,
        "recommendation_flag": "RECOMENDADO",
        "rationale": "El refinanciamiento genera un VPN positivo de 144.8 UF. La inversión se recupera en 28 meses.",
        "npv_uf": 144.8,
        "npv_clp": 5932056.0,
        "monthly_savings_uf": 1.26,
        "monthly_savings_clp": 51619.0,
        "payback_months": 28,
        "discount_rate_pct": 2.5,
        "switching_costs": {
            "prepayment_penalty_uf": 20.32,
            "cbr_uf": 3.20,
            "stamp_tax_uf": 0.0,
            "appraisal_uf": 3.0,
            "title_deed_uf": 4.0,
            "notary_uf": 1.0,
            "total_cost_uf": 31.52,
        },
        "market_opportunities": [
            {
                "bank_name": "Mutuaria Security",
                "annual_rate_pct": 4.23,
                "monthly_dividend_uf": 25.08,
                "monthly_savings_clp": 51619.0,
                "npv_uf": 144.8,
                "payback_months": 28,
                "recommendation_flag": "RECOMENDADO",
            },
            {
                "bank_name": "Banco de Chile",
                "annual_rate_pct": 4.38,
                "monthly_dividend_uf": 25.43,
                "monthly_savings_clp": 37280.0,
                "npv_uf": 105.3,
                "payback_months": 37,
                "recommendation_flag": "EVALUAR_CON_CAUTELA",
            },
        ],
    }


def test_executive_report_generator_success(sample_report_payload):
    """Verifica que el generador cree un PDF válido con el contenido exacto y 2 páginas."""
    pdf_bytes = ExecutiveReportGenerator.generate_pdf(sample_report_payload)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 2

    full_text = " ".join(page.extract_text() for page in reader.pages)
    assert "HipoRefi-CL" in full_text
    assert "Ley N° 21.236" in full_text
    assert "Sebastián Urzúa" in full_text
    assert "Banco de Chile" in full_text
    assert "Mutuaria Security" in full_text
    assert "RECOMENDADO" in full_text
    assert "Break-Even" in full_text or "Punto de Equilibrio" in full_text


def test_executive_report_generator_caution_and_negative_flags(sample_report_payload):
    """Verifica que funcione con banderas de evaluación cautelosa o negativa."""
    for flag in ["EVALUAR_CON_CAUTELA", "NO_CONVIENE"]:
        sample_report_payload["recommendation_flag"] = flag
        sample_report_payload["npv_uf"] = -50.0 if flag == "NO_CONVIENE" else 15.0
        sample_report_payload["payback_months"] = None if flag == "NO_CONVIENE" else 55

        pdf_bytes = ExecutiveReportGenerator.generate_pdf(sample_report_payload)
        assert pdf_bytes.startswith(b"%PDF-")

        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 2
        text = reader.pages[0].extract_text()
        assert "DICTAMEN PATRIMONIAL" in text


def test_executive_report_generator_fallback_empty_data():
    """Verifica que el generador maneje diccionarios con valores mínimos por defecto sin lanzar excepción."""
    minimal_data = {
        "current_balance_uf": 2000.0,
        "current_rate_pct": 5.0,
        "months_remaining": 120,
        "target_bank": "Banco Alternativo",
        "new_rate_pct": 4.0,
        "payback_months": None,
    }
    pdf_bytes = ExecutiveReportGenerator.generate_pdf(minimal_data)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_api_pdf_report_endpoint_success():
    """Prueba el endpoint POST /api/v1/reports/pdf de FastAPI."""
    client = TestClient(app)
    req_body = {
        "current_loan": {
            "balance_uf": 3200.0,
            "annual_rate_pct": 5.20,
            "months_remaining": 180,
            "fire_insurance_monthly_uf": 0.70,
        },
        "new_loan": {
            "annual_rate_pct": 4.10,
            "term_years": 15,
            "institution_name": "Mutuaria Security",
        },
        "client_name": "Sebastián Urzúa",
        "operation_number": "45892019-3",
        "current_bank_name": "Banco de Chile",
    }

    response = client.post("/api/v1/reports/pdf", json=req_body)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers.get("content-disposition", "")

    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 2
    full_text = " ".join(page.extract_text() for page in reader.pages)
    assert "HipoRefi-CL" in full_text
    assert "Mutuaria Security" in full_text


def test_api_pdf_report_endpoint_validation_error():
    """Verifica que el endpoint devuelva 422 si los datos del crédito son inválidos."""
    client = TestClient(app)
    invalid_body = {
        "current_loan": {
            "balance_uf": -100.0,  # Inválido (debe ser > 0)
            "annual_rate_pct": 5.20,
            "months_remaining": 180,
        }
    }
    response = client.post("/api/v1/reports/pdf", json=invalid_body)
    assert response.status_code == 422
