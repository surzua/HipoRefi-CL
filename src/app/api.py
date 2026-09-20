"""API REST Backend de HipoRefi-CL con FastAPI.

Expone endpoints de simulación de amortización francesa, evaluación cuantitativa
de refinanciamiento patrimonial, costos normativos (Ley 21.236), extracción documental
de cartolas y consulta de datos de mercado en tiempo real.
"""

from typing import Optional, Dict, Any, List
import io
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status, Response
from fastapi.middleware.cors import CORSMiddleware

from src.app.schemas import (
    SimulationRequest,
    SimulationResponse,
    AmortizationRow,
    RefinanceEvaluationRequest,
    RefinanceEvaluationResponse,
    SwitchingCostsDetail,
    RefinanceDecisionDetail,
    OpportunityItem,
    StatementTextRequest,
    StatementExtractionResponse,
    MarketRatesResponse,
    HealthResponse,
    ReportPDFRequest,
    PrepaymentSimulationRequest,
    PrepaymentSimulationResponse,
    PrepaymentOptionResultSchema,
    MixedRateStressRequest,
    MixedRateStressResponse,
    StressScenarioDetail,
    InsurabilityCheckRequest,
    InsurabilityCheckResponse,
    GermanAmortizationRequest,
    GermanSimulationResponse,
    GermanComparisonDetail,
)
from src.core.amortizer import FrenchAmortizer, GermanAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator
from src.core.metrics import RefinanceAnalyzer
from src.core.advanced_financial import (
    PrepaymentSimulator,
    MixedRateRiskAnalyzer,
    LifeInsuranceActuary,
)
from src.scrapers.market_service import MarketDataService
from src.parsers.statement_extractor import StatementExtractor
from src.reports.pdf_generator import ExecutiveReportGenerator


# ============================================================================
# Instanciación y Configuración de FastAPI
# ============================================================================

app = FastAPI(
    title="HipoRefi-CL API",
    description=(
        "Motor Cuantitativo y Plataforma de Optimización de Refinanciamiento Hipotecario en Chile. "
        "Permite simular tablas de desarrollo en UF, evaluar decisiones financieras bajo VPN y Payback, "
        "calcular costos normativos de portabilidad (Ley N° 21.236 / LGB Art. 100) y procesar cartolas bancarias."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configuración de CORS para permitir consumo desde Streamlit, Next.js o clientes locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Inyección de Dependencias
# ============================================================================

_market_service_instance: Optional[MarketDataService] = None
_statement_extractor_instance: Optional[StatementExtractor] = None


def get_market_service() -> MarketDataService:
    """Provee una instancia singleton del servicio de datos de mercado y DuckDB."""
    global _market_service_instance
    if _market_service_instance is None:
        _market_service_instance = MarketDataService()
    return _market_service_instance


def get_statement_extractor() -> StatementExtractor:
    """Provee una instancia del extractor documental de cartolas."""
    global _statement_extractor_instance
    if _statement_extractor_instance is None:
        _statement_extractor_instance = StatementExtractor(mode="auto")
    return _statement_extractor_instance


# ============================================================================
# Endpoints de Salud y Metadatos
# ============================================================================

@app.get(
    "/",
    summary="Raíz de la API",
    tags=["Metadatos"],
)
def root():
    """Información general y bienvenida al servicio de API."""
    return {
        "service": "HipoRefi-CL API",
        "description": "Motor de optimización y evaluación de refinanciamiento hipotecario en Chile",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "simulate": "/api/v1/simulate",
            "simulate_german": "/api/v1/simulate/german",
            "evaluate_refinance": "/api/v1/evaluate-refinance",
            "prepayment_simulate": "/api/v1/prepayment/simulate",
            "mixed_rate_stress": "/api/v1/mixed-rate/stress-test",
            "insurability_check": "/api/v1/insurability/check",
            "extract_statement": "/api/v1/extract-statement",
            "extract_statement_upload": "/api/v1/extract-statement/upload",
            "market_rates": "/api/v1/market-rates",
            "health": "/health",
        },
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check del Servicio",
    tags=["Metadatos"],
)
@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Health Check v1",
    tags=["Metadatos"],
)
def health_check(market_service: MarketDataService = Depends(get_market_service)):
    """Verifica la disponibilidad de la API, conexión a DuckDB y valor actual de la UF."""
    try:
        current_uf = market_service.get_current_uf()
        return HealthResponse(
            status="healthy",
            service="hipo-refi-cl-api",
            version="0.1.0",
            database="duckdb_connected",
            uf_current=current_uf,
        )
    except Exception as e:
        return HealthResponse(
            status=f"degraded: {str(e)}",
            service="hipo-refi-cl-api",
            version="0.1.0",
            database="duckdb_error",
            uf_current=None,
        )


# ============================================================================
# Endpoint 1: Simulación de Crédito Hipotecario Francés
# ============================================================================

