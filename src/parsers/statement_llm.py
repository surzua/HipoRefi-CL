"""Extracción estructurada de cartolas hipotecarias bancarias mediante Pydantic y LLMs."""

from typing import Optional
from pydantic import BaseModel, Field


class MortgageStatementExtraction(BaseModel):
    bank_name: str = Field(description="Nombre del banco o mutuaria acreedora")
    operation_number: Optional[str] = Field(default=None, description="Número de operación o crédito")
    current_balance_uf: float = Field(description="Saldo insoluto de capital en UF")
    annual_interest_rate_pct: float = Field(description="Tasa de interés anual en porcentaje (ej: 4.2 para 4.2%)")
    remaining_installments: int = Field(description="Número de dividendos o cuotas pendientes")
    total_installments: Optional[int] = Field(default=None, description="Número total de dividendos pactados originalmente")
    current_total_dividend_uf: float = Field(description="Monto del dividendo mensual total en UF")
    financial_dividend_uf: Optional[float] = Field(default=None, description="Monto del dividendo sin seguros en UF")
    life_insurance_uf: Optional[float] = Field(default=None, description="Monto cobrado por seguro de desgravamen en UF")
    fire_insurance_uf: Optional[float] = Field(default=None, description="Monto cobrado por seguro de incendio y sismo en UF")
    customer_age_years: Optional[int] = Field(default=None, description="Edad del titular si figura en el documento")


SYSTEM_PROMPT_EXTRACTION = """
Eres un asistente experto en ingeniería financiera y banca hipotecaria chilena.
Tu tarea es analizar el texto extraído de una cartola de dividendo hipotecario o estado de cuenta bancario
y extraer las variables cuantitativas críticas en formato JSON estricto cumpliendo el schema provisto.

Reglas fundamentales:
1. Normaliza los montos a UF. Si un valor está exclusivamente en pesos ($ CLP), divídelo por el valor de la UF indicado en la cartola o déjalo nulo si no es identificable.
2. Identifica con precisión si la tasa informada es anual o mensual. Debes entregar siempre la tasa anual en porcentaje (ej. 4.5 para 4.5% anual).
3. Asegúrate de diferenciar el saldo insoluto de capital remanente del monto original contratado.
"""
