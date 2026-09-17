#!/usr/bin/env python3
"""
Script de Demostración y Validación Integral de HipoRefi-CL.
Ejecuta de punta a punta:
1. Extracción de datos de una cartola bancaria de muestra.
2. Consulta de indicadores macroeconómicos y valor de la UF en DuckDB.
3. Desglose normativo de costos de cambio bajo la Ley N° 21.236.
4. Evaluación cuantitativa (VPN, Payback, Ahorro) contra todas las entidades financieras.
5. Demostración práctica de la detección de 'La Falacia del Dividendo'.
"""

import sys
from pathlib import Path

# Asegurar que src esté en el path de importación
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsers.statement_extractor import StatementExtractor
from src.parsers.pdf_reader import PDFReader
from src.scrapers.market_service import MarketDataService
from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator
from src.core.metrics import RefinanceAnalyzer


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def main():
    print_banner("HipoRefi-CL: Demostración de Motor Financiero y Datos de Mercado")

    # -------------------------------------------------------------
    # PASO 1: Ingesta y Extracción Documental de Cartola Hipotecaria
    # -------------------------------------------------------------
    print_banner("1. Extracción Documental de Cartola (PDF en Memoria)")
    sample_statement_lines = [
        "BANCO DE CHILE",
        "COMPROBANTE Y CARTOLA DE DIVIDENDO HIPOTECARIO",
        "Operación N° 45892019-3",
        "Titular: Sebastián Urzúa",
        "Edad: 39 años",
        "Saldo de Capital Insoluto: 3.200,00 UF",
        "Tasa de Interés Anual Pactada: 5,20 %",
        "Dividendo 60 de 240",
        "Dividendo Financiero: 21,50 UF",
        "Seguro Desgravamen: 0,90 UF",
        "Seguro Incendio y Sismo: 0,70 UF",
        "Dividendo Total a Pagar: 23,10 UF",
    ]
    print("-> Generando cartola PDF sintética en memoria...")
    pdf_bytes = PDFReader.create_synthetic_pdf(sample_statement_lines)

    extractor = StatementExtractor(mode="auto")
    extracted_data = extractor.extract_from_pdf(pdf_bytes)

    print("\n[OK] Datos extraídos exitosamente por el Parser:")
    print(f"   • Banco Acreedor Actual : {extracted_data.bank_name}")
    print(f"   • N° de Operación       : {extracted_data.operation_number}")
    print(f"   • Saldo Insoluto        : {extracted_data.current_balance_uf:,.2f} UF")
    print(f"   • Tasa Anual Actual     : {extracted_data.annual_interest_rate_pct:.2f}%")
    print(f"   • Dividendos Restantes  : {extracted_data.remaining_installments} meses (~{extracted_data.remaining_installments/12:.1f} años)")
    print(f"   • Dividendo Actual      : {extracted_data.current_total_dividend_uf:.2f} UF")

    # -------------------------------------------------------------
    # PASO 2: Consulta de Mercado y DuckDB
    # -------------------------------------------------------------
    print_banner("2. Entorno Macroeconómico y Datos de Mercado (DuckDB)")
    market_service = MarketDataService()
    current_uf = market_service.get_current_uf()
    overview = market_service.get_market_overview()

    balance_clp = market_service.convert_uf_to_clp(extracted_data.current_balance_uf)
    dividend_clp = market_service.convert_uf_to_clp(extracted_data.current_total_dividend_uf)

    print(f"   • Valor UF Vigente      : ${current_uf:,.2f} CLP")
    print(f"   • Saldo en Pesos (CLP)  : ${balance_clp:,.0f} CLP")
    print(f"   • Dividendo en Pesos    : ${dividend_clp:,.0f} CLP / mes")

    macro_rates = overview["latest_macro_rates"]
    if "F072.CLP.COL.VIV.Z.M" in macro_rates:
        print(f"   • Tasa Promedio CMF     : {macro_rates['F072.CLP.COL.VIV.Z.M']['value']:.2f}% anual")
    if "F073.TPM.TCM.G01.Z.D" in macro_rates:
        print(f"   • Tasa Política Monet.  : {macro_rates['F073.TPM.TCM.G01.Z.D']['value']:.2f}% (TPM)")

    # -------------------------------------------------------------
    # PASO 3: Costos de Cambio bajo Ley 21.236 y DL 3475
    # -------------------------------------------------------------
    print_banner("3. Costos Operacionales de Portabilidad (Ley 21.236)")
    costs = SwitchingCostCalculator.calculate_total_costs(
        balance_uf=extracted_data.current_balance_uf,
        current_annual_rate=extracted_data.annual_interest_rate_pct / 100.0,
    )
    costs_dict = costs.to_dict()

    print(f"   • Comisión Prepago (LGB Art. 100, máx 1.5 meses int.) : {costs.prepayment_penalty_uf:.2f} UF (${market_service.convert_uf_to_clp(costs.prepayment_penalty_uf):,.0f} CLP)")
    print(f"   • Arancel CBR (Ley 21.236, 50% desc. subrogación)     : {costs.cbr_uf:.2f} UF (${market_service.convert_uf_to_clp(costs.cbr_uf):,.0f} CLP)")
    print(f"   • Tasación Inmueble                                   : {costs.appraisal_uf:.2f} UF")
    print(f"   • Estudio de Títulos                                  : {costs.title_deed_uf:.2f} UF")
    print(f"   • Gastos Notariales                                   : {costs.notary_uf:.2f} UF")
    print(f"   • Impuesto Timbres y Estampillas (D.L. 3475)          : {costs.stamp_tax_uf:.2f} UF (EXENTO)")
    print(f"   -------------------------------------------------------------------")
    print(f"   TOTAL GASTOS DE CIERRE ($G_k$): {costs.total_cost_uf:.2f} UF (${market_service.convert_uf_to_clp(costs.total_cost_uf):,.0f} CLP)")

    # -------------------------------------------------------------
    # PASO 4: Evaluación Cuantitativa del Mercado de Refinanciamiento
    # -------------------------------------------------------------
    print_banner("4. Ranking de Ofertas Bancarias y Ganancia Patrimonial (VPN)")
    evaluation = market_service.evaluate_refinance_against_market(
        current_balance_uf=extracted_data.current_balance_uf,
        current_annual_rate=extracted_data.annual_interest_rate_pct / 100.0,
        months_remaining=extracted_data.remaining_installments,
        current_total_dividend_uf=extracted_data.current_total_dividend_uf,
    )

    print(f"{'Entidad':<20} | {'Tasa':<6} | {'Div. Nuevo (UF)':<15} | {'Ahorro/Mes':<11} | {'VPN (UF)':<10} | {'Payback':<10} | {'Decisión'}")
    print("-" * 95)

    for opp in evaluation["all_opportunities"]:
        quote = opp["bank_quote"]
        eval_metrics = opp["evaluation"]
        bank = quote["bank_name"][:19]
        rate_str = f"{quote['annual_rate_pct']:.2f}%"
        div_str = f"{quote['monthly_total_dividend_uf']:.2f} UF"
        save_str = f"+{eval_metrics['monthly_savings_uf']:.2f} UF"
        npv_str = f"{eval_metrics['npv_uf']:+.1f} UF"
        payback_str = f"{eval_metrics['payback_months']} meses" if eval_metrics['payback_months'] else "> vida"
        flag = eval_metrics["recommendation_flag"]

        print(f"{bank:<20} | {rate_str:<6} | {div_str:<15} | {save_str:<11} | {npv_str:<10} | {payback_str:<10} | {flag}")

    best = evaluation["best_opportunity"]
    print("\n" + "*" * 70)
    print(f"  MEJOR OPCIÓN DETECTADA: {best['bank_quote']['bank_name']}")
    print(f"  • Ganancia Patrimonial Neta (VPN) : +{best['evaluation']['npv_uf']:.2f} UF (~${market_service.convert_uf_to_clp(best['evaluation']['npv_uf']):,.0f} CLP)")
    print(f"  • Ahorro Mensual Inmediato        : {best['evaluation']['monthly_savings_uf']:.2f} UF (${market_service.convert_uf_to_clp(best['evaluation']['monthly_savings_uf']):,.0f} CLP/mes)")
    print(f"  • Plazo de Retorno (Payback)      : {best['evaluation']['payback_months']} meses")
    print(f"  • Dictamen                        : {best['evaluation']['rationale']}")
    print("*" * 70)

    # -------------------------------------------------------------
    # PASO 5: Demostración de Detección de 'La Falacia del Dividendo'
    # -------------------------------------------------------------
    print_banner("5. Prueba de Estrés: 'La Falacia del Dividendo'")
    print("Simulando oferta 'atractiva' que reduce cuota mensual pero alarga plazo de 15 a 25 años:")

    sched_current = FrenchAmortizer.generate_schedule(MortgageParams(
        principal=3200.0,
        annual_rate=0.052,
        months_remaining=180,
    ))
    # Oferta con tasa ligeramente menor pero alargada a 300 meses
    sched_trap = FrenchAmortizer.generate_schedule(MortgageParams(
        principal=3200.0,
        annual_rate=0.049,
        months_remaining=300,
    ))

    trap_eval = RefinanceAnalyzer.evaluate(
        current_schedule=sched_current,
        new_schedule=sched_trap,
        upfront_costs_uf=costs.total_cost_uf,
    )

    div_current = sched_current[0]["total_dividend_uf"]
    div_trap = sched_trap[0]["total_dividend_uf"]

    print(f"   • Dividendo Actual (15 años)          : {div_current:.2f} UF/mes")
    print(f"   • Dividendo 'Oferta Trampa' (25 años) : {div_trap:.2f} UF/mes  (¡Baja cuota en {div_current - div_trap:.2f} UF!)")
    print(f"   • Destrucción Patrimonial Neta (VPN)  : {trap_eval.npv_uf:.2f} UF (${market_service.convert_uf_to_clp(trap_eval.npv_uf):,.0f} CLP)")
    print(f"   • Pérdida Nominal Acumulada           : {trap_eval.total_lifetime_savings_nominal_uf:.2f} UF")
    print(f"   • Semáforo Patrimonial                : [{trap_eval.recommendation_flag}]")
    print(f"   • Explicación                         : {trap_eval.rationale}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