@app.post(
    "/api/v1/simulate",
    response_model=SimulationResponse,
    summary="Simular tabla de amortización francesa de un crédito",
    tags=["Simulación Hipotecaria"],
)
def simulate_mortgage(request: SimulationRequest) -> SimulationResponse:
    """
    Calcula el dividendo mensual constante (sistema francés) bajo convención chilena estándar,
    segregando capital, intereses y coberturas de seguros (desgravamen e incendio/sismo).
    Retorna los totales acumulados del crédito y opcionalmente la tabla mes a mes completa.
    """
    try:
        months = request.months or (request.term_years * 12 if request.term_years else 240)
        annual_rate_decimal = request.annual_rate_pct / 100.0

        params = MortgageParams(
            principal=request.principal,
            annual_rate=annual_rate_decimal,
            months_remaining=months,
            fire_insurance_monthly_uf=request.fire_insurance_monthly_uf,
            life_insurance_rate_monthly=request.life_insurance_rate_monthly,
        )

        schedule = FrenchAmortizer.generate_schedule(params)

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fue posible generar la tabla de amortización con los parámetros provistos.",
            )

        # Cálculo de agregados
        first_row = schedule[0]
        financial_dividend = first_row["financial_dividend_uf"]
        initial_total_dividend = first_row["total_dividend_uf"]

        total_interest = sum(row["interest_uf"] for row in schedule)
        total_cost = sum(row["total_dividend_uf"] for row in schedule)
        total_life_ins = sum(row["life_insurance_uf"] for row in schedule)
        total_fire_ins = sum(row["fire_insurance_uf"] for row in schedule)

        amort_rows = None
        if request.include_schedule:
            amort_rows = [AmortizationRow(**row) for row in schedule]

        return SimulationResponse(
            principal_uf=round(request.principal, 4),
            annual_rate_pct=round(request.annual_rate_pct, 4),
            months=months,
            term_years=round(months / 12.0, 2),
            monthly_financial_dividend_uf=round(financial_dividend, 4),
            initial_total_dividend_uf=round(initial_total_dividend, 4),
            total_interest_uf=round(total_interest, 4),
            total_cost_uf=round(total_cost, 4),
            total_life_insurance_uf=round(total_life_ins, 4),
            total_fire_insurance_uf=round(total_fire_ins, 4),
            schedule=amort_rows,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la simulación: {str(e)}",
        )


# ============================================================================
# Endpoint 2: Evaluación Cuantitativa de Refinanciamiento
# ============================================================================

