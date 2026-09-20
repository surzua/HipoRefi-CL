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


# ============================================================================
# Modelos para Hito 8: Módulo Financiero y Normativo Avanzado
# ============================================================================

# --- 1. Prepagos y Abonos Extraordinarios ---

class PrepaymentSimulationRequest(BaseModel):
    """Solicitud para evaluar un abono extraordinario (prepago parcial) bajo LGB Art. 100."""
    balance_uf: float = Field(..., gt=0, description="Saldo insoluto actual en UF", examples=[3000.0])
    annual_rate_pct: float = Field(..., gt=0, le=30.0, description="Tasa anual en %", examples=[4.80])
    months_remaining: int = Field(..., gt=0, le=480, description="Plazo restante en meses", examples=[180])
    prepayment_amount_uf: float = Field(..., gt=0, description="Monto del abono extraordinario en UF", examples=[300.0])
    fire_insurance_monthly_uf: float = Field(default=0.0, ge=0, description="Seguro de incendio y sismo mensual en UF")
    life_insurance_rate_monthly: float = Field(default=0.00028, ge=0, description="Tasa mensual seguro de desgravamen")
    annual_discount_rate_pct: float = Field(default=2.5, ge=0, description="Tasa anual de descuento en UF (%)")
    penalty_months: float = Field(default=1.5, ge=0, le=3.0, description="Meses de intereses para comisión de prepago (máx 1.5 por ley)")


class PrepaymentOptionResultSchema(BaseModel):
    """Resultados cuantitativos para una modalidad de prepago."""
    modality: str = Field(description="Modalidad: REDUCE_TERM o REDUCE_DIVIDEND")
    new_months: int = Field(description="Nuevo plazo restante en meses")
    months_saved: int = Field(description="Meses totales ahorrados")
    new_monthly_dividend_uf: float = Field(description="Nuevo dividendo mensual total en UF")
    new_monthly_dividend_clp: float = Field(description="Nuevo dividendo mensual total en CLP")
    monthly_dividend_saving_uf: float = Field(description="Ahorro mensual en dividendo en UF")
    monthly_dividend_saving_clp: float = Field(description="Ahorro mensual en dividendo en CLP")
    total_interest_paid_uf: float = Field(description="Total de intereses que se pagarán tras el prepago")
    interest_savings_uf: float = Field(description="Intereses totales ahorrados en UF")
    interest_savings_clp: float = Field(description="Intereses totales ahorrados en CLP")
    interest_savings_pct: float = Field(description="Porcentaje de ahorro en intereses respecto al escenario base")
    total_cost_uf: float = Field(description="Costo total de dividendos restantes en UF")
    npv_uf: float = Field(description="Valor Presente Neto descontado del prepago en UF")
    npv_clp: float = Field(description="Valor Presente Neto descontado del prepago en CLP")


class PrepaymentSimulationResponse(BaseModel):
    """Respuesta completa comparativa del simulador de prepagos parciales."""
    uf_value_clp: float = Field(description="Valor vigente de la UF")
    original_balance_uf: float = Field(description="Saldo insoluto antes del prepago")
    prepayment_amount_uf: float = Field(description="Monto inyectado en UF")
    prepayment_amount_clp: float = Field(description="Monto inyectado en CLP")
    prepayment_penalty_uf: float = Field(description="Comisión legal de prepago (Art. 100 LGB) en UF")
    prepayment_penalty_clp: float = Field(description="Comisión legal de prepago en CLP")
    total_cash_outlay_uf: float = Field(description="Desembolso total requerido (abono + comisión) en UF")
    total_cash_outlay_clp: float = Field(description="Desembolso total requerido en CLP")
    new_balance_uf: float = Field(description="Nuevo saldo insoluto post-abono")
    original_months: int = Field(description="Plazo original restante en meses")
    original_dividend_uf: float = Field(description="Dividendo mensual previo en UF")
    original_dividend_clp: float = Field(description="Dividendo mensual previo en CLP")
    reduce_term_option: PrepaymentOptionResultSchema = Field(description="Opción 1: Reducir plazo manteniendo dividendo")
    reduce_dividend_option: PrepaymentOptionResultSchema = Field(description="Opción 2: Reducir dividendo manteniendo plazo")
    best_recommendation: str = Field(description="Opción recomendada cuantitativamente")
    rationale: str = Field(description="Fundamento técnico y patrimonial de la recomendación")


