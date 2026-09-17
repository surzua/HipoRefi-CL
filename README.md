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

Ejecutar la suite completa de pruebas financieras:

```bash
pytest tests/ -v
```

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