@app.post(
    "/api/v1/evaluate-refinance",
    response_model=RefinanceEvaluationResponse,
    summary="Evaluar conveniencia patrimonial de refinanciamiento (VPN, Payback, Ley 21.236)",
    tags=["Optimización y Refinanciamiento"],
)
def evaluate_refinance(
    request: RefinanceEvaluationRequest,
    market_service: MarketDataService = Depends(get_market_service),
) -> RefinanceEvaluationResponse:
    """
    Evalúa técnica y patrimonialmente la conveniencia de refinanciar un crédito hipotecario vigente.
    
    Capacidades:
    1. Calcula con precisión jurídica los costos de cambio (Ley 21.236, DL 3475, LGB Art. 100).
    2. Si se proporciona `new_loan`: analiza en detalle esa propuesta puntual (VPN, Payback y clasificación).
    3. Si NO se proporciona `new_loan`: simula y contrasta contra la oferta de todos los bancos comerciales
       y mutuarias de Chile, rankeando las mejores oportunidades según mayor VPN para el cliente.
    """
    try:
        current = request.current_loan
        current_rate_dec = current.annual_rate_pct / 100.0
        current_balance = current.balance_uf
        months_remaining = current.months_remaining
        uf_value = market_service.get_current_uf()
        discount_rate_dec = request.annual_discount_rate_pct / 100.0

        # 1. Costos de cambio normativos
        costs = SwitchingCostCalculator.calculate_total_costs(
            balance_uf=current_balance,
            current_annual_rate=current_rate_dec,
            additional_cash_uf=request.additional_cash_uf,
            appraisal_uf=request.custom_appraisal_uf or SwitchingCostCalculator.BASE_APPRAISAL_UF,
            title_deed_uf=request.custom_title_deed_uf or SwitchingCostCalculator.BASE_TITLE_DEED_UF,
            notary_uf=request.custom_notary_uf or SwitchingCostCalculator.BASE_NOTARY_UF,
        )

        switching_costs_detail = SwitchingCostsDetail(
            prepayment_penalty_uf=round(costs.prepayment_penalty_uf, 2),
            appraisal_uf=round(costs.appraisal_uf, 2),
            title_deed_uf=round(costs.title_deed_uf, 2),
            notary_uf=round(costs.notary_uf, 2),
            cbr_uf=round(costs.cbr_uf, 2),
            stamp_tax_uf=round(costs.stamp_tax_uf, 2),
            total_cost_uf=round(costs.total_cost_uf, 2),
            total_cost_clp=round(costs.total_cost_uf * uf_value, 0),
        )

        # 2. Generar tabla de desarrollo del crédito actual
        params_current = MortgageParams(
            principal=current_balance,
            annual_rate=current_rate_dec,
            months_remaining=months_remaining,
            fire_insurance_monthly_uf=current.fire_insurance_monthly_uf,
            life_insurance_rate_monthly=current.life_insurance_rate_monthly,
        )
        current_schedule = FrenchAmortizer.generate_schedule(params_current)
        current_initial_dividend = (
            current.current_total_dividend_uf
            if current.current_total_dividend_uf is not None
            else (current_schedule[0]["total_dividend_uf"] if current_schedule else 0.0)
        )

        current_loan_summary = {
            "balance_uf": current_balance,
            "balance_clp": round(current_balance * uf_value, 0),
            "annual_rate_pct": current.annual_rate_pct,
            "months_remaining": months_remaining,
            "term_remaining_years": round(months_remaining / 12.0, 1),
            "current_dividend_uf": current_initial_dividend,
            "current_dividend_clp": round(current_initial_dividend * uf_value, 0),
        }

        # CASO A: Evaluación de una propuesta específica (new_loan provisto)
        single_eval: Optional[RefinanceDecisionDetail] = None
        if request.new_loan is not None:
            new_offer = request.new_loan
            new_rate_dec = new_offer.annual_rate_pct / 100.0
            new_months = new_offer.months or (new_offer.term_years * 12 if new_offer.term_years else months_remaining)

            # Si se financian los costos, se suman al capital del nuevo préstamo
            new_principal = (
                current_balance + (costs.total_cost_uf if request.finance_costs else 0.0) + request.additional_cash_uf
            )

            params_new = MortgageParams(
                principal=new_principal,
                annual_rate=new_rate_dec,
                months_remaining=new_months,
                fire_insurance_monthly_uf=new_offer.fire_insurance_monthly_uf,
                life_insurance_rate_monthly=new_offer.life_insurance_rate_monthly,
            )
            new_schedule = FrenchAmortizer.generate_schedule(params_new)

            decision = RefinanceAnalyzer.evaluate(
                current_schedule=current_schedule,
                new_schedule=new_schedule,
                upfront_costs_uf=costs.total_cost_uf,
                financed_costs=request.finance_costs,
                annual_discount_rate=discount_rate_dec,
            )

            single_eval = RefinanceDecisionDetail(
                npv_uf=decision.npv_uf,
                npv_clp=round(decision.npv_uf * uf_value, 0),
                payback_months=decision.payback_months,
                monthly_savings_uf=decision.monthly_savings_uf,
                monthly_savings_clp=round(decision.monthly_savings_uf * uf_value, 0),
                total_lifetime_savings_nominal_uf=decision.total_lifetime_savings_nominal_uf,
                total_lifetime_savings_nominal_clp=round(decision.total_lifetime_savings_nominal_uf * uf_value, 0),
                recommendation_flag=decision.recommendation_flag,
                rationale=decision.rationale,
            )

            return RefinanceEvaluationResponse(
                uf_rate_clp=round(uf_value, 2),
                current_loan_summary=current_loan_summary,
                switching_costs=switching_costs_detail,
                single_evaluation=single_eval,
                best_opportunity=None,
                all_opportunities=[],
            )

        # CASO B: Evaluación global contra la oferta de mercado
        target_term = request.target_term_years or max(5, round(months_remaining / 12))
        quotes = market_service.get_bank_quotes(principal_uf=current_balance, term_years=target_term)

        opportunities: List[OpportunityItem] = []
        for q in quotes:
            q_rate_dec = q.annual_rate_pct / 100.0
            q_principal = (
                current_balance + (costs.total_cost_uf if request.finance_costs else 0.0) + request.additional_cash_uf
            )

            params_q = MortgageParams(
                principal=q_principal,
                annual_rate=q_rate_dec,
                months_remaining=target_term * 12,
                fire_insurance_monthly_uf=q.fire_insurance_uf,
                life_insurance_rate_monthly=0.00028,
            )
            q_schedule = FrenchAmortizer.generate_schedule(params_q)

            dec = RefinanceAnalyzer.evaluate(
                current_schedule=current_schedule,
                new_schedule=q_schedule,
                upfront_costs_uf=costs.total_cost_uf,
                financed_costs=request.finance_costs,
                annual_discount_rate=discount_rate_dec,
            )

            opp_item = OpportunityItem(
                institution_name=q.bank_name,
                institution_id=q.bank_id,
                loan_type=q.loan_type,
                annual_rate_pct=round(q.annual_rate_pct, 2),
                term_years=q.term_years,
                monthly_dividend_new_uf=round(q.monthly_total_dividend_uf, 2),
                monthly_dividend_new_clp=round(q.monthly_total_dividend_uf * uf_value, 0),
                estimated_cae_pct=round(q.estimated_cae_pct, 2),
                evaluation=RefinanceDecisionDetail(
                    npv_uf=dec.npv_uf,
                    npv_clp=round(dec.npv_uf * uf_value, 0),
                    payback_months=dec.payback_months,
                    monthly_savings_uf=dec.monthly_savings_uf,
                    monthly_savings_clp=round(dec.monthly_savings_uf * uf_value, 0),
                    total_lifetime_savings_nominal_uf=dec.total_lifetime_savings_nominal_uf,
                    total_lifetime_savings_nominal_clp=round(dec.total_lifetime_savings_nominal_uf * uf_value, 0),
                    recommendation_flag=dec.recommendation_flag,
                    rationale=dec.rationale,
                ),
            )
            opportunities.append(opp_item)

        # Ordenar por mayor VPN
        opportunities.sort(key=lambda x: x.evaluation.npv_uf, reverse=True)
        best_opp = opportunities[0] if opportunities else None

        return RefinanceEvaluationResponse(
            uf_rate_clp=round(uf_value, 2),
            current_loan_summary=current_loan_summary,
            switching_costs=switching_costs_detail,
            single_evaluation=None,
            best_opportunity=best_opp,
            all_opportunities=opportunities,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la evaluación de refinanciamiento: {str(e)}",
        )