# --- 2. Modelado de Riesgo de Tasa Mixta vs. Fija ---

class MixedRateStressRequest(BaseModel):
    """Parámetros de entrada para simulación y estrés de crédito con tasa mixta."""
    principal_uf: float = Field(..., gt=0, description="Monto del préstamo en UF", examples=[3200.0])
    total_months: int = Field(..., gt=0, le=480, description="Plazo total en meses", examples=[240])
    fixed_period_months: int = Field(default=36, gt=0, description="Meses del período inicial a tasa fija", examples=[36])
    initial_fixed_rate_pct: float = Field(..., gt=0, le=30.0, description="Tasa fija del período inicial en %", examples=[3.90])
    baseline_subsequent_rate_pct: float = Field(..., gt=0, le=30.0, description="Tasa esperada de mercado para período variable en %", examples=[4.80])
    pure_fixed_rate_pct: float = Field(..., gt=0, le=30.0, description="Tasa de crédito 100% fijo de contraste en %", examples=[4.60])
    fire_insurance_monthly_uf: float = Field(default=0.0, ge=0, description="Seguro mensual de incendio")
    life_insurance_rate_monthly: float = Field(default=0.00028, ge=0, description="Tasa mensual desgravamen")
    annual_discount_rate_pct: float = Field(default=2.5, ge=0, description="Tasa anual de descuento en UF (%)")


class StressScenarioDetail(BaseModel):
    """Métricas resultantes para un escenario de estrés de tasa mixta."""
    scenario_name: str = Field(description="Nombre descriptivo del escenario")
    rate_change_bps: int = Field(description="Variación en puntos básicos (bps)")
    variable_annual_rate_pct: float = Field(description="Tasa anual efectiva aplicada en el tramo variable (%)")
    initial_dividend_uf: float = Field(description="Dividendo mensual durante el tramo fijo en UF")
    subsequent_dividend_uf: float = Field(description="Nuevo dividendo mensual durante el tramo variable en UF")
    dividend_jump_uf: float = Field(description="Salto absoluto en dividendo al reiniciar tasa en UF")
    dividend_jump_pct: float = Field(description="Variación porcentual en dividendo")
    total_cost_uf: float = Field(description="Costo total de los dividendos en el crédito")
    total_interest_uf: float = Field(description="Total de intereses pagados")
    npv_vs_fixed_uf: float = Field(description="VPN comparado contra crédito 100% fijo (UF)")
    npv_vs_fixed_clp: float = Field(description="VPN comparado contra crédito 100% fijo (CLP)")


class MixedRateStressResponse(BaseModel):
    """Respuesta de la matriz de estrés y punto de equilibrio de tasa mixta."""
    uf_value_clp: float = Field(description="Valor vigente de la UF")
    principal_uf: float = Field(description="Monto financiado")
    total_months: int = Field(description="Plazo en meses")
    fixed_period_months: int = Field(description="Meses fijos iniciales")
    initial_fixed_rate_pct: float = Field(description="Tasa del período fijo (%)")
    baseline_subsequent_rate_pct: float = Field(description="Tasa variable base (%)")
    pure_fixed_rate_pct: float = Field(description="Tasa del crédito 100% fijo de referencia (%)")
    pure_fixed_dividend_uf: float = Field(description="Dividendo mensual constante del crédito fijo puro")
    pure_fixed_total_interest_uf: float = Field(description="Intereses totales del crédito fijo puro")
    pure_fixed_total_cost_uf: float = Field(description="Costo total del crédito fijo puro")
    breakeven_variable_rate_pct: float = Field(description="Tasa variable de quiebre (Breakeven Rate) en %")
    scenarios: List[StressScenarioDetail] = Field(description="Resultados en cada uno de los 4 escenarios de estrés")
    recommendation_summary: str = Field(description="Dictamen cuantitativo del riesgo asumido")


# --- 3. Asegurabilidad y Curva Actuarial de Desgravamen ---

class InsurabilityCheckRequest(BaseModel):
    """Solicitud de validación actuarial y topes de asegurabilidad por edad."""
    current_age: int = Field(..., ge=18, le=95, description="Edad actual del titular", examples=[42])
    loan_term_years: int = Field(..., gt=0, le=40, description="Plazo solicitado del crédito en años", examples=[25])


