"""Pruebas unitarias para PDFReader y extracción estructurada de cartolas hipotecarias."""

import pytest
import io
from pathlib import Path
from src.parsers.pdf_reader import PDFReader, PDFReaderError
from src.parsers.statement_extractor import (
    StatementExtractor,
    HeuristicStatementParser,
    StatementExtractionError,
)
from src.parsers.statement_llm import MortgageStatementExtraction


def test_pdf_reader_synthetic_extract():
    """Valida la generación y lectura de un PDF sintético en memoria."""
    lines = [
        "Banco Santander Chile",
        "Cartola de Crédito Hipotecario",
        "Operación: 98765432-1",
        "Saldo Insoluto: 2.850,50 UF",
        "Tasa de Interés Anual: 4,35 %",
        "Cuota 48 de 240",
        "Dividendo Total: 21,35 UF",
        "Seguro Desgravamen: 0,80 UF",
        "Seguro Incendio: 0,65 UF",
        "Edad titular: 38 años",
    ]
    pdf_bytes = PDFReader.create_synthetic_pdf(lines)
    extracted = PDFReader.extract_text(pdf_bytes)

    assert "Banco Santander" in extracted
    assert "2.850,50" in extracted
    assert "4,35" in extracted


def test_pdf_reader_non_existent_file():
    """Verifica el manejo de archivos inexistentes."""
    with pytest.raises(FileNotFoundError):
        PDFReader.extract_text("data/raw/archivo_fantasma.pdf")


def test_pdf_reader_invalid_bytes():
    """Verifica que bytes corruptos o no-PDF arrojen PDFReaderError."""
    with pytest.raises(PDFReaderError):
        PDFReader.extract_text(b"ESTO NO ES UN PDF VALIDO")


def test_heuristic_parser_banco_de_chile():
    """Prueba el parser determinista con un formato típico de Banco de Chile."""
    text = """
    BANCO DE CHILE
    COMPROBANTE DE PAGO DE DIVIDENDO HIPOTECARIO
    Operación N° 12048593
    Titular: Juan Pérez González
    Edad: 41 años
    Saldo de Capital: 3.120,40 UF
    Tasa Anual: 4,40%
    Dividendo N° 60 / 240
    Dividendo Financiero: 19,85 UF
    Seguro Desgravamen: 0,87 UF
    Seguro Incendio y Sismo: 0,72 UF
    Dividendo Total a Pagar: 21,44 UF
    """
    extraction = HeuristicStatementParser.extract_from_text(text)
    assert extraction.bank_name == "Banco de Chile"
    assert extraction.operation_number == "12048593"
    assert extraction.current_balance_uf == 3120.40
    assert extraction.annual_interest_rate_pct == 4.40
    assert extraction.remaining_installments == 180
    assert extraction.total_installments == 240
    assert extraction.current_total_dividend_uf == 21.44
    assert extraction.financial_dividend_uf == 19.85
    assert extraction.life_insurance_uf == 0.87
    assert extraction.fire_insurance_uf == 0.72
    assert extraction.customer_age_years == 41


def test_heuristic_parser_bancoestado():
    """Prueba el parser con formato BancoEstado."""
    text = """
    BANCO DEL ESTADO DE CHILE
    ESTADO DE CUENTA CRÉDITO HIPOTECARIO HABITA
    Crédito: 7739201-4
    Saldo Insoluto: 1.950,00 UF
    Tasa Pactada: 4,65%
    Cuotas pendientes: 144
    Dividendo Mensual: 16,80 UF
    """
    extraction = HeuristicStatementParser.extract_from_text(text)
    assert extraction.bank_name == "BancoEstado"
    assert extraction.current_balance_uf == 1950.00
    assert extraction.annual_interest_rate_pct == 4.65
    assert extraction.remaining_installments == 144
    assert extraction.current_total_dividend_uf == 16.80


def test_heuristic_parser_bci():
    """Prueba el parser con formato BCI."""
    text = """
    BCI - Banco de Crédito e Inversiones
    Detalle de Dividendo Hipotecario
    Operación: 4402910
    Capital Insoluto: 2.450,80 UF
    Tasa de Interés: 4,25%
    Dividendo 36 de 180
    Total Dividendo: 18,90 UF
    """
    extraction = HeuristicStatementParser.extract_from_text(text)
    assert extraction.bank_name == "BCI"
    assert extraction.current_balance_uf == 2450.80
    assert extraction.annual_interest_rate_pct == 4.25
    assert extraction.remaining_installments == 144
    assert extraction.total_installments == 180


def test_statement_extractor_end_to_end_from_pdf():
    """Prueba de integración end-to-end: PDF binario en memoria a schema MortgageStatementExtraction."""
    lines = [
        "Banco Santander",
        "Cartola Dividendo Hipotecario",
        "Operación N° 88992211",
        "Saldo Insoluto: 3.400,00 UF",
        "Tasa de Interés Anual: 4,50 %",
        "Cuotas Restantes: 200",
        "Dividendo Total: 24,50 UF",
        "Seguro Desgravamen: 0,95 UF",
        "Seguro Incendio: 0,80 UF",
    ]
    pdf_bytes = PDFReader.create_synthetic_pdf(lines)

    extractor = StatementExtractor(mode="auto")
    result = extractor.extract_from_pdf(pdf_bytes)

    assert isinstance(result, MortgageStatementExtraction)
    assert result.bank_name == "Banco Santander"
    assert result.current_balance_uf == 3400.00
    assert result.annual_interest_rate_pct == 4.50
    assert result.remaining_installments == 200
    assert result.current_total_dividend_uf == 24.50
