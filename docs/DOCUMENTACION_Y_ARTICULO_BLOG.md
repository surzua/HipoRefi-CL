# HipoRefi-CL: De la Hipoteca a la Optimización Cuantitativa
> **Guía Técnica Exhaustiva del Sistema y Documento Base para Artículo en Sitio Web Personal**  
> *Autor:* Sebastián Felipe Urzúa Bórquez  
> *Stack:* Python 3.11 | FastAPI | Streamlit | DuckDB | Playwright | Plotly | ReportLab | uv | Docker  
> *Ámbito Normativo:* Chile (Ley N° 21.236 de Portabilidad Financiera, D.L. 3475, Ley General de Bancos Art. 100)

---

## Índice General

1. [Introducción y Storytelling: El Problema de la Deuda Hipotecaria en Chile](#1-introducción-y-storytelling-el-problema-de-la-deuda-hipotecaria-en-chile)
2. [Visión General y Propuesta de Valor de HipoRefi-CL](#2-visión-general-y-propuesta-de-valor-de-hiporefi-cl)
3. [Arquitectura General del Sistema](#3-arquitectura-general-del-sistema)
4. [El Núcleo Cuantitativo y Financiero (La Matemática Real)](#4-el-núcleo-cuantitativo-y-financiero-la-matemática-real)
   - 4.1. Amortización Francesa vs. Amortización Alemana en UF
   - 4.2. La Anatomía de los Seguros Obligatorios (Incendio, Sismo y Desgravamen Actuarial)
   - 4.3. Los Costos de Cambio y la Regulación Chilena (Ley 21.236, DL 3475, LGB Art. 100)
   - 4.4. Métricas de Decisión: VPN Descontado, Payback Dinámico y Semáforo Patrimonial
   - 4.5. Módulo Avanzado: Abonos Extraordinarios y Riesgo de Tasa Mixta
5. [Ingesta de Mercado y Web Scraping Headless en Vivo](#5-ingesta-de-mercado-y-web-scraping-headless-en-vivo)
   - 5.1. Conexión Macroeconómica (Banco Central de Chile y CMF)
   - 5.2. Web Scraping Bancario con Playwright (7 Entidades Financieras)
   - 5.3. Persistencia Embebida y Concurrencia con DuckDB
6. [Extracción Documental Inteligente de Cartolas Bancarias](#6-extracción-documental-inteligente-de-cartolas-bancarias)
   - 6.1. Pipeline Híbrido: Regex Heurístico + Esquemas Pydantic con Fallback LLM
   - 6.2. Validación Humana en el Loop (Modal Interactivo en UI)
7. [Motor de Generación de Informes Ejecutivos en PDF](#7-motor-de-generación-de-informes-ejecutivos-en-pdf)
8. [Capas de Consumo: API REST (FastAPI) y Dashboard (Streamlit)](#8-capas-de-consumo-api-rest-fastapi-y-dashboard-streamlit)
   - 8.1. API Backend RESTful con Validación Pydantic v2
   - 8.2. Dashboard Analítico de 8 Pestañas e Interactividad Plotly
   - 8.3. Comparador Head-to-Head y Compartición por URL
9. [Infraestructura, DevOps y Calidad de Código](#9-infraestructura-devops-y-calidad-de-código)
   - 9.1. Entorno Ultrarrápido con uv
   - 9.2. Docker y Docker Compose
   - 9.3. Suite de Pruebas Automatizadas (106 tests pasando) y GitHub Actions CI
10. [Hoja de Ruta de Desarrollo (Roadmap de 10 Hitos Completados)](#10-hoja-de-ruta-de-desarrollo-roadmap-de-10-hitos-completados)
11. [Guía de Redacción para el Artículo del Blog Personal](#11-guía-de-redacción-para-el-artículo-del-blog-personal)
    - 11.1. Estructura Narrativa Sugerida (Pitch, Nudo, Desenlace)
    - 11.2. Ideas de Títulos Atractivos
    - 11.3. Puntos de Impacto Técnico para Mostrar a Reclutadores y Pares

---

## 1. Introducción y Storytelling: El Problema de la Deuda Hipotecaria en Chile

El crédito hipotecario es, con creces, el compromiso financiero más relevante y duradero que asume una familia en Chile. Se contrae típicamente a **20, 25 o 30 años**, está nominado en **Unidades de Fomento (UF)** —lo que significa que la deuda principal y los dividendos se indexan diariamente a la inflación— y puede comprometer entre el 20% y el 40% del ingreso mensual del hogar.

A fines de 2020 se promulgó en Chile la **Ley N° 21.236 de Portabilidad Financiera**, cuyo objetivo era democratizar y abaratar la migración de créditos entre instituciones financieras mediante la figura jurídica de la **subrogación**, rebajando aranceles registrales y prohibiendo costos abusivos.

Sin embargo, a más de tres años de su entrada en vigencia, **menos del 10% de los deudores hipotecarios cotiza o refinancia activamente su crédito**. ¿Por qué ocurre esto?

### Las Tres Barreras de Asimetría

1. **La Caja Negra de los Costos de Cambio:**  
   Calcular cuánto cuesta realmente cambiarse de banco es confuso. Hay que calcular la **comisión de prepago** (tope legal de 1.5 meses de intereses según el Art. 100 de la Ley General de Bancos), los aranceles del **Conservador de Bienes Raíces (CBR)** con el descuento legal del 50%, la tasación del inmueble, el estudio de títulos, los gastos notariales y el impuesto de timbres y estampillas (D.L. 3475). Ningún cotizador bancario tradicional presenta este desglose con transparencia.

2. **La "Falacia del Dividendo":**  
   Muchos deudores caen en la trampa comercial de *"bajar su cuota mensual"*. Un ejecutivo les propone extender un crédito con 15 años remanentes a un nuevo plazo de 25 años. El dividendo mensual baja en apariencia, pero el costo total acumulado en intereses aumenta drásticamente, destruyendo patrimonio neto a largo plazo.

3. **La Asimetría en Seguros:**  
   Los bancos publicitan tasas de interés anual atractivas, pero luego imponen primas elevadas en los seguros obligatorios de desgravamen e incendio/sismo. Además, el seguro de desgravamen se encarece naturalmente a medida que el deudor envejece, lo que hace que una tasa más baja en otro banco no siempre compense el mayor costo de la póliza.

### El Origen del Proyecto

Frente a este escenario, decidí crear **HipoRefi-CL**: un proyecto personal de ingeniería de software y finanzas cuantitativas concebido como una plataforma integral de código abierto. El propósito es entregarle a cualquier deudor o asesor una herramienta rigurosa, transparente y en tiempo real que responda a una sola pregunta fundamental:

> *¿Conviene o no conviene refinanciar este crédito hipotecario hoy, cuánto dinero se ahorra en valor presente neto, y en cuántos meses exactos se recupera la inversión de cambiar de banco?*

---

## 2. Visión General y Propuesta de Valor de HipoRefi-CL

HipoRefi-CL es un **motor analítico de extremo a extremo** diseñado específicamente bajo la normativa chilena. Integra:

- **Ingesta continua de condiciones macroeconómicas:** Conexión a la API del Banco Central de Chile (UF diaria, TPM) y a las series de la Comisión para el Mercado Financiero (CMF).
- **Web scraping headless en vivo:** Monitoreo automatizado con Playwright de los simuladores hipotecarios públicos de **7 entidades bancarias en Chile** (BancoEstado vía Casaverso, Banco Santander, BCI, Banco de Chile/Toctoc, Banco Itaú, Consorcio, Banco Falabella y Banco Internacional).
- **Extracción inteligente de cartolas (PDF):** Procesamiento de estados de cuenta hipotecarios reales mediante regex estructurado calibrado a la banca chilena y respaldo con LLMs y Pydantic.
- **Motor cuantitativo de alta precisión:** Amortización francesa y alemana en UF y CLP, recargo actuarial de desgravamen por edad, modelado de prepagos parciales y análisis de estrés para créditos con tasa mixta.
- **Doble interfaz:** Una **API REST moderna con FastAPI** para consumo programático y un **Dashboard interactivo en Streamlit** con gráficos dinámicos en Plotly y generación de informes ejecutivos en PDF mediante ReportLab.

---

## 3. Arquitectura General del Sistema

El proyecto sigue una arquitectura modular en capas desacopladas, lo que permite probar, escalar y mantener cada subsistema de forma independiente.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          INGESTA DE DATOS                              │
│  ┌───────────────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│  │   API Banco Central   │  │   Estadísticas    │  │ Web Scraping   │  │
│  │  - UF diaria en vivo  │  │   CMF (Tasas      │  │ Headless       │  │
│  │  - TPM (4.50%)        │  │   Promedio Sis.)  │  │ (Playwright)   │  │
│  └───────────┬───────────┘  └─────────┬─────────┘  └────────┬───────┘  │
└──────────────┼────────────────────────┼─────────────────────┼──────────┘
               │                        │                     │
               ▼                        ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  CAPA DE ALMACENAMIENTO & PERSISTENCIA                 │
│  DuckDB (Local / In-Process / Concurrencia segura con fallback RAM)   │
│  - macro_series  |  bank_offers  |  saved_simulations                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        MOTOR FINANCIERO (CORE)                         │
│  • Amortización Francesa y Alemana (Vectorizado con NumPy)             │
│  • Costos Normativos de Cambio (Ley 21.236 + DL 3475 + LGB Art. 100)  │
│  • Métricas: VPN (UF), Payback Dinámico, Ahorro Vida del Crédito      │
│  • Módulo Avanzado: Prepagos, Tasa Mixta (Monte Carlo), Actuarial     │
└───────────────────────▲────────────────────────▲───────────────────────┘
                        │                        │
┌───────────────────────┴──────┐  ┌──────────────┴───────────────────────┐
│     EXTRACCIÓN DOCUMENTAL    │  │        CAPAS DE CONSUMO & UX         │
│  • Cartolas PDF (pypdf)      │  │  • FastAPI REST API (Swagger UI)     │
│  • Heurísticas Regex Chile   │  │  • Streamlit Web App (8 Pestañas)    │
│  • Fallback LLM estructurado │  │  • Comparador Head-to-Head           │
│  • Modal de Confirmación     │  │  • Reportes Ejecutivos PDF           │
└──────────────────────────────┘  └──────────────────────────────────────┘
```

### Estructura del Repositorio

```text
HipoRefi-CL/
├── .github/workflows/ci.yml       # Integración continua (lint ruff + pytest 106 tests)
├── data/                          # Base de datos DuckDB y series históricas
│   └── market_rates.duckdb
├── docs/                          # Especificaciones matemáticas, legales y blog post
│   ├── PROYECTO_REFINANCIAMIENTO_HIPOTECARIO.md
│   └── DOCUMENTACION_Y_ARTICULO_BLOG.md
├── scripts/                       # Herramientas CLI de simulación y scraping
│   ├── demo_evaluacion.py         # Demostración cuantitativa completa por consola
│   └── sync_live_market.py        # Sincronización CLI con Playwright hacia DuckDB
├── src/
│   ├── core/                      # Núcleo matemático y financiero puro
│   │   ├── amortizer.py           # Amortización francesa y alemana en UF
│   │   ├── switching_costs.py     # Gastos de cambio bajo Ley 21.236 y LGB
│   │   ├── metrics.py             # VPN, Payback dinámico, comparador Head-to-Head
│   │   └── advanced_financial.py  # Prepagos, estrés tasa mixta y curvas actuariales
│   ├── scrapers/                  # Clientes macroeconómicos y web scrapers
│   │   ├── bcch_client.py         # Cliente API Banco Central de Chile
│   │   ├── cmf_client.py          # Cliente de series históricas CMF
│   │   ├── bank_simulators.py     # Fallback y cotizadores de mercado
│   │   ├── headless_scrapers.py   # Scrapers Playwright (7 entidades bancarias)
│   │   └── market_service.py      # Orquestador unificado de mercado
│   ├── parsers/                   # Procesamiento de estados de cuenta
│   │   ├── pdf_reader.py          # Extractor de texto crudo con pypdf
│   │   ├── statement_extractor.py # Regex determinista para banca chilena
│   │   └── statement_llm.py       # Extracción estructurada vía LLM
│   ├── reports/                   # Generación de informes PDF
│   │   └── pdf_generator.py       # ReportLab con tablas y gráficos vectoriales
│   ├── data/                      # Capa de datos y persistencia
│   │   └── market_store.py        # Store DuckDB thread-safe y migraciones
│   └── app/                       # Interfaces de usuario y APIs
│       ├── api.py                 # FastAPI backend con OpenAPI/Swagger
│       ├── schemas.py             # Modelos de validación Pydantic v2
│       ├── dashboard.py           # Aplicación web Streamlit (8 pestañas)
│       └── charts.py              # Visualizaciones interactivas con Plotly
├── tests/                         # Suite de 106 pruebas unitarias e integrales
├── Dockerfile                     # Imagen multi-stage optimizada
├── docker-compose.yml             # Despliegue conjunto FastAPI + Streamlit + DuckDB
└── pyproject.toml                 # Gestión de dependencias con uv y hatchling
```

---

## 4. El Núcleo Cuantitativo y Financiero (La Matemática Real)

Uno de los pilares de HipoRefi-CL es que **toda la matemática se formula en Unidades de Fomento (UF)**. La inflación es tratada como neutral dentro del modelo: si se analizara en pesos nominales a 25 años, las cifras resultarían distorsionadas y carentes de significado financiero comparable. Los pesos se utilizan exclusivamente para visualizar el desembolso mensual actual según el valor del día de la UF.

### 4.1. Amortización Francesa vs. Amortización Alemana en UF

#### Sistema Francés (Estándar de la Banca Chilena)
El sistema francés se caracteriza por un **dividendo financiero constante** $D_f$ a lo largo de toda la vida del crédito.

Dado:
- $S_0$: Saldo de capital insoluto remanente (UF).
- $i_a$: Tasa de interés anual nominal pactada.
- $n$: Número de dividendos mensuales remanentes.

La tasa de interés mensual efectiva bajo convención chilena se calcula como:
$$r = (1 + i_a)^{1/12} - 1$$

El dividendo financiero mensual constante (sin seguros) es:
$$D_f = S_0 \cdot \frac{r(1 + r)^n}{(1 + r)^n - 1}$$

En cada mes $t \in \{1, 2, \dots, n\}$:
- Interés devengado: $I_t = S_{t-1} \cdot r$
- Amortización de capital: $A_t = D_f - I_t$
- Saldo final de capital: $S_t = S_{t-1} - A_t$

#### Sistema Alemán (Amortización de Capital Constante)
En el sistema alemán, la amortización de capital es fija cada mes:
$$A_t = \frac{S_0}{n} \quad \forall t$$

El dividendo financiero es decreciente en el tiempo, ya que los intereses disminuyen linealmente:
$$I_t = S_{t-1} \cdot r$$
$$D_f(t) = A_t + I_t = \frac{S_0}{n} + S_{t-1} \cdot r$$

**Hallazgo Cuantitativo:** A igualdad de tasa y plazo, el sistema alemán amortiza capital mucho más rápido al inicio, lo que reduce el total acumulado de intereses entre un 10% y un 18% respecto al sistema francés. HipoRefi-CL permite comparar ambos sistemas directamente en su módulo avanzado.

---

### 4.2. La Anatomía de los Seguros Obligatorios

En Chile, todo crédito hipotecario exige legalmente dos seguros:

1. **Seguro de Incendio y Sismo:**  
   Se calcula sobre el valor de tasación del inmueble deduciendo el terreno (valor de reconstrucción $V_{\text{rec}}$). Es un valor fijo en UF mes a mes:
   $$g_{\text{inc}} = V_{\text{rec}} \cdot \tau_{\text{inc}}$$

2. **Seguro de Desgravamen (con Curva Actuarial por Edad):**  
   Cubre el saldo insoluto en caso de fallecimiento o invalidez total del deudor. Su tasa mensual por mil $\tau_{\text{desg}}$ depende directamente de la **edad alcanzada** por el titular en cada período.

En `src/core/advanced_financial.py`, implementamos una curva actuarial calibrada según las tablas de mortalidad chilenas MI-2006 y las licitaciones colectivas vigentes:

| Tramo Etario | Tasa Mensual por Mil ($\tau_{\text{desg}}$) | Ejemplo para Saldo de 3.000 UF |
| :---: | :---: | :---: |
| $\le 30$ años | $0.0150\%$ ($0.150$ ‰) | $0.450$ UF/mes |
| $31 - 40$ años | $0.0220\%$ ($0.220$ ‰) | $0.660$ UF/mes |
| $41 - 50$ años | $0.0380\%$ ($0.380$ ‰) | $1.140$ UF/mes |
| $51 - 60$ años | $0.0750\%$ ($0.750$ ‰) | $2.250$ UF/mes |
| $61 - 70$ años | $0.1600\%$ ($1.600$ ‰) | $4.800$ UF/mes |
| $> 70$ años | $0.3200\%$ ($3.200$ ‰) | $9.600$ UF/mes |

Además, el sistema evalúa la **regla de asegurabilidad técnica al vencimiento**: la banca suele rechazar créditos cuyo término supere los 75 u 80 años de edad del titular.

---

### 4.3. Los Costos de Cambio y la Regulación Chilena

Para migrar una hipoteca a un nuevo banco $k$, se incurre en una serie de gastos de cierre regulados por ley:

$$G_k = \text{Prepago}(S_0) + \text{Tasación} + \text{Estudio de Títulos} + \text{Notaría} + \text{Conservador (CBR)} + \text{Timbres (DL 3475)}$$

HipoRefi-CL implementa con exactitud cada restricción legal en `src/core/switching_costs.py`:

1. **Comisión de Prepago (Ley General de Bancos Art. 100):**  
   Para créditos para la vivienda no superiores a 5.000 UF, la ley establece un tope máximo estricto: **no puede exceder el equivalente a 1.5 meses de intereses pactados** sobre el capital que se prepaga:
   $$\text{Prepago}(S_0) = 1.5 \cdot (S_0 \cdot r_0)$$

2. **Exención de Timbres y Estampillas (D.L. 3475):**  
   Si el nuevo crédito se destina **exclusivamente al refinanciamiento** del saldo anterior, la operación goza de **exención total (0 UF)** del impuesto de timbres (que normalmente es de 0.8%). Si el deudor solicita fondos frescos adicionales ("fines generales"), solo el saldo marginal tributa al 0.8%.

3. **Aranceles del Conservador de Bienes Raíces (Ley N° 21.236):**  
   Bajo portabilidad financiera con subrogación, el arancel de inscripción registral goza de un **descuento legal del 50%**, modelado como un $\sim 0.1\%$ del saldo insoluto con cota mínima de 1.5 UF y tope de 12.0 UF.

4. **Gastos Operacionales Fijos:**  
   Tasación ($\sim 3.0$ UF), Estudio de Títulos ($\sim 4.0$ UF) y Notaría regulada ($\sim 1.0$ UF).

---

### 4.4. Métricas de Decisión: VPN Descontado, Payback Dinámico y Semáforo Patrimonial

El sistema compara los flujos mensuales del crédito actual $D_0(t)$ frente a la nueva oferta $D_k(t)$ a una **tasa de descuento real del deudor $\delta$** (por defecto $2.5\%$ anual real en UF, equivalente al costo de oportunidad o renta fija indexada):

$$\Delta F_t = D_0(t) - D_k(t)$$

#### Valor Presente Neto (VPN)
- **Gastos pagados al contado en $t=0$:**
  $$\text{VPN}_k = -G_k + \sum_{t=1}^{n_k} \frac{\Delta F_t}{(1 + \delta)^t}$$
- **Gastos financiados en el nuevo saldo ($S_k = S_0 + G_k$):**
  $$\text{VPN}_k = \sum_{t=1}^{n_k} \frac{D_0(t) - D_k(t; S_0 + G_k)}{(1 + \delta)^t}$$

#### Período de Recuperación Dinámico (*Payback* Descontado $t^*$)
Es el mes exacto en que la sumatoria acumulada de ahorros mensuales descontados absorbe íntegramente los gastos de cambio:
$$t^* = \min \left\{ T \in [1, n_k] \;\middle|\; \sum_{t=1}^{T} \frac{\Delta F_t}{(1 + \delta)^t} \ge G_k \right\}$$

#### El Semáforo Patrimonial
Para evitar análisis basados únicamente en la intuición, HipoRefi-CL clasifica cada alternativa con reglas deterministas:
- 🟢 **RECOMENDADO:** $\text{VPN} > 15\text{ UF}$ y $t^* \le 36\text{ meses}$.
- 🟡 **EVALUAR CON CAUTELA:** $\text{VPN} > 0\text{ UF}$, pero $36 < t^* \le 60\text{ meses}$ (riesgo si la propiedad se vende en el mediano plazo).
- 🔴 **NO CONVIENE:** $\text{VPN} \le 0\text{ UF}$ o $t^* > 60\text{ meses}$ o aumento neto de intereses por extensión de plazo.

---

### 4.5. Módulo Avanzado: Abonos Extraordinarios y Riesgo de Tasa Mixta

En `src/core/advanced_financial.py` se desarrollaron dos herramientas cuantitativas complementarias:

1. **Optimizador de Prepagos Parciales (LGB Art. 100):**  
   Evalúa la inyección de capital extraordinario (ej. un bono laboral o liquidación) enfrentando dos alternativas:
   - **Opción A (Reducción de Plazo):** Mantiene el dividendo y acorta la duración del crédito. Genera un ahorro masivo de intereses y el mayor VPN.
   - **Opción B (Reducción de Dividendo):** Mantiene el plazo y disminuye la carga mensual inmediata. Proporciona alivio de liquidez a corto plazo.

2. **Analizador de Riesgo de Tasa Mixta vs. Fija:**  
   Muchos bancos ofrecen tasas mixtas (fijas por 3 o 5 años y luego flotantes indexadas a TAB/TPM). El sistema aplica **matrices de estrés macroeconómico**:
   - Escenario Base (tasa proyectada neutral).
   - Escenario Bajista ($-150\text{ bps}$).
   - Escenario Alcista ($+150\text{ bps}$).
   - Escenario Severo ($+300\text{ bps}$).  
   Calcula la **Tasa de Quiebre (*Breakeven Floating Rate*)**: la tasa máxima a la que el crédito mixto puede llegar en su fase variable antes de que el costo total supere al de un crédito de tasa fija garantizada.

---

## 5. Ingesta de Mercado y Web Scraping Headless en Vivo

Una plataforma analítica es tan buena como los datos que la alimentan. En lugar de utilizar datos ficticios, HipoRefi-CL cuenta con una infraestructura de recolección en dos niveles.

### 5.1. Conexión Macroeconómica (Banco Central y CMF)

- **API del Banco Central de Chile:** Consulta el valor diario de la UF y la Tasa de Política Monetaria (**TPM en 4.50%**).
- **Estadísticas de la CMF:** Descarga y normaliza los promedios de tasas hipotecarias reales ponderadas del sistema bancario chileno.

### 5.2. Web Scraping Bancario con Playwright (7 Entidades Financieras)

En Chile, los bancos no ofrecen APIs públicas para cotizar hipotecas. Sus simuladores residen en aplicaciones web enriquecidas (SPAs con React, Angular o Vue), a menudo protegidas por mecanismos antibot o validaciones de RUT.

En `src/scrapers/headless_scrapers.py`, construí un coordinador que ejecuta navegadores **Chromium headless vía Playwright** para interactuar directamente con los portales:

1. **BancoEstado:** Migrado al nuevo portal de vivienda inmobiliaria **Casaverso**.
2. **Banco Santander:** Navegación por el formulario de simulación de crédito hipotecario estándar.
3. **BCI (Banco de Crédito e Inversiones):** Extracción de tasas y CAE en su cotizador público.
4. **Banco de Chile:** Scraper adaptado al portal abierto de Toctoc integrado con la banca.
5. **Banco Itaú:** Cotización de dividendo en UF y desglose de seguros.
6. **Consorcio:** Simulación de crédito para mutuarias y banco.
7. **Banco Falabella y Banco Internacional:** Scrapers con endpoints REST internos y parsing HTML con fallback mediante regex nativo si `BeautifulSoup` no está presente.

Cada cotización extraída se normaliza en una estructura `ScrapedBankQuote` que calcula:
- Tasa anual nominal pactada.
- Dividendo financiero y dividendo total con seguros.
- Carga Anual Equivalente (CAE).
- Spread sobre el benchmark del Banco Central.

El script de sincronización `scripts/sync_live_market.py` permite correr la actualización en segundo plano, en modo *dry-run* o con salida JSON para tareas programadas (cron):

```bash
python scripts/sync_live_market.py --principal 3200 --term 20 --dry-run
```

### 5.3. Persistencia Embebida y Concurrencia con DuckDB

Para el almacenamiento se eligió **DuckDB** (`data/market_rates.duckdb`). DuckDB ofrece almacenamiento columnar OLAP de alto rendimiento sin requerir un servidor de base de datos externo (como PostgreSQL o MySQL).

#### Gestión de Concurrencia Thread-Safe
Cuando dos procesos intentan acceder a un mismo archivo DuckDB en disco (por ejemplo, el servidor Uvicorn de FastAPI y la instancia de Streamlit corriendo simultáneamente), DuckDB bloquea el archivo para prevenir corrupción. En `src/data/market_store.py` se implementó un mecanismo de **fallback transparente a memoria (`:memory:`)**, permitiendo que ambos procesos operen sin interrupción y sin conflictos de bloqueo.

Tablas maestras:
- `macro_series`: Series temporales de UF, TPM y promedios CMF.
- `bank_offers`: Ofertas vigentes de cada banco con tasas y spreads.
- `saved_simulations`: Escenarios guardados por los usuarios para auditoría o seguimiento comercial.

---

## 6. Extracción Documental Inteligente de Cartolas Bancarias

Uno de los principales puntos de fricción para un deudor es tener que transcribir los datos de su estado de cuenta bancario: saldo de capital, tasa pactada, meses restantes y seguros.

### 6.1. Pipeline Híbrido: Regex Heurístico + Esquemas Pydantic con Fallback LLM

En `src/parsers/` diseñamos un pipeline híbrido en dos fases:

1. **Fase Heurística (Determinista y Local):**  
   Utiliza `pypdf` para extraer el texto y una batería de expresiones regulares calibradas para los formatos de cartola de los principales bancos de Chile (Banco de Chile, Santander, BancoEstado, BCI, Scotiabank, Itaú, etc.). Incluye un parser numérico (`parse_chilean_number`) que resuelve las distintas convenciones de puntuación chilenas (uso de puntos para miles y comas para decimales, o viceversa).  
   *Ventaja:* Tiempo de respuesta instantáneo (< 50 ms), costo cero y privacidad total.

2. **Fase LLM (Fallback Estructurado):**  
   Si la cartola presenta un formato tabular no estándar o el motor determinista detecta campos incompletos, el texto se envía a un modelo de lenguaje (OpenAI / Claude / Gemini) con un esquema estricto validado por **Pydantic** (`MortgageStatementExtraction`).

Campos extraídos:
- Nombre de la entidad emisora y número de operación.
- Saldo insoluto de capital en UF.
- Tasa de interés anual nominal.
- Plazo remanente en meses (o cuotas pagadas / cuotas totales).
- Monto del dividendo mensual actual en UF o CLP.
- Desglose de seguros (incendio, sismo, desgravamen).

### 6.2. Validación Humana en el Loop (Modal Interactivo en UI)

En la interfaz de Streamlit, al arrastrar y soltar un PDF, el sistema abre un **diálogo modal de confirmación**. El usuario puede previsualizar los campos detectados, ajustar cualquier discrepancia si la cartola tiene texto poco legible, y confirmar los valores antes de recalcular los modelos.

---

## 7. Motor de Generación de Informes Ejecutivos en PDF

Para que el análisis sea útil frente a un ejecutivo bancario o corredor de propiedades, HipoRefi-CL genera un **Informe Ejecutivo y Dictamen de Portabilidad Financiera** en formato PDF de 2 páginas con diseño profesional (`src/reports/pdf_generator.py`).

Construido íntegramente con **ReportLab**, el generador incluye:
- **Diseño Editorial Corporativo:** Paleta de colores institucional (Navy `#1B4F72`, Slate `#2C3E50`), tipografía jerárquica y márgenes calibrados para impresión.
- **Gráficos Vectoriales Nativos:** Renderizados mediante `reportlab.graphics.shapes` (gráficos de barras comparativas y curvas de amortización) como elementos `Flowable` puros, eliminando dependencias pesadas como Matplotlib o renderizado web headless.
- **Dictamen de Portabilidad Formal:** Con sello de recomendación patrimonial (badge verde/amarillo/rojo), desglose normativo de costos de la Ley 21.236 y tabla resumen de flujos de caja.

El PDF puede descargarse con un clic desde el Dashboard o generarse programáticamente mediante el endpoint `POST /api/v1/generate-report/pdf` de la API.

---

## 8. Capas de Consumo: API REST (FastAPI) y Dashboard (Streamlit)

### 8.1. API Backend RESTful con Validación Pydantic v2

El backend en **FastAPI** (`src/app/api.py`) expone una API completa con documentación interactiva Swagger (`/docs`):

| Método | Endpoint | Descripción |
| :---: | :--- | :--- |
| `GET` | `/health` | Chequeo de estado de la API y de DuckDB. |
| `POST` | `/api/v1/simulate` | Simula la tabla de desarrollo de amortización francesa en UF. |
| `POST` | `/api/v1/evaluate-refinance` | Evalúa una propuesta frente al crédito actual (VPN, Payback, Semáforo). |
| `POST` | `/api/v1/compare/head-to-head` | Comparación cuantitativa directa lado a lado entre dos bancos. |
| `POST` | `/api/v1/advanced/prepayment` | Simulación de abonos extraordinarios (reducir plazo vs cuota). |
| `POST` | `/api/v1/advanced/mixed-rate-stress` | Matriz de estrés y tasa de quiebre para créditos de tasa mixta. |
| `POST` | `/api/v1/advanced/insurability-check` | Evaluación actuarial de desgravamen y tope de edad. |
| `POST` | `/api/v1/advanced/german-schedule` | Tabla y comparación de amortización alemana vs francesa. |
| `POST` | `/api/v1/extract-statement` | Extracción de datos desde texto o upload directo de PDF. |
| `GET` | `/api/v1/market-rates` | Tasas macroeconómicas, TPM y ofertas bancarias. |
| `POST` | `/api/v1/market-rates/scrape-sync` | Dispara el scraping headless en vivo de Playwright. |
| `GET` | `/api/v1/simulations` | Listado de simulaciones guardadas en DuckDB (CRUD completo). |
| `POST` | `/api/v1/generate-report/pdf` | Generación y descarga binaria del informe PDF ejecutivo. |

---

### 8.2. Dashboard Analítico de 8 Pestañas e Interactividad Plotly

El frontend desarrollado en **Streamlit** (`src/app/dashboard.py`) organiza el análisis en **8 pestañas especializadas**:

1. 🏆 **Comparador de Mercado:** Ranking de entidades según mayor ganancia neta patrimonial (VPN en UF y CLP), ahorro mensual y desglose legal de gastos de cambio.
2. 🥊 **Comparador Head-to-Head:** Enfrentamiento directo de dos bancos o contraofertas con gráfico de brecha patrimonial y dictamen de dominancia.
3. 📈 **Punto de Equilibrio & Payback:** Curva de recuperación descontada que visualiza el mes exacto de Break-Even frente a los costos de cambio.
4. 🎛️ **Simulador a Medida & Heatmap 2D:** Sliders interactivos para evaluar cualquier propuesta libre y un mapa de calor bidimensional de **Tasa vs. Plazo**.
5. ⚠️ **Detector de la "Falacia del Dividendo":** Muestra gráfica del sobrecosto en intereses al alargar plazos para rebajar cuotas mensuales.
6. 📋 **Tabla de Amortización Francesa:** Detalle cuota a cuota con desglose de amortización, interés devengado, seguros y botón de descarga en CSV.
7. 🔬 **Módulo Financiero Avanzado:** Con 4 sub-pestañas:
   - *Abonos Extraordinarios:* Simulación de prepagos y comparación plazo vs. cuota.
   - *Riesgo Tasa Mixta:* Matriz de estrés Monte Carlo y tasa de quiebre.
   - *Desgravamen Actuarial:* Curva por edad y gauge de asegurabilidad técnica.
   - *Amortización Alemana:* Ahorro en intereses frente al sistema francés.
8. 💾 **Historial y Simulaciones Guardadas:** Persistencia en DuckDB para guardar, recargar o auditar escenarios a lo largo del tiempo.

### 8.3. Compartición por URL Parametrizada

El dashboard permite compartir escenarios de simulación directamente a través de parámetros en la URL:
- `http://localhost:8501/?balance=3200&rate=5.2&months=180&bank=Santander`
- `http://localhost:8501/?sim_id=<UUID>`

Al abrir el enlace, el sistema precarga todas las variables automáticamente.

---

## 9. Infraestructura, DevOps y Calidad de Código

### 9.1. Entorno Ultrarrápido con uv

El proyecto utiliza [`uv`](https://github.com/astral-sh/uv) (de Astral) para la gestión del entorno y dependencias. Las instalaciones y resoluciones de dependencias se realizan en cuestión de milisegundos, reemplazando con ventaja a `pip` y `poetry`.

```bash
# Crear entorno virtual e instalar en modo editable con herramientas de desarrollo
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 9.2. Docker y Docker Compose

El proyecto cuenta con un `Dockerfile` optimizado y un `docker-compose.yml` que orquesta la API REST y el Dashboard en contenedores conectados a un volumen persistente compartido para DuckDB:

```bash
# Levantar el ecosistema completo con un comando
docker compose up --build -d
```
- Dashboard: `http://localhost:8501`
- API y Swagger UI: `http://localhost:8000/docs`

### 9.3. Suite de Pruebas Automatizadas y GitHub Actions CI

La confiabilidad matemática y de software está respaldada por una suite de **106 pruebas unitarias e integrales** con `pytest` que verifican:
- Fórmulas de amortización francesa y alemana.
- Restricciones legales de la Ley 21.236 y Art. 100 LGB.
- Parsers de cartolas y normalización de formatos numéricos chilenos.
- Endpoints de FastAPI y contratos Pydantic.
- Scrapers headless y generador de reportes PDF.

```bash
# Ejecutar suite completa con cobertura
pytest tests/ -v
```

El pipeline de **GitHub Actions** (`.github/workflows/ci.yml`) ejecuta en cada commit:
1. Verificación de estilo y calidad con `ruff check .`.
2. Ejecución integral de las pruebas automatizadas en Python 3.11.

---

## 10. Hoja de Ruta de Desarrollo (Roadmap de 10 Hitos Completados)

| Hito | Nombre | Logro Técnico Principal |
| :---: | :--- | :--- |
| **Hito 1** | **Core Matemático** | Amortización francesa en UF, seguros obligatorios, costos Ley 21.236 y cálculo de VPN/Payback. |
| **Hito 2** | **Ingesta de Mercado** | Clientes BCCh y CMF, persistencia columnar en DuckDB con manejo de concurrencia. |
| **Hito 3** | **Extracción de Cartolas** | Parser PDF determinista con regex chileno y fallback estructurado con LLM + Pydantic. |
| **Hito 4** | **API REST Backend** | FastAPI con validación Pydantic v2, endpoints de simulación y documentación OpenAPI. |
| **Hito 5** | **Dashboard Interactivo** | Interfaz web en Streamlit, 5 pestañas de análisis iniciales y gráficos Plotly. |
| **Hito 6** | **DevOps & Contenedores** | Dockerfile, `docker-compose.yml`, configuración `.dockerignore` y pipeline CI en GitHub Actions. |
| **Hito 7** | **Informe Ejecutivo PDF** | Generador ReportLab con gráficos vectoriales nativos y dictamen de portabilidad formal. |
| **Hito 8** | **Módulo Financiero Avanzado** | Amortización alemana, simulación de abonos extraordinarios, estrés de tasa mixta y curvas actuariales. |
| **Hito 9** | **Web Scraping Headless** | Playwright headless para cotizadores en vivo de 7 bancos chilenos y CLI `sync_live_market.py`. |
| **Hito 10** | **UX Comercial Avanzada** | Comparador Head-to-Head lado a lado, persistencia de simulaciones, modal interactivo y URL sharing. |

---

## 11. Guía de Redacción para el Artículo del Blog Personal

Esta sección entrega recomendaciones para estructurar un post técnico de lectura amena en tu sitio web personal.

### 11.1. Estructura Narrativa Sugerida

1. **El Gancho Inicial (The Hook):**  
   Comienza con una anécdota personal o una cifra reveladora: *"En Chile, un crédito hipotecario promedio acumula en 25 años más de 1.500 UF en intereses puros. Sin embargo, menos del 10% de los deudores evalúa refinanciar. ¿Por qué nos cuesta tanto tomar esta decisión?"*
2. **El Diagnóstico del Problema:**  
   Explica de forma sencilla la asimetría de información y la "Falacia del Dividendo". Añade una captura del gráfico del detector de la falacia para ilustrar el punto visualmente.
3. **El Desafío de Ingeniería:**  
   Plantea por qué decidiste abordar esto construyendo software: *"Quería una herramienta que no solo me diera números, sino que modelara con rigor matemático la ley chilena (Ley 21.236, DL 3475, LGB Art. 100) y extrajera ofertas reales de la banca en tiempo real."*
4. **La Arquitectura Tecnológica:**  
   Menciona las decisiones clave de diseño:
   - ¿Por qué Python 3.11 con `uv`? (Velocidad y reproducibilidad).
   - ¿Por qué DuckDB en lugar de un servidor PostgreSQL? (Arquitectura embebida, almacenamiento columnar y cero fricción de despliegue).
   - ¿Por qué Playwright para scraping bancario? (Interacción real con SPAs bancarias modernas).
   - ¿Por qué un pipeline híbrido regex + LLM para cartolas? (Velocidad, costo y precisión).
5. **Los Resultados y la Experiencia de Usuario:**  
   Muestra capturas del Dashboard en Streamlit, el comparador Head-to-Head y el informe ejecutivo en PDF generado con ReportLab.
6. **Lecciones Aprendidas:**  
   Comparte los desafíos técnicos más interesantes que resolviste: lidiar con los bloqueos de concurrencia en DuckDB, los formatos numéricos con comas y puntos en las cartolas chilenas, y la sutileza de calcular primas de desgravamen ajustadas por edad.
7. **Conclusión y Código Abierto:**  
   Cierra invitando a la comunidad a probar la herramienta, revisar el repositorio en GitHub y compartir su experiencia.

### 11.2. Ideas de Títulos Atractivos

- *Cómo construí un motor cuantitativo para hackear la decisión del crédito hipotecario en Chile*
- *HipoRefi-CL: Finanzas cuantitativas, scraping bancario y la Ley de Portabilidad Financiera*
- *La matemática detrás de tu crédito hipotecario: Por qué bajar el dividendo puede costarte millones*
- *De una cartola bancaria en PDF a una decisión financiera óptima: Diseñando HipoRefi-CL*
- *Construyendo una plataforma financiera end-to-end con Python, DuckDB, FastAPI y Streamlit*

### 11.3. Puntos de Impacto Técnico para Mostrar a Reclutadores y Pares

Si utilizas este proyecto en tu portafolio profesional, los siguientes aspectos demuestran habilidades de ingeniería de software y finanzas cuantitativas:

- **Dominio de Finanzas Cuantitativas y Regulación:** No es un simple calculador de cuotas; modela valor presente neto descontado a tasa real de oportunidad, amortización francesa y alemana, curvas actuariales por edad y restricciones regulatorias chilenas específicas.
- **Arquitectura de Datos y Web Scraping Moderno:** Implementación de Playwright headless para automatizar cotizaciones en portales bancarios protegidos, junto con almacenamiento columnar OLAP en DuckDB.
- **Tratamiento Documental Inteligente:** Pipeline de dos niveles (regex heurístico de alta velocidad + esquemas estructurados Pydantic con fallback a LLMs).
- **Calidad de Código y Pruebas:** 106 pruebas unitarias e integrales automatizadas con `pytest`, tipado estático con dataclasses y Pydantic, linting con `ruff` y CI continuo en GitHub Actions.
- **Despliegue y Contenedorización:** Configuración completa de Docker y `docker-compose` con volúmenes persistentes y servidor de producción.