class InsurabilityCheckResponse(BaseModel):
    """Diagnóstico de asegurabilidad según estándares de la banca y aseguradoras en Chile."""
    current_age: int = Field(description="Edad actual del deudor")
    loan_term_years: int = Field(description="Plazo del crédito en años")
    maturity_age: int = Field(description="Edad que tendrá el deudor al vencer el crédito")
    initial_monthly_rate: float = Field(description="Tasa mensual inicial de desgravamen según tramo")
    final_monthly_rate: float = Field(description="Tasa mensual estimada de desgravamen al final del crédito")
    status: str = Field(description="ESTÁNDAR, OBSERVACIÓN, RESTRICCIÓN_MÉDICA o INASEGURABLE")
    risk_level: str = Field(description="BAJO, MEDIO, ALTO o CRÍTICO")
    is_insurable: bool = Field(description="Indica si la operación es asegurable bajo normas habituales")
    medical_requirements: List[str] = Field(description="Requisitos y exámenes de suscripción esperados")
    regulatory_alert: str = Field(description="Notificación técnica de cumplimiento de políticas")
    age_bracket_table: List[Dict[str, Any]] = Field(description="Tabla de referencia de primas por tramo etario")


# --- 4. Amortización Alemana (Cuota Decreciente) ---

class GermanAmortizationRequest(BaseModel):
    """Solicitud de simulación de crédito hipotecario bajo sistema alemán."""
    principal: float = Field(..., gt=0, description="Monto en UF", examples=[3200.0])
    annual_rate_pct: float = Field(..., gt=0, le=30.0, description="Tasa de interés anual (%)", examples=[4.5])
    months: Optional[int] = Field(default=None, gt=0, le=480, description="Plazo en meses")
    term_years: Optional[int] = Field(default=None, gt=0, le=40, description="Plazo en años")
    fire_insurance_monthly_uf: float = Field(default=0.0, ge=0, description="Seguro de incendio mensual en UF")
    life_insurance_rate_monthly: float = Field(default=0.00028, ge=0, description="Tasa mensual seguro de desgravamen")
    include_schedule: bool = Field(default=True, description="Incluir tabla mes a mes")

    @model_validator(mode="after")
    def validate_term(self) -> "GermanAmortizationRequest":
        if self.months is None and self.term_years is None:
            raise ValueError("Debe proporcionar al menos 'months' o 'term_years'.")
        if self.months is None and self.term_years is not None:
            self.months = self.term_years * 12
        return self


class GermanComparisonDetail(BaseModel):
    """Comparativa cuantitativa entre amortización alemana y francesa."""
    french_initial_total_dividend_uf: float = Field(description="Primer dividendo en sistema francés")
    german_initial_total_dividend_uf: float = Field(description="Primer dividendo en sistema alemán (más alto)")
    german_final_total_dividend_uf: float = Field(description="Último dividendo en sistema alemán (más bajo)")
    initial_dividend_diff_uf: float = Field(description="Diferencia inicial de dividendo (Alemán - Francés)")
    french_total_interest_uf: float = Field(description="Total de intereses pagados en sistema francés")
    german_total_interest_uf: float = Field(description="Total de intereses pagados en sistema alemán")
    interest_savings_uf: float = Field(description="Ahorro total de intereses eligiendo el sistema alemán")
    interest_savings_pct: float = Field(description="Porcentaje de ahorro de intereses")
    french_total_cost_uf: float = Field(description="Costo total acumulado en sistema francés")
    german_total_cost_uf: float = Field(description="Costo total acumulado en sistema alemán")


class GermanSimulationResponse(BaseModel):
    """Respuesta de simulación bajo sistema alemán y benchmark frente a sistema francés."""
    principal_uf: float = Field(description="Monto en UF")
    annual_rate_pct: float = Field(description="Tasa anual (%)")
    months: int = Field(description="Plazo en meses")
    term_years: float = Field(description="Plazo en años")
    fixed_principal_amortization_uf: float = Field(description="Amortización mensual fija de capital")
    initial_total_dividend_uf: float = Field(description="Primer dividendo total (más alto)")
    final_total_dividend_uf: float = Field(description="Último dividendo total (más bajo)")
    total_interest_uf: float = Field(description="Total de intereses pagados")
    total_cost_uf: float = Field(description="Costo total de dividendos pagados")
    comparison_with_french: GermanComparisonDetail = Field(description="Comparación directa frente al sistema francés")
    schedule: Optional[List[AmortizationRow]] = Field(default=None, description="Tabla mes a mes si fue solicitada")

