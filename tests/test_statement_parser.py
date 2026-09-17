"""Pruebas unitarias para los esquemas de extracción de cartolas hipotecarias (Pydantic)."""

import pytest
from pydantic import ValidationError
from src.parsers.statement_llm import MortgageStatementExtraction, SYSTEM_PROMPT_EXTRACTION


def test_statement_extraction_schema_valid():
    """Valida la instanciación de MortgageStatementExtraction con datos completos."""
    data = {
        "bank_name": "Banco de Chile",
        "operation_number": "12345678-9",
        "current_balance_uf": 2850.50,
        "annual_interest_rate_pct": 4.35,
        "remaining_installments": 180,
        "total_installments": 240,
        "current_total_dividend_uf": 21.45,
        "financial_dividend_uf": 19.80,
        "life_insurance_uf": 0.85,
        "fire_insurance_uf": 0.80,
        "customer_age_years": 42,
    }

    extraction = MortgageStatementExtraction(**data)
    assert extraction.bank_name == "Banco de Chile"
    assert extraction.current_balance_uf == 2850.50
    assert extraction.remaining_installments == 180
    assert extraction.customer_age_years == 42


def test_statement_extraction_missing_required_fields():
    """Verifica que Pydantic exija los campos fundamentales de la deuda."""
    with pytest.raises(ValidationError):
        # Falta current_balance_uf y annual_interest_rate_pct
        MortgageStatementExtraction(
            bank_name="Santander",
            remaining_installments=120,
            current_total_dividend_uf=15.0,
        )


def test_system_prompt_integrity():
    """Verifica que el prompt de extracción contenga las directrices clave."""
    assert "UF" in SYSTEM_PROMPT_EXTRACTION
    assert "tasa anual" in SYSTEM_PROMPT_EXTRACTION.lower()
