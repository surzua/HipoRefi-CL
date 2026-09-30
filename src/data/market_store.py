"""Persistencia en DuckDB para series macroeconómicas y ofertas de tasas bancarias chilenas."""

from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import json
import uuid
import duckdb
import pandas as pd


class MarketDataStore:
    DEFAULT_DB_PATH = "data/market_rates.duckdb"

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.is_memory_fallback = False
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = duckdb.connect(self.db_path)
            self.init_schema()
        except duckdb.IOException:
            # Fallback en memoria si la base de datos en disco tiene bloqueo por otro proceso (ej: uvicorn vs streamlit)
            self.conn = duckdb.connect(":memory:")
            self.is_memory_fallback = True
            self.init_schema()
            self.seed_default_market_data()

    def init_schema(self) -> None:
        """Inicializa las tablas maestras si no existen."""
        # Tabla de series de tiempo macroeconómicas (BCCh, CMF)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS macro_series (
                date DATE,
                series_code VARCHAR,
                series_name VARCHAR,
                value DOUBLE,
                unit VARCHAR,
                source VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, series_code)
            );
        """)

        # Asegurar que la TPM esté actualizada a 4.50 si existían observaciones obsoletas
        try:
            self.conn.execute("""
                UPDATE macro_series
                SET value = 4.50
                WHERE series_code = 'F073.TPM.TCM.G01.Z.D' AND value != 4.50;
            """)
        except Exception:
            pass

        # Tabla de ofertas de crédito y tasas de mercado por entidad
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_offers (
                id VARCHAR PRIMARY KEY,
                bank_name VARCHAR,
                loan_type VARCHAR,
                term_years INTEGER,
                annual_rate DOUBLE,
                spread_over_benchmark DOUBLE,
                min_ltv DOUBLE,
                fire_insurance_rate_monthly DOUBLE,
                life_insurance_rate_monthly DOUBLE,
                source VARCHAR,
                updated_at TIMESTAMP
            );
        """)

        # Tabla de simulaciones guardadas por el usuario (Hito 10)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_simulations (
                id VARCHAR PRIMARY KEY,
                title VARCHAR,
                client_name VARCHAR,
                current_bank VARCHAR,
                balance_uf DOUBLE,
                annual_rate_pct DOUBLE,
                months_remaining INTEGER,
                current_dividend_uf DOUBLE,
                fire_insurance_uf DOUBLE,
                target_bank VARCHAR,
                target_rate_pct DOUBLE,
                target_term_years INTEGER,
                npv_uf DOUBLE,
                monthly_savings_uf DOUBLE,
                payback_months INTEGER,
                recommendation_flag VARCHAR,
                created_at TIMESTAMP,
                metadata_json VARCHAR
            );
        """)

    def save_macro_series(self, records: List[Dict[str, Any]]) -> int:
        """
        Inserta o actualiza registros de series temporales macroeconómicas.
        Cada registro debe tener: date, series_code, series_name, value, unit, source.
        """
        if not records:
            return 0

        count = 0
        for rec in records:
            record_date = rec["date"]
            if isinstance(record_date, str):
                record_date = datetime.strptime(record_date, "%Y-%m-%d").date()

            self.conn.execute("""
                INSERT INTO macro_series (date, series_code, series_name, value, unit, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, now())
                ON CONFLICT (date, series_code) DO UPDATE SET
                    value = EXCLUDED.value,
                    series_name = EXCLUDED.series_name,
                    unit = EXCLUDED.unit,
                    source = EXCLUDED.source;
            """, [
                record_date,
                rec["series_code"],
                rec.get("series_name", rec["series_code"]),
                float(rec["value"]),
                rec.get("unit", "INDEX"),
                rec.get("source", "MANUAL"),
            ])
            count += 1
        return count

    def save_bank_offers(self, offers: List[Dict[str, Any]]) -> int:
        """Guarda o actualiza ofertas de crédito bancario."""
        if not offers:
            return 0

        count = 0
        for off in offers:
            updated_at = off.get("updated_at")
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)
            elif updated_at is None:
                updated_at = datetime.now()

            self.conn.execute("""
                INSERT INTO bank_offers (
                    id, bank_name, loan_type, term_years, annual_rate,
                    spread_over_benchmark, min_ltv, fire_insurance_rate_monthly,
                    life_insurance_rate_monthly, source, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    bank_name = EXCLUDED.bank_name,
                    loan_type = EXCLUDED.loan_type,
                    term_years = EXCLUDED.term_years,
                    annual_rate = EXCLUDED.annual_rate,
                    spread_over_benchmark = EXCLUDED.spread_over_benchmark,
                    min_ltv = EXCLUDED.min_ltv,
                    fire_insurance_rate_monthly = EXCLUDED.fire_insurance_rate_monthly,
                    life_insurance_rate_monthly = EXCLUDED.life_insurance_rate_monthly,
                    source = EXCLUDED.source,
                    updated_at = EXCLUDED.updated_at;
            """, [
                off["id"],
                off["bank_name"],
                off.get("loan_type", "Tasa Fija"),
                int(off["term_years"]),
                float(off["annual_rate"]),
                float(off.get("spread_over_benchmark", 0.0)),
                float(off.get("min_ltv", 0.80)),
                float(off.get("fire_insurance_rate_monthly", 0.00015)),
                float(off.get("life_insurance_rate_monthly", 0.00028)),
                off.get("source", "SIMULATOR"),
                updated_at,
            ])
            count += 1
        return count

    def get_latest_uf(self) -> Optional[float]:
        """Retorna el último valor registrado de la UF."""
        res = self.conn.execute("""
            SELECT value FROM macro_series
            WHERE series_code = 'F073.UFF.PRE.Z.D'
            ORDER BY date DESC
            LIMIT 1;
        """).fetchone()
        return float(res[0]) if res else None

    def get_latest_macro_rates(self) -> Dict[str, Any]:
        """Obtiene un resumen de los últimos indicadores macroeconómicos relevantes."""
        query = """
            SELECT series_code, series_name, value, unit, date
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER(PARTITION BY series_code ORDER BY date DESC) as rn
                FROM macro_series
            )
            WHERE rn = 1;
        """
        rows = self.conn.execute(query).fetchall()
        summary = {}
        for row in rows:
            code, name, val, unit, dt = row
            summary[code] = {
                "name": name,
                "value": val,
                "unit": unit,
                "date": str(dt),
            }
        return summary

    def get_active_bank_offers(
        self,
        term_years: Optional[int] = None,
        max_rate: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Consulta las ofertas de tasas activas ordenadas por menor tasa."""
        conditions = []
        params = []

        if term_years is not None:
            conditions.append("term_years = ?")
            params.append(term_years)

        if max_rate is not None:
            conditions.append("annual_rate <= ?")
            params.append(max_rate)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, bank_name, loan_type, term_years, annual_rate,
                   spread_over_benchmark, min_ltv, fire_insurance_rate_monthly,
                   life_insurance_rate_monthly, source, updated_at
            FROM bank_offers
            {where_clause}
            ORDER BY annual_rate ASC;
        """
        rows = self.conn.execute(query, params).fetchall()
        offers = []
        for r in rows:
            offers.append({
                "id": r[0],
                "bank_name": r[1],
                "loan_type": r[2],
                "term_years": r[3],
                "annual_rate": r[4],
                "spread_over_benchmark": r[5],
                "min_ltv": r[6],
                "fire_insurance_rate_monthly": r[7],
                "life_insurance_rate_monthly": r[8],
                "source": r[9],
                "updated_at": str(r[10]),
            })
        return offers

    def seed_default_market_data(self) -> None:
        """
        Inserta datos semilla realistas de referencia para la banca chilena.
        Garantiza que la plataforma funcione en modo offline o sin API keys.
        """
        today_str = date.today().isoformat()

        # 1. Series macro de referencia
        macro_seeds = [
            {
                "date": today_str,
                "series_code": "F073.UFF.PRE.Z.D",
                "series_name": "Unidad de Fomento (UF)",
                "value": 40942.74,
                "unit": "CLP",
                "source": "SEED_BENCHMARK",
            },
            {
                "date": today_str,
                "series_code": "F072.CLP.COL.VIV.Z.M",
                "series_name": "Tasa Colocación Vivienda Promedio Sistema",
                "value": 4.68,
                "unit": "PERCENT",
                "source": "SEED_BENCHMARK",
            },
            {
                "date": today_str,
                "series_code": "F073.TPM.TCM.G01.Z.D",
                "series_name": "Tasa de Política Monetaria (TPM)",
                "value": 4.50,
                "unit": "PERCENT",
                "source": "SEED_BENCHMARK",
            },
        ]
        self.save_macro_series(macro_seeds)

        # 2. Catálogo de ofertas bancarias representativas en Chile
        bank_seeds = [
            {
                "id": "bchile-fija-20",
                "bank_name": "Banco de Chile",
                "loan_type": "Tasa Fija",
                "term_years": 20,
                "annual_rate": 0.0435,  # 4.35%
                "spread_over_benchmark": -0.0033,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "bchile-fija-25",
                "bank_name": "Banco de Chile",
                "loan_type": "Tasa Fija",
                "term_years": 25,
                "annual_rate": 0.0455,  # 4.55%
                "spread_over_benchmark": -0.0013,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "santander-fija-20",
                "bank_name": "Banco Santander",
                "loan_type": "Tasa Fija",
                "term_years": 20,
                "annual_rate": 0.0440,  # 4.40%
                "spread_over_benchmark": -0.0028,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "santander-fija-25",
                "bank_name": "Banco Santander",
                "loan_type": "Tasa Fija",
                "term_years": 25,
                "annual_rate": 0.0460,  # 4.60%
                "spread_over_benchmark": -0.0008,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "bci-fija-20",
                "bank_name": "BCI",
                "loan_type": "Tasa Fija",
                "term_years": 20,
                "annual_rate": 0.0438,  # 4.38%
                "spread_over_benchmark": -0.0030,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "scotiabank-fija-20",
                "bank_name": "Scotiabank",
                "loan_type": "Tasa Fija",
                "term_years": 20,
                "annual_rate": 0.0442,  # 4.42%
                "spread_over_benchmark": -0.0026,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "bancoestado-fija-20",
                "bank_name": "BancoEstado",
                "loan_type": "Tasa Fija",
                "term_years": 20,
                "annual_rate": 0.0450,  # 4.50%
                "spread_over_benchmark": -0.0018,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "bancoestado-fija-30",
                "bank_name": "BancoEstado",
                "loan_type": "Tasa Fija",
                "term_years": 30,
                "annual_rate": 0.0480,  # 4.80%
                "spread_over_benchmark": 0.0012,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
            {
                "id": "mutuaria-security-20",
                "bank_name": "Mutuaria Security",
                "loan_type": "Mutuaria Endosable",
                "term_years": 20,
                "annual_rate": 0.0425,  # 4.25%
                "spread_over_benchmark": -0.0043,
                "min_ltv": 0.80,
                "source": "SEED_MARKET",
            },
        ]
        self.save_bank_offers(bank_seeds)

    def save_simulation(self, sim: Dict[str, Any]) -> str:
        """Guarda o actualiza un escenario de simulación en DuckDB (Hito 10)."""
        sim_id = sim.get("id") or f"sim-{uuid.uuid4().hex[:10]}"
        created_at = sim.get("created_at") or datetime.now()
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        meta = sim.get("metadata_json") or {}
        if isinstance(meta, dict):
            meta = json.dumps(meta, ensure_ascii=False)

        self.conn.execute("""
            INSERT INTO saved_simulations (
                id, title, client_name, current_bank, balance_uf,
                annual_rate_pct, months_remaining, current_dividend_uf,
                fire_insurance_uf, target_bank, target_rate_pct,
                target_term_years, npv_uf, monthly_savings_uf,
                payback_months, recommendation_flag, created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                client_name = EXCLUDED.client_name,
                current_bank = EXCLUDED.current_bank,
                balance_uf = EXCLUDED.balance_uf,
                annual_rate_pct = EXCLUDED.annual_rate_pct,
                months_remaining = EXCLUDED.months_remaining,
                current_dividend_uf = EXCLUDED.current_dividend_uf,
                fire_insurance_uf = EXCLUDED.fire_insurance_uf,
                target_bank = EXCLUDED.target_bank,
                target_rate_pct = EXCLUDED.target_rate_pct,
                target_term_years = EXCLUDED.target_term_years,
                npv_uf = EXCLUDED.npv_uf,
                monthly_savings_uf = EXCLUDED.monthly_savings_uf,
                payback_months = EXCLUDED.payback_months,
                recommendation_flag = EXCLUDED.recommendation_flag,
                metadata_json = EXCLUDED.metadata_json;
        """, [
            sim_id,
            sim.get("title", f"Simulación {sim.get('target_bank', 'Hipotecario')}"),
            sim.get("client_name", "Titular del Crédito"),
            sim.get("current_bank", "Banco Actual"),
            float(sim.get("balance_uf", 0.0)),
            float(sim.get("annual_rate_pct", 0.0)),
            int(sim.get("months_remaining", 0)),
            float(sim.get("current_dividend_uf", 0.0)),
            float(sim.get("fire_insurance_uf", 0.0)),
            sim.get("target_bank", "Banco Destino"),
            float(sim.get("target_rate_pct", 0.0)),
            int(sim.get("target_term_years", 0)),
            float(sim.get("npv_uf", 0.0)),
            float(sim.get("monthly_savings_uf", 0.0)),
            sim.get("payback_months"),
            sim.get("recommendation_flag", "RECOMENDADO"),
            created_at,
            meta,
        ])
        return sim_id

    def get_saved_simulations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista las simulaciones guardadas ordenadas por fecha de creación descendente."""
        df = self.conn.execute("""
            SELECT id, title, client_name, current_bank, balance_uf,
                   annual_rate_pct, months_remaining, current_dividend_uf,
                   fire_insurance_uf, target_bank, target_rate_pct,
                   target_term_years, npv_uf, monthly_savings_uf,
                   payback_months, recommendation_flag, created_at, metadata_json
            FROM saved_simulations
            ORDER BY created_at DESC
            LIMIT ?;
        """, [limit]).fetchdf()

        results = []
        for _, row in df.iterrows():
            meta = {}
            if row["metadata_json"]:
                try:
                    meta = json.loads(row["metadata_json"])
                except Exception:
                    pass
            results.append({
                "id": row["id"],
                "title": row["title"],
                "client_name": row["client_name"],
                "current_bank": row["current_bank"],
                "balance_uf": float(row["balance_uf"]),
                "annual_rate_pct": float(row["annual_rate_pct"]),
                "months_remaining": int(row["months_remaining"]),
                "current_dividend_uf": float(row["current_dividend_uf"]),
                "fire_insurance_uf": float(row["fire_insurance_uf"]),
                "target_bank": row["target_bank"],
                "target_rate_pct": float(row["target_rate_pct"]),
                "target_term_years": int(row["target_term_years"]),
                "npv_uf": float(row["npv_uf"]),
                "monthly_savings_uf": float(row["monthly_savings_uf"]),
                "payback_months": int(row["payback_months"]) if pd.notnull(row["payback_months"]) else None,
                "recommendation_flag": row["recommendation_flag"],
                "created_at": str(row["created_at"]),
                "metadata_json": meta,
            })
        return results

    def get_saved_simulation_by_id(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una simulación guardada por su identificador único."""
        df = self.conn.execute("""
            SELECT id, title, client_name, current_bank, balance_uf,
                   annual_rate_pct, months_remaining, current_dividend_uf,
                   fire_insurance_uf, target_bank, target_rate_pct,
                   target_term_years, npv_uf, monthly_savings_uf,
                   payback_months, recommendation_flag, created_at, metadata_json
            FROM saved_simulations
            WHERE id = ?;
        """, [sim_id]).fetchdf()

        if df.empty:
            return None
        row = df.iloc[0]
        meta = {}
        if row["metadata_json"]:
            try:
                meta = json.loads(row["metadata_json"])
            except Exception:
                pass
        return {
            "id": row["id"],
            "title": row["title"],
            "client_name": row["client_name"],
            "current_bank": row["current_bank"],
            "balance_uf": float(row["balance_uf"]),
            "annual_rate_pct": float(row["annual_rate_pct"]),
            "months_remaining": int(row["months_remaining"]),
            "current_dividend_uf": float(row["current_dividend_uf"]),
            "fire_insurance_uf": float(row["fire_insurance_uf"]),
            "target_bank": row["target_bank"],
            "target_rate_pct": float(row["target_rate_pct"]),
            "target_term_years": int(row["target_term_years"]),
            "npv_uf": float(row["npv_uf"]),
            "monthly_savings_uf": float(row["monthly_savings_uf"]),
            "payback_months": int(row["payback_months"]) if pd.notnull(row["payback_months"]) else None,
            "recommendation_flag": row["recommendation_flag"],
            "created_at": str(row["created_at"]),
            "metadata_json": meta,
        }

    def delete_saved_simulation(self, sim_id: str) -> bool:
        """Elimina una simulación guardada por su identificador único."""
        self.conn.execute("""
            DELETE FROM saved_simulations WHERE id = ?;
        """, [sim_id])
        return True

    def close(self) -> None:
        """Cierra la conexión a DuckDB."""
        self.conn.close()