# ============================================================================
# Endpoint 3: Extracción de Cartola Hipotecaria (JSON Texto y Subida PDF)
# ============================================================================

@app.post(
    "/api/v1/extract-statement",
    response_model=StatementExtractionResponse,
    summary="Extraer datos estructurados de una cartola desde texto plano",
    tags=["Extracción Documental"],
)
def extract_statement_from_text(
    request: StatementTextRequest,
    extractor: StatementExtractor = Depends(get_statement_extractor),
    market_service: MarketDataService = Depends(get_market_service),
) -> StatementExtractionResponse:
    """Extrae las variables cuantitativas críticas de una cartola a partir del texto plano proporcionado."""
    try:
        extractor.mode = request.mode
        extracted = extractor.extract_from_text(request.text)

        uf_val = market_service.get_current_uf()
        balance_clp = round(extracted.current_balance_uf * uf_val, 0)
        dividend_clp = round(extracted.current_total_dividend_uf * uf_val, 0)

        return StatementExtractionResponse(
            bank_name=extracted.bank_name,
            operation_number=extracted.operation_number,
            current_balance_uf=extracted.current_balance_uf,
            current_balance_clp=balance_clp,
            annual_interest_rate_pct=extracted.annual_interest_rate_pct,
            remaining_installments=extracted.remaining_installments,
            remaining_years=round(extracted.remaining_installments / 12.0, 1),
            total_installments=extracted.total_installments,
            current_total_dividend_uf=extracted.current_total_dividend_uf,
            current_total_dividend_clp=dividend_clp,
            financial_dividend_uf=extracted.financial_dividend_uf,
            life_insurance_uf=extracted.life_insurance_uf,
            fire_insurance_uf=extracted.fire_insurance_uf,
            customer_age_years=extracted.customer_age_years,
            extraction_source=request.mode,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al procesar el texto de la cartola: {str(e)}",
        )


@app.post(
    "/api/v1/extract-statement/upload",
    response_model=StatementExtractionResponse,
    summary="Extraer datos estructurados subiendo un archivo PDF de cartola",
    tags=["Extracción Documental"],
)
async def extract_statement_from_upload(
    file: UploadFile = File(..., description="Archivo PDF de la cartola hipotecaria"),
    mode: str = Form("auto", description="Modo de extracción: 'auto', 'heuristic', 'gemini', 'openai'"),
    extractor: StatementExtractor = Depends(get_statement_extractor),
    market_service: MarketDataService = Depends(get_market_service),
) -> StatementExtractionResponse:
    """Extrae las variables de una cartola directamente desde un archivo PDF subido por multipart/form-data."""
    if not file.filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se aceptan archivos en formato PDF (.pdf).",
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo PDF subido está vacío.",
            )

        extractor.mode = mode
        extracted = extractor.extract_from_pdf(io.BytesIO(content))

        uf_val = market_service.get_current_uf()
        balance_clp = round(extracted.current_balance_uf * uf_val, 0)
        dividend_clp = round(extracted.current_total_dividend_uf * uf_val, 0)

        return StatementExtractionResponse(
            bank_name=extracted.bank_name,
            operation_number=extracted.operation_number,
            current_balance_uf=extracted.current_balance_uf,
            current_balance_clp=balance_clp,
            annual_interest_rate_pct=extracted.annual_interest_rate_pct,
            remaining_installments=extracted.remaining_installments,
            remaining_years=round(extracted.remaining_installments / 12.0, 1),
            total_installments=extracted.total_installments,
            current_total_dividend_uf=extracted.current_total_dividend_uf,
            current_total_dividend_clp=dividend_clp,
            financial_dividend_uf=extracted.financial_dividend_uf,
            life_insurance_uf=extracted.life_insurance_uf,
            fire_insurance_uf=extracted.fire_insurance_uf,
            customer_age_years=extracted.customer_age_years,
            extraction_source=f"pdf_upload_{mode}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al leer o interpretar el documento PDF: {str(e)}",
        )


