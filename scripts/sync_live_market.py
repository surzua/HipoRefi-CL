#!/usr/bin/env python3
"""Script CLI para sincronización en vivo de tasas y cotizaciones bancarias con Playwright.

Ejecuta scrapers headless sobre los cotizadores públicos de BancoEstado, Santander y BCI,
extrayendo dividendos brutos, primas de seguros y CAE informada, y actualizando
la tabla `bank_offers` en DuckDB.

Uso:
    python scripts/sync_live_market.py --principal 3200 --term 20
    python scripts/sync_live_market.py --dry-run
    python scripts/sync_live_market.py --banks bancoestado,santander --json
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import datetime

# Asegurar importación de src
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data.market_store import MarketDataStore
from src.scrapers.cmf_client import CMFClient
from src.scrapers.headless_scrapers import HeadlessMarketScraperCoordinator


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sincronización en vivo de cotizadores hipotecarios bancarios con Playwright."
    )
    parser.add_argument(
        "--principal",
        type=float,
        default=3200.0,
        help="Monto del crédito en UF (default: 3200.0 UF)",
    )
    parser.add_argument(
        "--term",
        type=int,
        default=20,
        help="Plazo del crédito en años (default: 20 años)",
    )
    parser.add_argument(
        "--property-value",
        type=float,
        default=None,
        help="Valor de la propiedad en UF (default: principal / 0.80)",
    )
    parser.add_argument(
        "--banks",
        type=str,
        default="bancoestado,santander,bci",
        help="Lista de bancos separados por coma (ej: bancoestado,santander,bci)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Ejecutar Chromium en modo headless (default: True)",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Ejecutar Chromium con interfaz gráfica visible",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=35000,
        help="Timeout en milisegundos por simulación (default: 35000 ms)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=MarketDataStore.DEFAULT_DB_PATH,
        help="Ruta al archivo DuckDB (default: data/market_rates.duckdb)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo ejecuta el scraping y muestra resultados en consola sin guardar en DuckDB",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime la salida en formato JSON estructurado",
    )
    return parser.parse_args()


def print_table(quotes, benchmark_rate):
    header = (
        f"{'Banco':<28} | {'Plazo':<5} | {'Tasa %':<7} | {'Div. Bruto':<10} | "
        f"{'Seguros':<8} | {'Div. Total':<10} | {'CAE %':<6} | {'Fuente':<18}"
    )
    separator = "-" * len(header)
    print("\n" + "=" * len(header))
    print(f"📊 RESULTADOS DE COTIZACIÓN HIPOTECARIA EN VIVO (Benchmark CMF: {benchmark_rate:.2f}%)")
    print("=" * len(header))
    print(header)
    print(separator)

    for q in quotes:
        ins_total = q.fire_insurance_uf + q.life_insurance_uf
        print(
            f"{q.bank_name:<28} | "
            f"{q.term_years}a    | "
            f"{q.annual_rate_pct:>6.2f}% | "
            f"{q.monthly_financial_dividend_uf:>8.3f} UF | "
            f"{ins_total:>6.3f} UF | "
            f"{q.monthly_total_dividend_uf:>8.3f} UF | "
            f"{q.cae_pct:>5.2f}% | "
            f"{q.source:<18}"
        )
    print(separator + "\n")


def main():
    args = parse_args()
    bank_list = [b.strip().lower() for b in args.banks.split(",") if b.strip()]

    if not args.json:
        print(f"🚀 Iniciando scraping en vivo para: {', '.join(bank_list)}")
        print(f"💰 Parámetros: Principal = {args.principal:,.0f} UF, Plazo = {args.term} años")

    cmf = CMFClient()
    avg_rate = cmf.get_average_rate("bancos")

    coordinator = HeadlessMarketScraperCoordinator(
        headless=args.headless,
        timeout_ms=args.timeout,
    )

    if args.dry_run:
        quotes = coordinator.scrape_all(
            principal_uf=args.principal,
            term_years=args.term,
            property_value_uf=args.property_value,
            bank_ids=bank_list,
        )
        saved_count = 0
    else:
        store = MarketDataStore(db_path=args.db_path)
        sync_result = coordinator.sync_to_duckdb(
            store=store,
            principal_uf=args.principal,
            term_years=args.term,
            property_value_uf=args.property_value,
            bank_ids=bank_list,
            base_benchmark_rate=avg_rate,
        )
        quotes = sync_result.get("quote_objects") or []
        saved_count = sync_result["records_saved"]
        store.close()

    if args.json:
        output_payload = {
            "status": "SUCCESS",
            "dry_run": args.dry_run,
            "principal_uf": args.principal,
            "term_years": args.term,
            "records_saved": saved_count,
            "quotes": [q.to_dict() for q in quotes],
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(output_payload, indent=2, ensure_ascii=False))
    else:
        print_table(quotes, avg_rate)
        if args.dry_run:
            print("ℹ️ Modo --dry-run activo: los registros NO fueron guardados en DuckDB.")
        else:
            print(f"✅ Sincronización exitosa: {saved_count} ofertas guardadas/actualizadas en '{args.db_path}'.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
