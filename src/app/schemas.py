"""Modelos Pydantic para solicitudes y respuestas de la API de HipoRefi-CL."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Modelos para /api/v1/simulate
# ============================================================================

class SimulationRequest(BaseModel):
    """Parámetros de entrada para simulación de crédito hipotecario francés."""
    principal: float = Field(
        ...,
        gt=0,
        description="Monto del préstamo o saldo de capital en UF (ej: 3200.0)",
        examples=[3200.0],
    )
    annual_rate_pct: float = Field(
        ...,
        gt=0,
        le=30.0,
        description="Tasa de interés anual en porcentaje (ej: 4.5 para 4.5% anual)",
        examples=[4.5],
    )
    months: Optional[int] = Field(
        default=None,
        gt=0,
        le=480,
        description="Plazo del crédito en meses (ej: 240 para 20 años). Opcional si se indica term_years.",
        examples=[240],
    )
    term_years: Optional[int] = Field(
        default=None,
        gt=0,
        le=40,
        description="Plazo del crédito en años (ej: 20). Opcional si se indica months.",
        examples=[20],
    )
    fire_insurance_monthly_uf: float = Field(
        default=0.0,
        ge=0,
        description="Monto fijo mensual del seguro de incendio y sismo en UF.",
        examples=[0.70],
    )
    life_insurance_rate_monthly: float = Field(
        default=0.00028,
        ge=0,
        description="Tasa mensual del seguro de desgravamen sobre saldo insoluto (defecto 0.028% = 0.00028).",
        examples=[0.00028],
    )
    include_schedule: bool = Field(
        default=True,
        description="Determina si la respuesta incluye la tabla completa mes a mes.",
    )

    @model_validator(mode="after")
    def validate_term(self) -> "SimulationRequest":
        if self.months is None and self.term_years is None:
            raise ValueError("Debe proporcionar al menos 'months' o 'term_years'.")
        if self.months is None and self.term_years is not None:
            self.months = self.term_years * 12
        return self


class AmortizationRow(BaseModel):
    """Detalle de una cuota mensual en la tabla de amortización."""
    month: int = Field(description="Número de cuota (1 a N)")
    start_balance_uf: float = Field(description="Saldo insoluto al inicio del mes")
    financial_dividend_uf: float = Field(description="Dividendo financiero puro (capital + interés)")
    interest_uf: float = Field(description="Interés devengado en el mes")
    amortization_uf: float = Field(description="Amortización real de capital")
    life_insurance_uf: float = Field(description="Seguro de desgravamen del mes")
    fire_insurance_uf: float = Field(description="Seguro de incendio y sismo del mes")
    total_dividend_uf: float = Field(description="Dividendo total a pagar en el mes")
    end_balance_uf: float = Field(description="Saldo de capital al finalizar el mes")


class SimulationResponse(BaseModel):
    """Resumen cuantitativo y tabla de desarrollo de la simulación."""
    principal_uf: float = Field(description="Monto o saldo simulado en UF")
    annual_rate_pct: float = Field(description="Tasa anual nominal simulada en %")
    months: int = Field(description="Plazo total en meses")
    term_years: float = Field(description="Plazo equivalente en años")
    monthly_financial_dividend_uf: float = Field(description="Dividendo financiero mensual puro en UF")
    initial_total_dividend_uf: float = Field(description="Primer dividendo total mensual con seguros en UF")
    total_interest_uf: float = Field(description="Total acumulado de intereses a pagar durante el crédito")
    total_cost_uf: float = Field(description="Costo total acumulado de todos los dividendos")
    total_life_insurance_uf: float = Field(description="Total de primas pagadas por seguro de desgravamen")
    total_fire_insurance_uf: float = Field(description="Total de primas pagadas por seguro de incendio")
    schedule: Optional[List[AmortizationRow]] = Field(
        default=None,
        description="Tabla de amortización detallada mes a mes (si fue solicitada).",
    )


# ============================================================================
# Modelos para /api/v1/evaluate-refinance
# ============================================================================

class CurrentLoanInput(BaseModel):
    """Datos del crédito hipotecario vigente del cliente."""
    balance_uf: float = Field(
        ...,
        gt=0,
        description="Saldo insoluto actual de capital en UF",
        examples=[3200.0],
    )
    annual_rate_pct: float = Field(
        ...,
        gt=0,
        le=30.0,
        description="Tasa de interés anual pactada actual en %",
        examples=[5.20],
    )
    months_remaining: int = Field(
        ...,
        gt=0,
        le=480,
        description="Plazo restante en meses del crédito actual",
        examples=[180],
    )
    current_total_dividend_uf: Optional[float] = Field(
        default=None,
        gt=0,
        description="Dividendo total mensual pagado actualmente en UF (si se omite, se calcula matemáticamente)",
        examples=[23.10],
    )
    fire_insurance_monthly_uf: float = Field(
        default=0.0,
        ge=0,
        description="Monto mensual en UF del seguro de incendio y sismo actual",
        examples=[0.70],
    )
    life_insurance_rate_monthly: float = Field(
        default=0.00028,
        ge=0,
        description="Tasa mensual del seguro de desgravamen actual sobre saldo",
        examples=[0.00028],
    )


class NewLoanOfferInput(BaseModel):
    """Oferta o propuesta específica de nuevo crédito a evaluar."""
    annual_rate_pct: float = Field(
        ...,
        gt=0,
        le=30.0,
        description="Tasa anual ofrecida en % por la nueva entidad",
        examples=[4.10],
    )
    months: Optional[int] = Field(
        default=None,
        gt=0,
        le=480,
        description="Nuevo plazo en meses. Si se omite, se puede usar term_years.",
        examples=[180],
    )
    term_years: Optional[int] = Field(
        default=None,
        gt=0,
        le=40,
        description="Nuevo plazo en años (ej: 15). Opcional si se indica months.",
        examples=[15],
    )
    fire_insurance_monthly_uf: float = Field(
        default=0.65,
        ge=0,
        description="Seguro de incendio y sismo mensual en UF en la nueva entidad",
        examples=[0.65],
    )
    life_insurance_rate_monthly: float = Field(
        default=0.00028,
        ge=0,
        description="Tasa mensual de desgravamen en la nueva entidad",
        examples=[0.00028],
    )
    institution_name: Optional[str] = Field(
        default="Propuesta Bancaria",
        description="Nombre del banco o mutuaria oferente",
        examples=["Banco Santander"],
    )

    @model_validator(mode="after")
    def validate_term(self) -> "NewLoanOfferInput":
        if self.months is None and self.term_years is not None:
            self.months = self.term_years * 12
        return self


class RefinanceEvaluationRequest(BaseModel):
    """Solicitud integral de análisis de refinanciamiento."""
    current_loan: CurrentLoanInput = Field(description="Datos del crédito hipotecario vigente")
    new_loan: Optional[NewLoanOfferInput] = Field(
        default=None,
        description="Propuesta específica a evaluar. Si se omite, se analiza contra todo el mercado de bancos y mutuarias.",
    )
    target_term_years: Optional[int] = Field(
        default=None,
        gt=0,
        le=40,
        description="Plazo en años objetivo para comparar contra el mercado (si no se envía new_loan). Por defecto el equivalente a months_remaining.",
    )
    finance_costs: bool = Field(
        default=False,
        description="Si es True, los gastos operacionales se agregan al capital del nuevo crédito (no se pagan de bolsillo en t=0).",
    )
    additional_cash_uf: float = Field(
        default=0.0,
        ge=0,
        description="Monto de libre disponibilidad adicional solicitado en UF (afecta impuesto D.L. 3475).",
    )
    annual_discount_rate_pct: float = Field(
        default=2.5,
        gt=0,
        le=20.0,
        description="Tasa de descuento anual en UF (costo de oportunidad del capital, defecto 2.5%).",
    )
    custom_appraisal_uf: Optional[float] = Field(
        default=None,
        ge=0,
        description="Costo personalizado de tasación en UF (si se omite, se usa promedio de mercado = 3.0 UF).",
    )
    custom_title_deed_uf: Optional[float] = Field(
        default=None,
        ge=0,
        description="Costo personalizado de estudio de títulos en UF (si se omite, se usa 4.0 UF).",
    )
    custom_notary_uf: Optional[float] = Field(
        default=None,
        ge=0,
        description="Costo personalizado de notaría en UF (si se omite, arancel Ley 21.236 = 1.0 UF).",
    )


class SwitchingCostsDetail(BaseModel):
    """Desglose normativo de costos de cambio según Ley 21.236, DL 3475 y LGB Art. 100."""
    prepayment_penalty_uf: float = Field(description="Comisión de prepago en UF (máx 1.5 meses de intereses devengados)")
    appraisal_uf: float = Field(description="Costo de tasación del inmueble en UF")
    title_deed_uf: float = Field(description="Costo de estudio de títulos y redacción de escritura en UF")
    notary_uf: float = Field(description="Gastos notariales bajo arancel regulado Ley 21.236 en UF")
    cbr_uf: float = Field(description="Arancel Conservador de Bienes Raíces (50% de descuento por subrogación)")
    stamp_tax_uf: float = Field(description="Impuesto D.L. 3475 (exento 100% si no hay capital fresco adicional)")
    total_cost_uf: float = Field(description="Costo total de cambio en UF")
    total_cost_clp: float = Field(description="Costo total de cambio convertido a pesos chilenos vigentes")


class RefinanceDecisionDetail(BaseModel):
    """Métricas cuantitativas de decisión patrimonial."""
    npv_uf: float = Field(description="Valor Presente Neto (VPN) de la operación en UF")
    npv_clp: float = Field(description="VPN de la operación en pesos chilenos")
    payback_months: Optional[int] = Field(description="Meses necesarios para recuperar los costos de cambio descontados")
    monthly_savings_uf: float = Field(description="Ahorro mensual en el primer dividendo en UF")
    monthly_savings_clp: float = Field(description="Ahorro mensual en pesos chilenos")
    total_lifetime_savings_nominal_uf: float = Field(description="Ahorro total nominal durante toda la vida del crédito en UF")
    total_lifetime_savings_nominal_clp: float = Field(description="Ahorro total nominal en pesos chilenos")
    recommendation_flag: str = Field(description="'RECOMENDADO', 'EVALUAR_CON_CAUTELA' o 'NO_CONVIENE'")
    rationale: str = Field(description="Justificación financiera y patrimonial detallada")


class OpportunityItem(BaseModel):
    """Detalle de una oferta o entidad analizada en el mercado."""
    institution_name: str = Field(description="Nombre de la institución bancaria o mutuaria")
    institution_id: str = Field(default="", description="Identificador institucional (ej: bchile, santander)")
    loan_type: str = Field(default="Tasa Fija", description="Tipo de tasa o producto hipotecario")
    annual_rate_pct: float = Field(description="Tasa anual ofrecida en %")
    term_years: int = Field(description="Plazo del crédito en años")
    monthly_dividend_new_uf: float = Field(description="Dividendo total mensual resultante en UF")
    monthly_dividend_new_clp: float = Field(description="Dividendo mensual resultante en pesos chilenos")
    estimated_cae_pct: Optional[float] = Field(default=None, description="Carga Anual Equivalente (CAE) estimada en %")
    evaluation: RefinanceDecisionDetail = Field(description="Evaluación de conveniencia de esta opción")


class RefinanceEvaluationResponse(BaseModel):
    """Respuesta completa del análisis de refinanciamiento."""
    uf_rate_clp: float = Field(description="Valor de la UF utilizado para las conversiones a CLP")
    current_loan_summary: Dict[str, Any] = Field(description="Resumen del crédito actual analizado")
    switching_costs: SwitchingCostsDetail = Field(description="Desglose legal de costos de cambio")
    single_evaluation: Optional[RefinanceDecisionDetail] = Field(
        default=None,
        description="Resultado de la evaluación si se proporcionó una oferta específica (new_loan).",
    )
    best_opportunity: Optional[OpportunityItem] = Field(
        default=None,
        description="Mejor alternativa identificada en el mercado (mayor VPN generado).",
    )
    all_opportunities: List[OpportunityItem] = Field(
        default=[],
        description="Ranking de todas las alternativas de bancos y mutuarias evaluadas, ordenadas por mayor VPN.",
    )


# ============================================================================
# Modelos para /api/v1/extract-statement
# ============================================================================

class StatementTextRequest(BaseModel):
    """Solicitud de extracción de cartola a partir de texto crudo."""
    text: str = Field(
        ...,
        min_length=10,
        description="Texto plano copiado de la cartola o estado de cuenta hipotecario",
        examples=["BANCO DE CHILE\nOperación N° 45892019-3\nSaldo de Capital Insoluto: 3.200,00 UF\nTasa: 5,20 %"],
    )
    mode: str = Field(
        default="auto",
        description="Modo de extracción: 'auto' (heurísticas + LLM si hay API keys), 'heuristic', 'gemini', 'openai'.",
        examples=["auto"],
    )


class StatementExtractionResponse(BaseModel):
    """Datos cuantitativos y administrativos extraídos de la cartola."""
    bank_name: str = Field(description="Nombre del banco o mutuaria acreedora identificado")
    operation_number: Optional[str] = Field(default=None, description="Número de operación o crédito")
    current_balance_uf: float = Field(description="Saldo insoluto de capital en UF")
    current_balance_clp: Optional[float] = Field(default=None, description="Saldo insoluto estimado en pesos chilenos")
    annual_interest_rate_pct: float = Field(description="Tasa de interés anual pactada en %")
    remaining_installments: int = Field(description="Número de dividendos o cuotas pendientes")
    remaining_years: float = Field(description="Plazo restante equivalente en años")
    total_installments: Optional[int] = Field(default=None, description="Número total de dividendos pactados originalmente")
    current_total_dividend_uf: float = Field(description="Monto del dividendo mensual total en UF")
    current_total_dividend_clp: Optional[float] = Field(default=None, description="Dividendo total mensual estimado en pesos")
    financial_dividend_uf: Optional[float] = Field(default=None, description="Dividendo financiero puro sin seguros en UF")
    life_insurance_uf: Optional[float] = Field(default=None, description="Monto cobrado por seguro de desgravamen en UF")
    fire_insurance_uf: Optional[float] = Field(default=None, description="Monto cobrado por seguro de incendio y sismo en UF")
    customer_age_years: Optional[int] = Field(default=None, description="Edad del titular si figura en el documento")
    extraction_source: str = Field(default="heuristic", description="Método o motor que extrajo la información")


# ============================================================================
# Modelos para /api/v1/market-rates
# ============================================================================

class MarketRatesResponse(BaseModel):
    """Panorama de tasas, UF vigente e indicadores macrofinancieros en Chile."""
    uf_current: float = Field(description="Valor vigente de la Unidad de Fomento (UF) en CLP")
    tpm_current: float = Field(default=4.50, description="Tasa de Política Monetaria (TPM) vigente en %")
    uf_source: str = Field(description="Fuente del dato de la UF (DuckDB, Mindicador API o BCCh)")
    latest_macro_rates: Dict[str, Any] = Field(description="Series macroeconómicas observadas (TPM, tasas promedio)")
    cmf_benchmarks: Dict[str, Any] = Field(description="Tasas de referencia CMF por segmento (letras, mutuos, no residenciales)")
    bank_quotes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Cotizaciones de bancos y mutuarias simuladas para los parámetros solicitados.",
    )


# ============================================================================
# Modelo Health / Metadata
# ============================================================================

class HealthResponse(BaseModel):
    """Estado de salud de la API y de sus servicios dependientes."""
    status: str = Field(examples=["healthy"])
    service: str = Field(examples=["hipo-refi-cl-api"])
    version: str = Field(examples=["0.1.0"])
    database: str = Field(examples=["duckdb_connected"])
    uf_current: Optional[float] = Field(default=None, description="Valor actual de la UF cargado en memoria")


# ============================================================================
# Modelo para Generación de Informe en PDF
# ============================================================================

class ReportPDFRequest(RefinanceEvaluationRequest):
    """Solicitud de generación de dictamen ejecutivo en PDF formal (Ley 21.236)."""
    client_name: Optional[str] = Field(
        default="Titular Hipotecario",
        description="Nombre del cliente o titular para la carátula del informe",
        examples=["Sebastián Urzúa"],
    )
    operation_number: Optional[str] = Field(
        default=None,
        description="Número de operación o crédito si está disponible",
        examples=["45892019-3"],
    )
    current_bank_name: Optional[str] = Field(
        default="Banco Acreedor Actual",
        description="Nombre del banco o mutuaria acreedora actual",
        examples=["Banco de Chile"],
    )