# ============================================================================
# Endpoint 4: Consulta de Tasas de Mercado y Macroeconómicas
# ============================================================================

@app.get(
    "/api/v1/market-rates",
    response_model=MarketRatesResponse,
    summary="Obtener valor de la UF, tasas de referencia CMF y cotizaciones bancarias",
    tags=["Datos de Mercado"],
)
def get_market_rates(
    refresh: bool = False,
    principal_uf: Optional[float] = None,
    term_years: int = 20,
    market_service: MarketDataService = Depends(get_market_service),
) -> MarketRatesResponse:
    """
    Retorna los indicadores macroeconómicos clave de Chile:
    - Valor actual de la UF en CLP.
    - Tasas estadísticas oficiales de la CMF.
    - Series observadas del Banco Central (TPM, tasas promedio hipotecarias).
    - Opcionalmente, cotizaciones simuladas de bancos para un monto y plazo dados.
    """
    try:
        uf_val = market_service.get_current_uf(force_refresh=refresh)
        overview = market_service.get_market_overview()

        bank_quotes_dict: Optional[List[Dict[str, Any]]] = None
        if principal_uf is not None and principal_uf > 0:
            quotes = market_service.get_bank_quotes(principal_uf=principal_uf, term_years=term_years)
            bank_quotes_dict = [q.to_dict() for q in quotes]

        return MarketRatesResponse(
            uf_current=round(uf_val, 2),
            tpm_current=round(overview.get("tpm_current", 4.50), 2),
            uf_source="Live API / DuckDB",
            latest_macro_rates=overview.get("latest_macro_rates", {}),
            cmf_benchmarks=overview.get("cmf_benchmarks", {}),
            bank_quotes=bank_quotes_dict,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar datos de mercado: {str(e)}",
        )


@app.post(
    "/api/v1/market-rates/sync",
    summary="Forzar sincronización de indicadores macroeconómicos y UF",
    tags=["Datos de Mercado"],
)
def sync_market_rates(market_service: MarketDataService = Depends(get_market_service)):
    """Ejecuta sincronización activa de la UF y series del Banco Central en DuckDB."""
    try:
        result = market_service.sync_from_central_bank()
        return {
            "status": "success",
            "sync_result": result,
            "uf_current": market_service.get_current_uf(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallo en la sincronización: {str(e)}",
        )


@app.post(
    "/api/v1/reports/pdf",
    summary="Generar Dictamen Ejecutivo y Reporte Técnico en PDF (Ley 21.236)",
    tags=["Reportabilidad"],
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Documento PDF binario con el dictamen de portabilidad hipotecaria.",
        }
    },
)
def generate_evaluation_pdf_report(
    request: ReportPDFRequest,
    market_service: MarketDataService = Depends(get_market_service),
):
    """
    Genera un dictamen formal descargable en PDF de 2 páginas que incluye:
    1. Ficha del deudor y crédito hipotecario vigente.
    2. Semáforo y recomendación patrimonial (VPN en UF y CLP, Ahorro mensual, Payback).
    3. Desglose normativo de costos de cambio (Ley N° 21.236, DL 3475, LGB Art. 100).
    4. Gráfico vectorial de la curva de Break-Even / Payback dinámico.
    5. Benchmark de alternativas de mercado y cláusulas metodológicas.
    """
    try:
        # Ejecutar evaluación cuantitativa
        eval_resp = evaluate_refinance(request, market_service)
        uf_val = market_service.get_current_uf()
        curr = request.current_loan
        curr_summary = eval_resp.current_loan_summary

        # Determinar propuesta evaluada (personalizada o mejor del mercado)
        if request.new_loan is not None and eval_resp.single_evaluation is not None:
            decision = eval_resp.single_evaluation
            target_bank = request.new_loan.institution_name or "Propuesta Evaluada"
            new_rate = request.new_loan.annual_rate_pct
            new_months = request.new_loan.months or (
                request.new_loan.term_years * 12 if request.new_loan.term_years else curr.months_remaining
            )
            new_div_uf = curr_summary.get("current_dividend_uf", 0.0) - decision.monthly_savings_uf
        elif eval_resp.best_opportunity is not None:
            best_opp = eval_resp.best_opportunity
            decision = best_opp.evaluation
            target_bank = best_opp.institution_name
            new_rate = best_opp.annual_rate_pct
            new_months = best_opp.term_years * 12
            new_div_uf = best_opp.monthly_dividend_new_uf
        else:
            decision = RefinanceDecisionDetail(
                npv_uf=0.0,
                npv_clp=0.0,
                payback_months=None,
                monthly_savings_uf=0.0,
                monthly_savings_clp=0.0,
                total_lifetime_savings_nominal_uf=0.0,
                total_lifetime_savings_nominal_clp=0.0,
                recommendation_flag="NO_CONVIENE",
                rationale="No se identificaron alternativas convenientes en el mercado.",
            )
            target_bank = "Mercado General"
            new_rate = curr.annual_rate_pct
            new_months = curr.months_remaining
            new_div_uf = curr_summary.get("current_dividend_uf", 0.0)

        market_opps_list = []
        for opp in eval_resp.all_opportunities:
            market_opps_list.append({
                "bank_name": opp.institution_name,
                "annual_rate_pct": opp.annual_rate_pct,
                "monthly_dividend_uf": opp.monthly_dividend_new_uf,
                "monthly_savings_clp": opp.evaluation.monthly_savings_clp,
                "npv_uf": opp.evaluation.npv_uf,
                "payback_months": opp.evaluation.payback_months,
                "recommendation_flag": opp.evaluation.recommendation_flag,
            })

        pdf_data = {
            "client_name": request.client_name or "Titular Hipotecario",
            "operation_number": request.operation_number,
            "current_bank": request.current_bank_name or "Banco Acreedor Actual",
            "uf_value": uf_val,
            "current_balance_uf": curr.balance_uf,
            "current_rate_pct": curr.annual_rate_pct,
            "months_remaining": curr.months_remaining,
            "current_total_dividend_uf": curr_summary.get("current_dividend_uf", 0.0),
            "current_dividend_clp": curr_summary.get("current_dividend_clp", 0.0),
            "target_bank": target_bank,
            "new_rate_pct": new_rate,
            "new_months": new_months,
            "new_dividend_uf": new_div_uf,
            "new_dividend_clp": new_div_uf * uf_val,
            "recommendation_flag": decision.recommendation_flag,
            "rationale": decision.rationale,
            "npv_uf": decision.npv_uf,
            "npv_clp": decision.npv_clp,
            "monthly_savings_uf": decision.monthly_savings_uf,
            "monthly_savings_clp": decision.monthly_savings_clp,
            "payback_months": decision.payback_months,
            "discount_rate_pct": request.annual_discount_rate_pct,
            "switching_costs": eval_resp.switching_costs.model_dump(),
            "market_opportunities": market_opps_list,
        }

        pdf_bytes = ExecutiveReportGenerator.generate_pdf(pdf_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=dictamen_hiporefi_cl.pdf"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar dictamen en PDF: {str(e)}",
        )


