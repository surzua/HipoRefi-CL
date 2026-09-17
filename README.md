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

## 🚀 Inicio Rápido

### 1. Activar el Entorno Virtual
Antes de ejecutar cualquier comando, activa el entorno virtual de Python:

```bash
source .venv/bin/activate
```

---

## 🖥️ Cómo Activar el Dashboard Interactivo (Streamlit)

El dashboard web es la forma más intuitiva de evaluar créditos hipotecarios, explorar ofertas bancarias y visualizar gráficos interactivos:

```bash
# Opción 1: Con entorno virtual activado
streamlit run src/app/dashboard.py

# Opción 2: Directo con el ejecutable del entorno
.venv/bin/streamlit run src/app/dashboard.py
```

Una vez ejecutado, se abrirá automáticamente en tu navegador en:
👉 **[http://localhost:8501](http://localhost:8501)**

### Funcionalidades Disponibles en la Interfaz:
- **Arrastrar y soltar (Drag & Drop) de cartolas PDF:** Sube tu estado de cuenta bancario y el sistema auto-completará saldo, tasa, cuotas restantes y seguros.
- **Monitoreo Macroeconómico en Vivo:** Indicadores actualizados de la UF en CLP, TPM (4.50%) y tasas CMF.
- **5 Pestañas de Análisis Especializado:**
  1. 🏆 **Comparador de Mercado:** Ranking de entidades según mayor ganancia neta (VPN) y desglose legal de gastos de cambio (Ley N° 21.236).
  2. 📈 **Punto de Equilibrio & Payback:** Curva de recuperación del costo de cambio y mes exacto de Break-Even.
  3. 🎛️ **Simulador a Medida:** Sliders para evaluar contraofertas particulares y **Heatmap 2D** de Tasa vs Plazo.
  4. ⚠️ **Detector de la 'Falacia del Dividendo':** Demostración del sobrecosto en intereses al alargar plazos para bajar cuota.
  5. 📋 **Tabla de Amortización Francesa:** Detalle cuota a cuota con botón de **descarga en CSV**.

---

## ⚡ Cómo Activar la API REST Backend (FastAPI)

Para consumir el motor cuantitativo desde otras aplicaciones, scripts o servicios web:

```bash
# Opción 1: Con entorno virtual activado
uvicorn src.app.api:app --reload --host 0.0.0.0 --port 8000

# Opción 2: Directo con el ejecutable del entorno
.venv/bin/uvicorn src.app.api:app --reload --port 8000
```

- **Documentación Interactiva (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación Alternativa (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Healthcheck:** `GET http://localhost:8000/health`
- **Simulación:** `POST http://localhost:8000/api/v1/simulate`
- **Evaluación Refinanciamiento:** `POST http://localhost:8000/api/v1/evaluate-refinance`
- **Extracción de Cartolas:** `POST http://localhost:8000/api/v1/extract-statement` y `POST http://localhost:8000/api/v1/extract-statement/upload`
- **Tasas e Indicadores de Mercado:** `GET http://localhost:8000/api/v1/market-rates`

> [!TIP]
> Puedes tener **el Dashboard y la API corriendo simultáneamente** en terminales separadas; la base de datos DuckDB cuenta con protección automática de concurrencia y no genera conflictos de bloqueo.

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
