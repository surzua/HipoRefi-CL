"""Extractor estructurado de cartolas hipotecarias chilenas mediante Heurísticas/NLP y LLMs."""

import re
import os
import json
from pathlib import Path
from typing import Union, BinaryIO, Optional, Dict, Any
import requests

from src.parsers.pdf_reader import PDFReader
from src.parsers.statement_llm import MortgageStatementExtraction, SYSTEM_PROMPT_EXTRACTION


class StatementExtractionError(Exception):
    """Error al extraer o estructurar la cartola hipotecaria."""
    pass


class HeuristicStatementParser:
    """
    Parser determinista calibrado para la banca hipotecaria chilena.
    Extrae variables cuantitativas clave usando expresiones regulares y normalización numérica.
    """

    KNOWN_BANKS = [
        ("Banco de Chile", [r"banco de chile", r"bancochile", r"edwards"]),
        ("Banco Santander", [r"santander", r"banco santander"]),
        ("BancoEstado", [r"bancoestado", r"banco del estado"]),
        ("BCI", [r"\bbci\b", r"banco de cr[eé]dito e inversiones"]),
        ("Scotiabank", [r"scotiabank"]),
        ("Banco Itaú", [r"ita[uú]", r"itau"]),
        ("Banco BICE", [r"bice"]),
        ("Banco Security", [r"security"]),
        ("Mutuaria Security", [r"mutuaria security"]),
        ("Consorcio", [r"consorcio"]),
        ("Principal", [r"principal"]),
    ]

    @classmethod
    def parse_chilean_number(cls, num_str: str) -> Optional[float]:
        """
        Normaliza formatos numéricos comunes en Chile:
        - 3.250,50 -> 3250.50
        - 3,250.50 -> 3250.50
        - 3250,50  -> 3250.50
        - 3250     -> 3250.0
        """
        if not num_str:
            return None
        cleaned = num_str.strip().replace("$", "").replace("UF", "").strip()

        # Caso: notación chilena/alemana con punto para miles y coma para decimal (ej: 3.250,50)
        if "." in cleaned and "," in cleaned:
            if cleaned.find(".") < cleaned.find(","):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        elif "." in cleaned:
            # Si tiene un punto y luego 3 dígitos al final (ej 3.250 sin decimales)
            parts = cleaned.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                cleaned = parts[0] + parts[1]

        try:
            return float(cleaned)
        except ValueError:
            return None

    @classmethod
    def extract_from_text(cls, text: str) -> MortgageStatementExtraction:
        """Parsea el texto de la cartola aplicando patrones de la banca chilena."""
        if not text or not text.strip():
            raise StatementExtractionError("El texto de la cartola está vacío.")

        lower_text = text.lower()

        # 1. Identificar Banco
        bank_name = "Entidad Financiera Chilena"
        for formal_name, patterns in cls.KNOWN_BANKS:
            if any(re.search(pat, lower_text) for pat in patterns):
                bank_name = formal_name
                break

        # 2. Número de operación / crédito
        op_match = re.search(
            r"(?:operaci[oó]n|cr[eé]dito|n[uú]mero\s*cr[eé]dito|n[°º.]?)\s*[:\s#]*([0-9\-\.]{4,16})",
            lower_text,
        )
        operation_number = op_match.group(1).strip() if op_match else None

        # 3. Saldo insoluto de capital en UF
        balance_match = re.search(
            r"(?:saldo\s*(?:de\s*)?capital|saldo\s*insoluto|capital\s*insoluto|saldo\s*deudor|saldo\s*remanente)"
            r"[\s\:\$]*([0-9\.,]+)\s*(?:uf)?",
            lower_text,
        )
        current_balance = (
            cls.parse_chilean_number(balance_match.group(1)) if balance_match else None
        )

        # 4. Tasa de interés anual
        rate_match = re.search(
            r"(?:tasa\s*(?:de\s*)?inter[eé]s(?:\s*anual)?|tasa\s*anual|tasa\s*pactada|tasa\s*cr[eé]dito)"
            r"[\s\:\=]*([0-9\.,]+)\s*%",
            lower_text,
        )
        annual_rate = cls.parse_chilean_number(rate_match.group(1)) if rate_match else None

        # 5. Cuotas y dividendos restantes
        # Patrón 1: "Cuota 60 de 240" o "Dividendo 45/180"
        installment_fraction = re.search(
            r"(?:dividendo|cuota)\s*(?:n[°º.]?)?\s*([0-9]+)\s*[\/\-de]+\s*([0-9]+)",
            lower_text,
        )
        remaining_installments = None
        total_installments = None

        if installment_fraction:
            paid_inst = int(installment_fraction.group(1))
            total_inst = int(installment_fraction.group(2))
            if total_inst >= paid_inst:
                total_installments = total_inst
                remaining_installments = total_inst - paid_inst
        else:
            # Patrón 2: "Cuotas pendientes: 120"
            rem_match = re.search(
                r"(?:cuotas?|dividendos?)\s*(?:pendientes?|remanentes?|por\s*pagar|restantes?)"
                r"[\s\:\=]*([0-9]{1,3})",
                lower_text,
            )
            if rem_match:
                remaining_installments = int(rem_match.group(1))

        # 6. Dividendo total en UF
        dividend_match = re.search(
            r"(?:dividendo\s*total(?:\s*a\s*pagar)?|total\s*dividendo|valor\s*(?:del\s*)?dividendo|"
            r"monto\s*(?:total\s*)?a\s*pagar|dividendo\s*del\s*mes|dividendo\s*mensual|"
            r"dividendo\s*a\s*pagar|total\s*a\s*pagar)"
            r"[\s\:\$]*([0-9\.,]+)\s*(?:uf)?",
            lower_text,
        )
        total_dividend = (
            cls.parse_chilean_number(dividend_match.group(1)) if dividend_match else None
        )

        # 7. Seguros
        life_ins_match = re.search(
            r"(?:seguro\s*desgravamen|desgravamen)[\s\:\$]*([0-9\.,]+)\s*(?:uf)?",
            lower_text,
        )
        life_ins = cls.parse_chilean_number(life_ins_match.group(1)) if life_ins_match else None

        fire_ins_match = re.search(
            r"(?:seguro\s*incendio|incendio\s*y\s*sismo|incendio)[\s\:\$]*([0-9\.,]+)\s*(?:uf)?",
            lower_text,
        )
        fire_ins = cls.parse_chilean_number(fire_ins_match.group(1)) if fire_ins_match else None

        # 8. Dividendo financiero (puro sin seguros)
        fin_match = re.search(
            r"(?:dividendo\s*financiero|cuota\s*financiera)[\s\:\$]*([0-9\.,]+)\s*(?:uf)?",
            lower_text,
        )
        fin_div = cls.parse_chilean_number(fin_match.group(1)) if fin_match else None

        # 9. Edad del cliente
        age_match = re.search(
            r"(?:edad|edad\s*titular|a[ñn]os)[\s\:\=]*([0-9]{2})\b",
            lower_text,
        )
        customer_age = int(age_match.group(1)) if age_match else None

        # Si faltan campos críticos, proveer valores por defecto razonables o arrojar error
        if current_balance is None:
            # Búsqueda secundaria de cifras que representen montos en UF típicos (ej: 500 a 15000 UF)
            uf_candidates = re.findall(r"([0-9\.,]+)\s*uf\b", lower_text)
            for cand in uf_candidates:
                val = cls.parse_chilean_number(cand)
                if val and 300.0 <= val <= 25000.0:
                    current_balance = val
                    break

        if current_balance is None:
            raise StatementExtractionError(
                "No fue posible detectar el saldo insoluto de capital en la cartola."
            )

        if annual_rate is None:
            # Búsqueda secundaria de porcentajes entre 2.0% y 9.0%
            rate_candidates = re.findall(r"([0-9\.,]+)\s*%", lower_text)
            for cand in rate_candidates:
                val = cls.parse_chilean_number(cand)
                if val and 2.0 <= val <= 10.0:
                    annual_rate = val
                    break
            if annual_rate is None:
                annual_rate = 4.50  # Tasa representativa por defecto si el texto no lo indica

        if remaining_installments is None:
            remaining_installments = 180  # 15 años estándar por defecto

        if total_dividend is None:
            # Estimar dividendo financiero preliminar
            monthly_r = (1.0 + (annual_rate / 100.0)) ** (1.0 / 12.0) - 1.0
            factor = (1.0 + monthly_r) ** remaining_installments
            estimated_df = current_balance * (monthly_r * factor) / (factor - 1.0)
            total_dividend = round(estimated_df * 1.06, 2)  # +6% por seguros

        return MortgageStatementExtraction(
            bank_name=bank_name,
            operation_number=operation_number,
            current_balance_uf=round(current_balance, 2),
            annual_interest_rate_pct=round(annual_rate, 2),
            remaining_installments=remaining_installments,
            total_installments=total_installments,
            current_total_dividend_uf=round(total_dividend, 2),
            financial_dividend_uf=round(fin_div, 2) if fin_div else None,
            life_insurance_uf=round(life_ins, 2) if life_ins else None,
            fire_insurance_uf=round(fire_ins, 2) if fire_ins else None,
            customer_age_years=customer_age,
        )


