# HipoRefi-CL 🇨🇱
> **Motor Cuantitativo y Plataforma de Optimización de Refinanciamiento Hipotecario en Chile**

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Plataforma analítica y cuantitativa diseñada bajo la normativa chilena (**Ley N° 21.236 de Portabilidad Financiera**, **D.L. 3475 de Timbres y Estampillas** y **Ley General de Bancos Art. 100**) para evaluar rigurosamente decisiones de refinanciamiento hipotecario en UF.

---

## 🚀 Características Principales

- **Simulador de Amortización Francesa en UF:** Modelado exacto mes a mes con desglose de amortización de capital, intereses devengados y seguros obligatorios (desgravamen con escalamiento por edad e incendio/sismo).
- **Calculadora de Costos de Cambio (Ley 21.236):** Descuento legal del 50% en aranceles del Conservador de Bienes Raíces (CBR) por subrogación, límite legal de comisión de prepago (1.5 meses de interés) y exención de impuesto de timbres y estampillas.
- **Evaluación Financiera Avanzada:** Cálculo de Valor Presente Neto (**VPN**) a tasa de oportunidad real en UF, período de recuperación dinámico (**Payback**) y semáforo patrimonial inteligente.
- **Ingesta de Mercado:** Conexión con series macroeconómicas del Banco Central de Chile y CMF.
- **Extracción Inteligente de Cartolas:** Procesamiento de estados de cuenta hipotecarios (PDF) mediante esquemas estructurados Pydantic y LLMs.

---

## 🛠️ Instalación y Entorno

Este proyecto utiliza [`uv`](https://github.com/astral-sh/uv) para gestión ultrarrápida de dependencias y entornos virtuales:

```bash
# 1. Crear entorno virtual con Python 3.11
uv venv .venv --python 3.11

# 2. Activar entorno virtual
source .venv/bin/activate

# 3. Instalar dependencias del proyecto (incluyendo tests y dev)
uv pip install -e ".[dev]"
```

---

## 🧪 Pruebas Unitarias

Ejecutar la suite completa de pruebas financieras y de API:

```bash
pytest tests/ -v
```

---

## ⚡ Ejecución de la API REST (FastAPI)

Para iniciar el servidor de desarrollo local con Swagger UI:

```bash
uvicorn src.app.api:app --reload --host 0.0.0.0 --port 8000
```

- **Documentación Interactiva (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación Alternativa (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Healthcheck:** `GET /health`
- **Simulación:** `POST /api/v1/simulate`
- **Evaluación Refinanciamiento:** `POST /api/v1/evaluate-refinance`
- **Extracción de Cartolas:** `POST /api/v1/extract-statement` y `POST /api/v1/extract-statement/upload`
- **Tasas de Mercado:** `GET /api/v1/market-rates`

---

## 🖥️ Interfaz de Usuario Interactiva (Streamlit)

Para lanzar el dashboard analítico interactivo con gráficos dinámicos de Plotly:

```bash
streamlit run src/app/dashboard.py
```

El panel abrirá automáticamente en tu navegador ([http://localhost:8501](http://localhost:8501)) y ofrece:
- **Subida drag-and-drop de cartolas PDF** con auto-completado del crédito.
- **Monitoreo macroeconómico:** UF en tiempo real, TPM y tasas CMF.
- **Comparador de mercado:** Simulación contra los principales bancos chilenos y mutuarias.
- **Gráficos dinámicos de Break-Even y Payback:** Curva de recuperación del costo de cambio.
- **Simulador a medida:** Sliders de sensibilidad y mapa de calor 2D (Heatmap).
- **Detector de la Falacia del Dividendo:** Advertencia cuantitativa contra el alargamiento destructivo de plazos.
- **Tabla de desarrollo descargable en CSV.**

---

## 📂 Arquitectura del Proyecto

```text
hipo-refi-cl/
├── docs/               # Especificaciones técnicas y regulatorias
├── data/               # DuckDB y series de datos de mercado
├── src/
│   ├── core/           # Motor financiero (Amortización, Costos, Métricas)
│   ├── scrapers/       # Clientes BCCh, CMF y cotizadores bancarios
│   ├── parsers/        # Extracción y parsing de cartolas PDF
│   └── app/            # API REST (FastAPI) y Dashboard interactivo
└── tests/              # Suite de pruebas unitarias
```

---

## 📜 Licencia

Distribuido bajo la Licencia MIT. Consulta `LICENSE` para más detalles.