# ============================================================================
# Endpoints de Hito 8: Módulo Financiero y Normativo Avanzado
# ============================================================================

@app.post(
    "/api/v1/prepayment/simulate",
    response_model=PrepaymentSimulationResponse,
    summary="Simular abono extraordinario o prepago parcial (LGB Art. 100)",
    tags=["Finanzas Avanzadas & Prepagos"],
)
def simulate_prepayment(
    request: PrepaymentSimulationRequest,
    market_service: MarketDataService = Depends(get_market_service),
) -> PrepaymentSimulationResponse:
    """
    Evalúa el impacto cuantitativo y regulatorio de un abono extraordinario:
    1. Calcula la comisión de prepago según Ley General de Bancos Art. 100.
    2. Modela la Opción 1: Reducción de Plazo (manteniendo dividendo actual).
    3. Modela la Opción 2: Reducción de Dividendo (manteniendo plazo actual).
    4. Compara el ahorro en intereses (UF y CLP), VPN de la inyección y genera recomendación.
    """
    try:
        uf_val = market_service.get_current_uf()
        annual_rate_dec = request.annual_rate_pct / 100.0
        disc_rate_dec = request.annual_discount_rate_pct / 100.0

        eval_res = PrepaymentSimulator.simulate(
            balance_uf=request.balance_uf,
            annual_rate=annual_rate_dec,
            months_remaining=request.months_remaining,
            prepayment_amount_uf=request.prepayment_amount_uf,
            fire_insurance_monthly_uf=request.fire_insurance_monthly_uf,
            life_insurance_rate_monthly=request.life_insurance_rate_monthly,
            annual_discount_rate=disc_rate_dec,
            penalty_months=request.penalty_months,
        )

        opt_term = eval_res.reduce_term_option
        opt_div = eval_res.reduce_dividend_option

        term_schema = PrepaymentOptionResultSchema(
            modality=opt_term.modality,
            new_months=opt_term.new_months,
            months_saved=opt_term.months_saved,
            new_monthly_dividend_uf=round(opt_term.new_monthly_dividend_uf, 4),
            new_monthly_dividend_clp=round(opt_term.new_monthly_dividend_uf * uf_val, 0),
            monthly_dividend_saving_uf=round(opt_term.monthly_dividend_saving_uf, 4),
            monthly_dividend_saving_clp=round(opt_term.monthly_dividend_saving_uf * uf_val, 0),
            total_interest_paid_uf=round(opt_term.total_interest_paid_uf, 4),
            interest_savings_uf=round(opt_term.interest_savings_uf, 4),
            interest_savings_clp=round(opt_term.interest_savings_uf * uf_val, 0),
            interest_savings_pct=round(opt_term.interest_savings_pct, 2),
            total_cost_uf=round(opt_term.total_cost_uf, 4),
            npv_uf=round(opt_term.npv_uf, 2),
            npv_clp=round(opt_term.npv_uf * uf_val, 0),
        )

        div_schema = PrepaymentOptionResultSchema(
            modality=opt_div.modality,
            new_months=opt_div.new_months,
            months_saved=opt_div.months_saved,
            new_monthly_dividend_uf=round(opt_div.new_monthly_dividend_uf, 4),
            new_monthly_dividend_clp=round(opt_div.new_monthly_dividend_uf * uf_val, 0),
            monthly_dividend_saving_uf=round(opt_div.monthly_dividend_saving_uf, 4),
            monthly_dividend_saving_clp=round(opt_div.monthly_dividend_saving_uf * uf_val, 0),
            total_interest_paid_uf=round(opt_div.total_interest_paid_uf, 4),
            interest_savings_uf=round(opt_div.interest_savings_uf, 4),
            interest_savings_clp=round(opt_div.interest_savings_uf * uf_val, 0),
            interest_savings_pct=round(opt_div.interest_savings_pct, 2),
            total_cost_uf=round(opt_div.total_cost_uf, 4),
            npv_uf=round(opt_div.npv_uf, 2),
            npv_clp=round(opt_div.npv_uf * uf_val, 0),
        )

        return PrepaymentSimulationResponse(
            uf_value_clp=round(uf_val, 2),
            original_balance_uf=round(eval_res.original_balance_uf, 4),
            prepayment_amount_uf=round(eval_res.prepayment_amount_uf, 4),
            prepayment_amount_clp=round(eval_res.prepayment_amount_uf * uf_val, 0),
            prepayment_penalty_uf=round(eval_res.prepayment_penalty_uf, 4),
            prepayment_penalty_clp=round(eval_res.prepayment_penalty_uf * uf_val, 0),
            total_cash_outlay_uf=round(eval_res.total_cash_outlay_uf, 4),
            total_cash_outlay_clp=round(eval_res.total_cash_outlay_uf * uf_val, 0),
            new_balance_uf=round(eval_res.new_balance_uf, 4),
            original_months=eval_res.original_months,
            original_dividend_uf=round(eval_res.original_dividend_uf, 4),
            original_dividend_clp=round(eval_res.original_dividend_uf * uf_val, 0),
            reduce_term_option=term_schema,
            reduce_dividend_option=div_schema,
            best_recommendation=eval_res.best_recommendation,
            rationale=eval_res.rationale,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error en simulación de prepago: {str(e)}")


@app.post(
    "/api/v1/mixed-rate/stress-test",
    response_model=MixedRateStressResponse,
    summary="Matriz de estrés para crédito de tasa mixta vs. tasa fija",
    tags=["Finanzas Avanzadas & Tasa Mixta"],
)
def evaluate_mixed_rate_stress(
    request: MixedRateStressRequest,
    market_service: MarketDataService = Depends(get_market_service),
) -> MixedRateStressResponse:
    """
    Evalúa la conveniencia patrimonial de una tasa mixta (tramo fijo inicial a 3 o 5 años)
    frente a un crédito 100% fijo, sometiendo el período variable a 4 escenarios de estrés
    (Bajista -150 bps, Base, Alcista +150 bps, Severo +300 bps) y calculando la Tasa de Quiebre.
    """
    try:
        uf_val = market_service.get_current_uf()

        res = MixedRateRiskAnalyzer.evaluate(
            principal_uf=request.principal_uf,
            total_months=request.total_months,
            fixed_period_months=request.fixed_period_months,
            initial_fixed_rate_pct=request.initial_fixed_rate_pct,
            baseline_subsequent_rate_pct=request.baseline_subsequent_rate_pct,
            pure_fixed_rate_pct=request.pure_fixed_rate_pct,
            fire_insurance_monthly_uf=request.fire_insurance_monthly_uf,
            life_insurance_rate_monthly=request.life_insurance_rate_monthly,
            annual_discount_rate_pct=request.annual_discount_rate_pct,
        )

        scenarios_detail = []
        for s in res.scenarios:
            scenarios_detail.append(StressScenarioDetail(
                scenario_name=s.scenario_name,
                rate_change_bps=s.rate_change_bps,
                variable_annual_rate_pct=s.variable_annual_rate_pct,
                initial_dividend_uf=s.initial_dividend_uf,
                subsequent_dividend_uf=s.subsequent_dividend_uf,
                dividend_jump_uf=s.dividend_jump_uf,
                dividend_jump_pct=s.dividend_jump_pct,
                total_cost_uf=s.total_cost_uf,
                total_interest_uf=s.total_interest_uf,
                npv_vs_fixed_uf=s.npv_vs_fixed_uf,
                npv_vs_fixed_clp=round(s.npv_vs_fixed_uf * uf_val, 0),
            ))

        return MixedRateStressResponse(
            uf_value_clp=round(uf_val, 2),
            principal_uf=res.principal_uf,
            total_months=res.total_months,
            fixed_period_months=res.fixed_period_months,
            initial_fixed_rate_pct=res.initial_fixed_rate_pct,
            baseline_subsequent_rate_pct=res.baseline_subsequent_rate_pct,
            pure_fixed_rate_pct=res.pure_fixed_rate_pct,
            pure_fixed_dividend_uf=res.pure_fixed_dividend_uf,
            pure_fixed_total_interest_uf=res.pure_fixed_total_interest_uf,
            pure_fixed_total_cost_uf=res.pure_fixed_total_cost_uf,
            breakeven_variable_rate_pct=res.breakeven_variable_rate_pct,
            scenarios=scenarios_detail,
            recommendation_summary=res.recommendation_summary,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error en estrés de tasa mixta: {str(e)}")


@app.post(
    "/api/v1/insurability/check",
    response_model=InsurabilityCheckResponse,
    summary="Evaluar asegurabilidad actuarial de desgravamen y topes de edad",
    tags=["Finanzas Avanzadas & Asegurabilidad"],
)
def check_insurability(request: InsurabilityCheckRequest) -> InsurabilityCheckResponse:
    """
    Determina la condición de asegurabilidad técnica al término del crédito según la edad
    del titular, calculando la prima de desgravamen por tramos y generando alertas regulatorias.
    """
    try:
        eval_ins = LifeInsuranceActuary.evaluate_insurability(
            current_age=request.current_age,
            loan_term_years=request.loan_term_years,
        )
        return InsurabilityCheckResponse(
            current_age=eval_ins.current_age,
            loan_term_years=eval_ins.loan_term_years,
            maturity_age=eval_ins.maturity_age,
            initial_monthly_rate=eval_ins.initial_monthly_rate,
            final_monthly_rate=eval_ins.final_monthly_rate,
            status=eval_ins.status,
            risk_level=eval_ins.risk_level,
            is_insurable=eval_ins.is_insurable,
            medical_requirements=eval_ins.medical_requirements,
            regulatory_alert=eval_ins.regulatory_alert,
            age_bracket_table=eval_ins.age_bracket_table,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error en asegurabilidad: {str(e)}")


@app.post(
    "/api/v1/simulate/german",
    response_model=GermanSimulationResponse,
    summary="Simular crédito hipotecario bajo sistema alemán (cuota decreciente)",
    tags=["Simulación Hipotecaria"],
)
def simulate_german_mortgage(request: GermanAmortizationRequest) -> GermanSimulationResponse:
    """
    Simula un crédito bajo el sistema alemán (amortización fija de capital y dividendos decrecientes),
    comparándolo detalladamente frente al sistema francés tradicional bajo las mismas condiciones.
    """
    try:
        months = request.months or (request.term_years * 12 if request.term_years else 240)
        annual_rate_dec = request.annual_rate_pct / 100.0

        params = MortgageParams(
            principal=request.principal,
            annual_rate=annual_rate_dec,
            months_remaining=months,
            fire_insurance_monthly_uf=request.fire_insurance_monthly_uf,
            life_insurance_rate_monthly=request.life_insurance_rate_monthly,
        )

        schedule = GermanAmortizer.generate_schedule(params)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fue posible generar la tabla alemana con los parámetros indicados.",
            )

        comp = GermanAmortizer.compare_french_vs_german(params)
        fixed_amort = request.principal / months

        first_row = schedule[0]
        last_row = schedule[-1]
        total_interest = sum(r["interest_uf"] for r in schedule)
        total_cost = sum(r["total_dividend_uf"] for r in schedule)

        amort_rows = None
        if request.include_schedule:
            amort_rows = [AmortizationRow(**row) for row in schedule]

        return GermanSimulationResponse(
            principal_uf=round(request.principal, 4),
            annual_rate_pct=round(request.annual_rate_pct, 4),
            months=months,
            term_years=round(months / 12.0, 2),
            fixed_principal_amortization_uf=round(fixed_amort, 4),
            initial_total_dividend_uf=round(first_row["total_dividend_uf"], 4),
            final_total_dividend_uf=round(last_row["total_dividend_uf"], 4),
            total_interest_uf=round(total_interest, 4),
            total_cost_uf=round(total_cost, 4),
            comparison_with_french=GermanComparisonDetail(**comp),
            schedule=amort_rows,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error en simulación alemana: {str(e)}")


# ============================================================================
# Ejecución Directa para Desarrollo Local
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.app.api:app", host="0.0.0.0", port=8000, reload=True)