class StatementExtractor:
    """
    Orquestador de extracción documental.
    Permite procesar PDFs mediante modelos LLM (Gemini/OpenAI) o
    vía parser heurístico local determinista.
    """

    def __init__(self, mode: str = "auto"):
        self.mode = mode.lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def extract_from_pdf(
        self, source: Union[str, Path, bytes, BinaryIO]
    ) -> MortgageStatementExtraction:
        """Lee el archivo PDF y extrae el schema estructurado de la cartola."""
        text = PDFReader.extract_text(source)
        return self.extract_from_text(text)

    def extract_from_text(self, text: str) -> MortgageStatementExtraction:
        """Extrae los campos cuantitativos del texto mediante LLM o Heurística."""
        # Si se especificó LLM o auto y hay credenciales de Gemini
        if self.mode in ["auto", "gemini"] and self.gemini_key:
            try:
                return self._extract_with_gemini(text)
            except Exception:
                # Fallback transparente a heurísticas
                pass

        # Si hay credenciales de OpenAI
        if self.mode in ["auto", "openai"] and self.openai_key:
            try:
                return self._extract_with_openai(text)
            except Exception:
                pass

        # Modo heurístico determinista (siempre disponible y offline)
        return HeuristicStatementParser.extract_from_text(text)

    def _extract_with_gemini(self, text: str) -> MortgageStatementExtraction:
        """Llama a la API de Gemini con schema structured output."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT_EXTRACTION}\n\nTexto de la cartola:\n{text}"}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
            },
        }

        resp = requests.post(url, json=payload, timeout=20)
        resp.raise_for_status()
        res_json = resp.json()

        candidate_text = (
            res_json.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        data = json.loads(candidate_text)
        return MortgageStatementExtraction(**data)

    def _extract_with_openai(self, text: str) -> MortgageStatementExtraction:
        """Llama a la API de OpenAI con response_format json_object."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_EXTRACTION},
                {"role": "user", "content": f"Texto de la cartola:\n{text}"},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return MortgageStatementExtraction(**data)
