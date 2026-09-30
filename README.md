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

## 🐳 Despliegue con Docker y Docker Compose

La plataforma incluye contenedorización lista para producción. Puedes levantar simultáneamente la API REST y el Dashboard interactivo con un solo comando:

```bash
# Construir y levantar servicios en segundo plano
docker compose up --build -d

# Ver logs en tiempo real
docker compose logs -f

# Detener los contenedores
docker compose down
```

* **Dashboard Web:** [http://localhost:8501](http://localhost:8501)
* **API REST & Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Persistencia:** Volumen compartido `hiporefi_data` para DuckDB.

---

## 🧪 Pruebas Unitarias y Calidad de Código

El proyecto cuenta con una suite completa de **54 pruebas unitarias y de integración**, además de validación de estilo con `ruff` e integración continua en GitHub Actions (`.github/workflows/ci.yml`):

```bash
# Ejecutar suite de pruebas con cobertura
pytest tests/ -v --cov=src

# Chequeo de calidad y estilo de código
ruff check .
```

---

## 🗺️ Hoja de Ruta del Proyecto (Roadmap)

| Hito | Estado | Descripción |
| :---: | :---: | :--- |
| **Hito 1** | ✅ Completado | Core Matemático (Amortización francesa en UF, seguros y 49 unit tests iniciales). |
| **Hito 2** | ✅ Completado | Ingesta de Mercado y Persistencia en DuckDB (BCCh, CMF y simuladores). |
| **Hito 3** | ✅ Completado | Extracción Documental de Cartolas PDF (heurística regex + fallback LLM). |
| **Hito 4** | ✅ Completado | API REST Backend en FastAPI (`/simulate`, `/evaluate-refinance`, `/health`). |
| **Hito 5** | ✅ Completado | Dashboard Interactivo en Streamlit (5 pestañas, Plotly y drag & drop). |
| **Hito 6** | ✅ Completado | DevOps: Contenedorización Docker, `docker-compose.yml`, `.dockerignore` y CI/CD en GitHub Actions. |
| **Hito 7** | ✅ Completado | Generador de Informe Ejecutivo y Dictamen de Portabilidad en PDF (ReportLab, gráficos vectoriales nativos y API). |
| **Hito 8** | ✅ Completado | Módulo Financiero Avanzado (Abonos extraordinarios, tasa mixta vs fija, desgravamen por edad, amortización alemana). |
| **Hito 9** | ✅ Completado | Ingesta en Vivo con Web Scraping Headless (Playwright sobre cotizadores de BancoEstado, Santander y BCI). |
| **Hito 10** | ✅ Completado | UX Comercial Avanzada (Comparador Head-to-Head, persistencia DuckDB, modal de validación y URL sharing). |

---

## 🥊 Comparador Head-to-Head y Persistencia (Hito 10)

HipoRefi-CL incorpora herramientas avanzadas de productividad comercial:
- **Comparador Lado a Lado Head-to-Head:** Enfrenta directamente 2 instituciones bancarias o contraofertas específicas (dividendo mensual, VPN generado, payback, interés total acumulado y dictamen cuantitativo de dominancia patrimonial).
- **Modal Interactivo de Validación Documental:** Al subir una cartola PDF, despliega un diálogo de confirmación interactivo que permite previsualizar y ajustar manualmente las variables antes de recalcular.
- **Persistencia de Simulaciones en DuckDB:** Guarda escenarios de evaluación para auditoría técnica, negociación bancaria o seguimiento a lo largo del tiempo.
- **Compartir vía URL Parametrizada:** Generación de enlaces con parámetros pre-poblados (`?balance=3200&rate=5.2&months=180&bank=Santander`) o ID de simulación (`?sim_id=...`).

Endpoints disponibles en la API:
- `POST /api/v1/compare/head-to-head`: Comparación cuantitativa directa entre Banco A y Banco B.
- `POST /api/v1/simulations/save`: Guarda una simulación en la tabla `saved_simulations` de DuckDB.
- `GET /api/v1/simulations`: Lista el historial de simulaciones guardadas.
- `GET /api/v1/simulations/{sim_id}`: Consulta el detalle completo de un escenario persistido.
- `DELETE /api/v1/simulations/{sim_id}`: Elimina una simulación guardada.

---

## 🤖 Web Scraping Headless en Vivo (Playwright)

El sistema incluye extracción automatizada sobre cotizadores bancarios públicos abiertos en Chile para alimentar la tabla `bank_offers` en DuckDB:

```bash
# Sincronización CLI con Playwright Headless
python scripts/sync_live_market.py --principal 3200 --term 20

# Simulación en modo dry-run con salida formateada
python scripts/sync_live_market.py --dry-run

# Salida en JSON para pipelines automatizados
python scripts/sync_live_market.py --dry-run --json
```

Endpoints disponibles en la API:
- `POST /api/v1/market-rates/scrape-sync`: Dispara la simulación headless y actualiza DuckDB.
- `GET /api/v1/market-rates/live-offers`: Consulta las ofertas bancarias vigentes extraídas.

---

## 📂 Arquitectura del Proyecto

```text
hipo-refi-cl/
├── .github/workflows/  # CI/CD (GitHub Actions)
├── docs/               # Especificaciones técnicas y regulatorias
├── data/               # DuckDB y series de datos de mercado
├── scripts/            # Scripts CLI (demostración y sync_live_market.py)
├── src/
│   ├── core/           # Motor financiero (Amortización, Costos Ley 21.236, Métricas)
│   ├── scrapers/       # Clientes BCCh, CMF, cotizadores y scrapers headless Playwright
│   ├── parsers/        # Extracción y parsing de cartolas PDF
│   ├── reports/        # Generador de informes y dictámenes ejecutivos en PDF (ReportLab)
│   ├── data/           # Persistencia en DuckDB con manejo de concurrencia
│   └── app/            # API REST (FastAPI), Dashboard (Streamlit) y Gráficos (Plotly)
├── tests/              # Suite de 88 pruebas unitarias e integrales
├── Dockerfile          # Contenedor optimizado multi-servicio
├── docker-compose.yml  # Orquestador API + Dashboard + DuckDB
└── pyproject.toml      # Configuración de dependencias, hatchling, pytest y ruff
```

---

## 📜 Licencia

Distribuido bajo la Licencia MIT. Consulta `LICENSE` para más detalles.

