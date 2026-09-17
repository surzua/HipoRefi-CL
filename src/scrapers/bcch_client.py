"""Cliente para consumir series macroeconómicas de la API del Banco Central de Chile (si3.bcentral.cl)."""

import os
import requests
from typing import Dict, Any, Optional


class CentralBankChileClient:
    BASE_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.asmx/SearchSeries"

    # Códigos de serie estándar del BCCh
    SERIES_UF_DAILY = "F073.UFF.PRE.Z.D"           # Unidad de Fomento diaria
    SERIES_MORTGAGE_RATE = "F072.CLP.COL.VIV.Z.M"  # Tasa colocación vivienda en UF (mensual)
    SERIES_TPM = "F073.TPM.TCM.G01.Z.D"            # Tasa de Política Monetaria

    def __init__(self, user: Optional[str] = None, password: Optional[str] = None):
        self.user = user or os.getenv("BCCH_API_USER")
        self.password = password or os.getenv("BCCH_API_PASS")

    def fetch_series(self, series_code: str, first_date: str, last_date: str) -> Dict[str, Any]:
        """
        Consulta una serie de tiempo en el Banco Central de Chile.
        Formato de fechas requerido: YYYY-MM-DD
        """
        if not self.user or not self.password:
            raise ValueError(
                "Credenciales del Banco Central no configuradas. "
                "Defina BCCH_API_USER y BCCH_API_PASS en el entorno o páselas al constructor."
            )

        params = {
            "user": self.user,
            "pass": self.password,
            "firstdate": first_date,
            "lastdate": last_date,
            "timeseries": series_code,
        }

        response = requests.get(self.BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("Codigo") != 0:
            raise RuntimeError(f"Error en API Banco Central: {data.get('Descripcion')}")

        return data.get("Series", {})
