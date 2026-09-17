"""Módulo de procesamiento y extracción estructurada de documentos de deuda hipotecaria."""

from src.parsers.statement_llm import MortgageStatementExtraction, SYSTEM_PROMPT_EXTRACTION

__all__ = ["MortgageStatementExtraction", "SYSTEM_PROMPT_EXTRACTION"]
