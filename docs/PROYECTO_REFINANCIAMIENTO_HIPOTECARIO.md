# HipoRefi-CL: Motor Cuantitativo y Plataforma de Optimización de Refinanciamiento Hipotecario

> **Especificación Técnica, Fundamentos Matemáticos, Arquitectura de Software y Código Base**  
> *Versión:* 1.0.0  
> *Ámbito Regulatorio:* Chile (Ley N° 21.236 de Portabilidad Financiera, D.L. 3475, Ley General de Bancos)

---

## 1. Resumen Ejecutivo y Planteamiento del Problema

El crédito hipotecario representa el pasivo financiero más voluminoso y de mayor duración en el ciclo de vida de un hogar en Chile (típicamente entre 15 y 30 años, expresado en Unidades de Fomento - UF). A pesar de que la **Ley N° 21.236 de Portabilidad Financiera** (vigente desde fines de 2020) redujo drásticamente las fricciones y los aranceles operacionales para migrar créditos entre instituciones bancarias y mutuarias, menos del 10% de los deudores hipotecarios realiza un monitoreo activo de su costo de deuda.

### El Problema Asimétrico
1. **Asimetría de Información:** Las entidades financieras cotizan a través de la Carga Anual Equivalente (CAE) o dividendo inicial, pero el deudor no tiene herramientas accesibles para aislar el sobrecosto de seguros colectivos frente a la tasa de interés pura.
2. **La Falacia del Dividendo:** Muchos deudores caen en la trampa de "reducir el dividendo mensual" re-pactando a un plazo mayor (ej. extender de 18 a 25 años restantes), lo que genera una destrucción patrimonial neta masiva por acumulación de intereses.
3. **Complejidad de los Costos de Cambio:** El cálculo del punto de equilibrio (*break-even* o *payback*) involucra variables no triviales: comisión legal de prepago, aranceles registrales con y sin subrogación, exenciones tributarias de timbres y estampillas, y recotización del seguro de desgravamen ajustado por la edad actual del titular.

### Objetivo del Proyecto
Construir una solución *end-to-end* que automatice:
1. La ingesta periódica de tasas de referencia del Banco Central de Chile (BCCh) y cotizaciones reales de simuladores bancarios locales.
2. El procesamiento no estructurado de estados de cuenta hipotecarios (cartolas bancarias en PDF) vía visión/LLM estructurado.
3. El cálculo financiero riguroso de tablas de amortización en UF y CLP, Valor Presente Neto (VPN), Tasa Interna de Retorno (TIR) y período de amortización del costo de cambio.
4. La generación de recomendaciones ejecutivas comprensibles mediante un semáforo de decisión patrimonial.

---

## 2. Marco Teórico y Formulación Matemática

El motor financiero opera fundamentalmente en **Unidades de Fomento (UF)** para aislar la inflación, convirtiendo a pesos chilenos (CLP) únicamente para efectos de visualización y estimación de desembolsos inmediatos.

### 2.1. Dinámica del Sistema Francés de Amortización en UF

Sea un crédito con:
- $S_0$: Saldo de capital insoluto remanente (UF).
- $i_a$: Tasa de interés anual nominal contracturada en UF.
- $n$: Número de dividendos mensuales remanentes.

La tasa de interés mensual efectiva viene dada por:
$$r = (1 + i_a)^{1/12} - 1 \quad 	ext{o bien} \quad r = \frac{i_a}{12} \quad \text{(según convención de la entidad)}$$

El dividendo financiero mensual constante (sin seguros) $D_f$ se calcula mediante la anualidad francesa:
$$D_f = S_0 \cdot \frac{r(1 + r)^n}{(1 + r)^n - 1}$$

Para cada período $t \in \{1, 2, \dots, n\}$:
1. **Cuota de Interés del período $t$:**
   $$I_t = S_{t-1} \cdot r$$
2. **Cuota de Amortización de Capital del período $t$:**
   $$A_t = D_f - I_t = D_f - (S_{t-1} \cdot r)$$
3. **Saldo Insoluto al cierre del período $t$:**
   $$S_t = S_{t-1} - A_t = S_{t-1}(1 + r) - D_f$$

### 2.2. Estructura de Seguros Obligatorios en Chile

El dividendo total pagado mensualmente por el cliente es:
$$D_{\text{total}}(t) = D_f + g_{\text{desg}}(t) + g_{\text{inc}}$$

Donde:
- **Seguro de Desgravamen ($g_{\text{desg}}(t)$):** Se calcula sobre el saldo insoluto $S_{t-1}$ o sobre el monto inicial $S_{\text{orig}}$ según la póliza. En el estándar chileno licitado, se calcula sobre el saldo insoluto con una tasa mensual por mil $\tau_{\text{desg}}(\text{edad}_t)$:
  $$g_{\text{desg}}(t) = S_{t-1} \cdot \tau_{\text{desg}}(\text{edad}_t)$$
  *Importante:* Si el deudor contrata un nuevo crédito $k$ años después del original, su prima por mil aumenta conforme a la tabla de mortalidad de la póliza colectiva:
  $$\tau_{\text{desg}}(\text{edad}_0 + \Delta t) > \tau_{\text{desg}}(\text{edad}_0)$$
- **Seguro de Incendio y Sismo ($g_{\text{inc}}$):** Se calcula sobre el valor de tasación del inmueble excluyendo el terreno (valor de reconstrucción $V_{\text{rec}}$):
  $$g_{\text{inc}} = V_{\text{rec}} \cdot \tau_{\text{inc}}$$

---

### 2.3. Costo Total de Migración / Gastos de Cierre ($G_k$)

Para refinanciar el crédito con una entidad $k$, se incurre en una serie de costos operativos regidos por la ley chilena:

$$G_k = \text{Prepago}(S_0) + \text{Tasación} + \text{Estudio Títulos} + \text{Notaría} + \text{Conservador (CBR)} + \text{Impuesto D.L. 3475}$$

#### Detalle de Componentes Regulatorios:
1. **Comisión de Prepago:**
   Regulada por el Art. 100 de la Ley General de Bancos. Para créditos en UF no superiores a 5.000 UF, la comisión no puede exceder el equivalente a **1.5 meses de intereses pactados** sobre el capital que se prepaga:
   $$\text{Prepago}(S_0) = 1.5 \cdot (r_0 \cdot S_0)$$
2. **Impuesto de Timbres y Estampillas (D.L. 3475):**
   - Si el nuevo crédito se destina **exclusivamente al refinanciamiento** del saldo anterior, la operación se encuentra **exenta** del impuesto del 0.8% sobre el capital refinanciado.
   - Si se solicita dinero adicional ("fines generales"), solo el saldo marginal tributa al 0.066% mensual con tope del 0.8%.
3. **Aranceles del Conservador de Bienes Raíces (CBR) bajo Portabilidad con Subrogación (Ley 21.236):**
   - El arancel de inscripción de hipoteca y gravámenes goza de un **descuento legal del 50%** sobre el arancel regular del CBR.
   - Típicamente oscila entre $0.1\%$ y $0.15\%$ del saldo insoluto, con topes fijados por decreto.
4. **Gastos Operacionales Fijos (Tasación, Estudio de Títulos, Notaría):**
   - Tasación: $\sim 2.5$ a $4.0\text{ UF}$.
   - Estudio de Títulos: $\sim 3.0$ a $5.0\text{ UF}$.
   - Notaría con subrogación: $\sim 0.8$ a $1.5\text{ UF}$.

---

### 2.4. Evaluación Financiera: VPN y Período de Recuperación

Sea:
- $D_0(t)$: Flujo total del dividendo original en el mes $t$.
- $D_k(t)$: Flujo total del nuevo dividendo propuesto por el banco $k$ en el mes $t$.
- $\delta$: Tasa mensual de descuento del deudor (costo de oportunidad real en UF, tasa libre de riesgo o retorno de inversiones líquidas seguras, ej. $\sim 2.5\%$ anual real $\rightarrow \delta \approx 0.00206$ mensual).

El diferencial de flujo de caja mensual para el deudor es:
$$\Delta F_t = D_0(t) - D_k(t)$$

#### Escenario A: Gastos Operacionales pagados al contado ($G_k$ en $t=0$)
$$\text{VPN}_k = -G_k + \sum_{t=1}^{n_k} \frac{\Delta F_t}{(1 + \delta)^t}$$

#### Escenario B: Gastos Operacionales incorporados en el nuevo saldo financiado ($S_k = S_0 + G_k$)
$$\text{VPN}_k = \sum_{t=1}^{n_k} \frac{D_0(t) - D_k(t; S_0 + G_k)}{(1 + \delta)^t}$$

#### Período de Recuperación Dinámico (*Payback* Descontado $t^*$):
El menor entero $T$ tal que el ahorro acumulado descontado absorbe el desembolso inicial:
$$t^* = \min \left\{ T \in [1, n_k] \;\middle|\; \sum_{t=1}^{T} \frac{\Delta F_t}{(1 + \delta)^t} \ge G_k \right\}$$

---

## 3. Arquitectura del Sistema

El sistema sigue una arquitectura modular en capas desacopladas:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          INGESTA DE DATOS                              │
│  ┌───────────────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│  │ API BCCh (si3)        │  │ Scraping CMF      │  │ Simuladores    │  │
│  │ - UF diaria           │  │ - Tasas promedio  │  │ Bancarios Web  │  │
│  │ - TPM / Curva Tasas   │  │   por segmento    │  │ (Playwright)   │  │
│  └───────────┬───────────┘  └─────────┬─────────┘  └────────┬───────┘  │
└──────────────┼────────────────────────┼─────────────────────┼──────────┘
               │                        │                     │
               ▼                        ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       ALMACENAMIENTO & PERSISTENCIA                    │
│  DuckDB local / SQLite / PostgreSQL (series de tiempo & snapshots)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        MOTOR FINANCIERO (CORE)                         │
│  • Generador de Tablas de Desarrollo (NumPy / Vectorizado)             │
│  • Validador de Costos de Portabilidad (Ley 21.236 + DL 3475)          │
│  • Optimizador de Plazo Equivalente vs. Reducción de Plazo             │
│  • Calculador de VPN, Payback y Ahorro Patrimonial Neto                │
└───────────────────────▲────────────────────────▲───────────────────────┘
                        │                        │
┌───────────────────────┴──────┐  ┌──────────────┴───────────────────────┐
│     EXTRACCIÓN DOCUMENTAL    │  │        CAPA DE PRESENTACIÓN          │
│  • Ingesta de PDF (Cartola)  │  │  • FastAPI (REST API Backend)        │
│  • Parser OCR / pypdf        │  │  • Streamlit / Dashboard Interactivo │
│  • Pydantic + LLM Extraction │  │  • Curvas Break-even con Plotly      │
└──────────────────────────────┘  └──────────────────────────────────────┘
```

---

## 4. Estructura del Repositorio

```text
hipo-refi-cl/
├── README.md
├── pyproject.toml
├── .env.example
├── data/
│   ├── raw/
│   ├── processed/
│   └── market_rates.duckdb
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── amortizer.py        # Generación de tablas de amortización francesa
│   │   ├── switching_costs.py  # Modelado de gastos operacionales y Ley 21.236
│   │   └── metrics.py          # Cálculo de VPN, TIR, Payback y matrices
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── bcch_client.py      # Conector oficial API Banco Central
│   │   ├── cmf_client.py       # Descargador estadístico CMF
│   │   └── bank_simulators.py  # Ingesta de tasas comerciales vigentes
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── pdf_reader.py       # Extracción de texto y tablas de cartolas
│   │   └── statement_llm.py    # Schema Pydantic y extracción vía LLM
│   └── app/
│       ├── __init__.py
│       ├── api.py              # Endpoints FastAPI
│       └── dashboard.py        # Interfaz web en Streamlit
└── tests/
    ├── test_amortizer.py
    ├── test_switching_costs.py
    └── test_metrics.py
```

---

## 5. Código Base Inicial (Core Modules)

A continuación se presentan las implementaciones productivas del núcleo financiero, listas para ejecución y prueba.

### 5.1. `src/core/amortizer.py`
Módulo encargado de generar tablas de desarrollo exactas mes a mes.

```python
"""Motor de amortización francesa para créditos hipotecarios en Chile."""

from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np


@dataclass
class MortgageParams:
    principal: float  # Saldo insoluto o monto inicial en UF
    annual_rate: float  # Tasa anual nominal (ej: 0.045 para 4.5%)
    months_remaining: int  # Plazo restante en meses
    fire_insurance_monthly_uf: float = 0.0  # Monto fijo en UF o calculado
    life_insurance_rate_monthly: float = 0.00028  # Prima por mil mensual sobre saldo


class FrenchAmortizer:
    @staticmethod
    def monthly_interest_rate(annual_rate: float) -> float:
        """Calcula la tasa mensual efectiva bajo convención chilena estándar."""
        return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0

    @classmethod
    def calculate_financial_dividend(cls, principal: float, annual_rate: float, months: int) -> float:
        """Calcula el dividendo financiero puro (sin seguros) en UF."""
        if months <= 0:
            raise ValueError("El número de meses debe ser positivo.")
        r = cls.monthly_interest_rate(annual_rate)
        if r == 0:
            return principal / months
        factor = (1.0 + r) ** months
        return principal * (r * factor) / (factor - 1.0)

    @classmethod
    def generate_schedule(cls, params: MortgageParams) -> List[Dict[str, Any]]:
        """Genera la tabla de desarrollo mes a mes con desglose completo."""
        r = cls.monthly_interest_rate(params.annual_rate)
        d_f = cls.calculate_financial_dividend(params.principal, params.annual_rate, params.months_remaining)

        schedule = []
        current_balance = params.principal

        for month in range(1, params.months_remaining + 1):
            interest = current_balance * r
            amortization = d_f - interest
            
            # Ajuste de cierre para el último mes
            if month == params.months_remaining:
                amortization = current_balance
                d_f = amortization + interest
                end_balance = 0.0
            else:
                end_balance = current_balance - amortization

            # Seguros del período
            life_ins = current_balance * params.life_insurance_rate_monthly
            fire_ins = params.fire_insurance_monthly_uf
            total_dividend = d_f + life_ins + fire_ins

            schedule.append({
                "month": month,
                "start_balance_uf": round(current_balance, 4),
                "financial_dividend_uf": round(d_f, 4),
                "interest_uf": round(interest, 4),
                "amortization_uf": round(amortization, 4),
                "life_insurance_uf": round(life_ins, 4),
                "fire_insurance_uf": round(fire_ins, 4),
                "total_dividend_uf": round(total_dividend, 4),
                "end_balance_uf": round(max(0.0, end_balance), 4),
            })
            current_balance = end_balance

        return schedule
```

---

### 5.2. `src/core/switching_costs.py`
Módulo que implementa los cálculos normativos de gastos operacionales y beneficios de la Ley 21.236.

```python
"""Modelamiento de costos operacionales de refinanciamiento en Chile (Ley 21.236)."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class SwitchingCostBreakdown:
    prepayment_penalty_uf: float
    appraisal_uf: float          # Tasación
    title_deed_uf: float         # Estudio de títulos
    notary_uf: float             # Notaría (con arancel Ley 21.236)
    cbr_uf: float                # Conservador de Bienes Raíces (arancel 50%)
    stamp_tax_uf: float          # Impuesto D.L. 3475 (0 si no hay capital adicional)
    total_cost_uf: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "prepayment_penalty_uf": round(self.prepayment_penalty_uf, 2),
            "appraisal_uf": round(self.appraisal_uf, 2),
            "title_deed_uf": round(self.title_deed_uf, 2),
            "notary_uf": round(self.notary_uf, 2),
            "cbr_uf": round(self.cbr_uf, 2),
            "stamp_tax_uf": round(self.stamp_tax_uf, 2),
            "total_cost_uf": round(self.total_cost_uf, 2),
        }


class SwitchingCostCalculator:
    # Parámetros medios de mercado chileno (en UF)
    BASE_APPRAISAL_UF = 3.0
    BASE_TITLE_DEED_UF = 4.0
    BASE_NOTARY_UF = 1.0

    @classmethod
    def calculate_cbr_fee(cls, balance_uf: float) -> float:
        """
        Arancel estimado CBR con descuento del 50% por Ley de Portabilidad (subrogación).
        Aproximación empírica regulatoria: 0.1% del valor de hipoteca, con tope ~12 UF.
        """
        fee = balance_uf * 0.0010
        return min(max(1.5, fee), 12.0)

    @classmethod
    def calculate_prepayment_penalty(cls, balance_uf: float, current_annual_rate: float) -> float:
        """
        Comisión de prepago según Ley General de Bancos Art. 100:
        Máximo 1.5 meses de intereses devengados.
        """
        monthly_r = (1.0 + current_annual_rate) ** (1.0 / 12.0) - 1.0
        return 1.5 * (balance_uf * monthly_r)

    @classmethod
    def calculate_total_costs(
        cls,
        balance_uf: float,
        current_annual_rate: float,
        additional_cash_uf: float = 0.0
    ) -> SwitchingCostBreakdown:
        """Calcula el gasto de cierre total en UF para migrar el crédito."""
        penalty = cls.calculate_prepayment_penalty(balance_uf, current_annual_rate)
        appraisal = cls.BASE_APPRAISAL_UF
        title_deed = cls.BASE_TITLE_DEED_UF
        notary = cls.BASE_NOTARY_UF
        cbr = cls.calculate_cbr_fee(balance_uf)

        # Impuesto de timbres y estampillas:
        # El saldo refinanciado está exento. Solo el capital fresco tributa (máx 0.8%).
        stamp_tax = additional_cash_uf * 0.008 if additional_cash_uf > 0 else 0.0

        total = penalty + appraisal + title_deed + notary + cbr + stamp_tax

        return SwitchingCostBreakdown(
            prepayment_penalty_uf=penalty,
            appraisal_uf=appraisal,
            title_deed_uf=title_deed,
            notary_uf=notary,
            cbr_uf=cbr,
            stamp_tax_uf=stamp_tax,
            total_cost_uf=total
        )
```

---

### 5.3. `src/core/metrics.py`
Módulo de evaluación de rentabilidad del refinanciamiento (VPN, Payback, Flujos).

```python
"""Evaluación cuantitativa de decisiones de refinanciamiento hipotecario."""

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np


@dataclass
class RefinanceDecision:
    npv_uf: float
    payback_months: Optional[int]
    monthly_savings_uf: float
    total_lifetime_savings_nominal_uf: float
    recommendation_flag: str  # "RECOMENDADO", "EVALUAR_CON_CAUTELA", "NO_CONVIENE"
    rationale: str


class RefinanceAnalyzer:
    DEFAULT_ANNUAL_DISCOUNT_RATE = 0.025  # 2.5% anual real en UF (costo de oportunidad)

    @classmethod
    def evaluate(
        cls,
        current_schedule: List[Dict[str, Any]],
        new_schedule: List[Dict[str, Any]],
        upfront_costs_uf: float,
        financed_costs: bool = False,
        annual_discount_rate: float = DEFAULT_ANNUAL_DISCOUNT_RATE
    ) -> RefinanceDecision:
        """
        Compara los dos flujos de dividendos y calcula VPN y Payback dinámico.
        """
        n_current = len(current_schedule)
        n_new = len(new_schedule)
        max_months = max(n_current, n_new)

        monthly_discount = (1.0 + annual_discount_rate) ** (1.0 / 12.0) - 1.0

        # Arrays alineados de pagos
        flows_current = np.zeros(max_months)
        flows_new = np.zeros(max_months)

        for i, item in enumerate(current_schedule):
            flows_current[i] = item["total_dividend_uf"]

        for i, item in enumerate(new_schedule):
            flows_new[i] = item["total_dividend_uf"]

        # Delta mensual: lo que ahorro cada mes (positivo si new < current)
        monthly_diff = flows_current - flows_new

        # Factor de descuento
        discount_factors = np.array([(1.0 + monthly_discount) ** (-t) for t in range(1, max_months + 1)])

        if financed_costs:
            # Si el costo se financió, upfront_cost es 0 porque ya está dentro de new_schedule
            npv = float(np.sum(monthly_diff * discount_factors))
            # Para el payback, evaluamos cuándo el ahorro acumulado compensa el costo asumido
            cumulative_disc_savings = np.cumsum(monthly_diff * discount_factors)
            payback_months = None
            for month_idx, cum_save in enumerate(cumulative_disc_savings):
                if cum_save >= upfront_costs_uf:
                    payback_months = month_idx + 1
                    break
        else:
            # Costo pagado al contado en t=0
            npv = float(-upfront_costs_uf + np.sum(monthly_diff * discount_factors))
            cumulative_disc_savings = np.cumsum(monthly_diff * discount_factors)
            payback_months = None
            for month_idx, cum_save in enumerate(cumulative_disc_savings):
                if cum_save >= upfront_costs_uf:
                    payback_months = month_idx + 1
                    break

        nominal_savings = float(np.sum(monthly_diff))
        initial_monthly_saving = float(monthly_diff[0]) if len(monthly_diff) > 0 else 0.0

        # Reglas de decisión heurística/cuantitativa
        if npv > 20.0 and payback_months is not None and payback_months <= 24:
            flag = "RECOMENDADO"
            rationale = (
                f"El refinanciamiento genera un VPN positivo de {npv:.1f} UF. "
                f"La inversión se recupera en {payback_months} meses y ahorras "
                f"{initial_monthly_saving:.2f} UF mensuales desde el primer dividendo."
            )
        elif npv > 0.0 and (payback_months is None or payback_months > 48):
            flag = "EVALUAR_CON_CAUTELA"
            rationale = (
                f"El VPN es positivo ({npv:.1f} UF), pero el tiempo de retorno es elevado "
                f"({payback_months if payback_months else '> ' + str(max_months)} meses). "
                "Si planeas vender o prepagar la propiedad en los próximos 4 años, no es conveniente."
            )
        else:
            flag = "NO_CONVIENE"
            rationale = (
                f"El costo de refinanciamiento destruye valor patrimonial (VPN = {npv:.1f} UF). "
                "Las condiciones actuales del mercado no justifican los gastos de migración."
            )

        return RefinanceDecision(
            npv_uf=round(npv, 2),
            payback_months=payback_months,
            monthly_savings_uf=round(initial_monthly_saving, 2),
            total_lifetime_savings_nominal_uf=round(nominal_savings, 2),
            recommendation_flag=flag,
            rationale=rationale
        )
```

---

### 5.4. `src/parsers/statement_llm.py`
Extracción estructurada con Pydantic y un modelo de lenguaje para leer cartolas hipotecarias en PDF.

```python
"""Extracción estructurada de cartolas hipotecarias bancarias mediante Pydantic y LLM."""

from pydantic import BaseModel, Field
from typing import Optional


class MortgageStatementExtraction(BaseModel):
    bank_name: str = Field(description="Nombre del banco o mutuaria acreedora")
    operation_number: Optional[str] = Field(description="Número de operación o crédito")
    current_balance_uf: float = Field(description="Saldo insoluto de capital en UF")
    annual_interest_rate_pct: float = Field(description="Tasa de interés anual en porcentaje (ej: 4.2 para 4.2%)")
    remaining_installments: int = Field(description="Número de dividendos o cuotas pendientes")
    total_installments: Optional[int] = Field(description="Número total de dividendos pactados originalmente")
    current_total_dividend_uf: float = Field(description="Monto del dividendo mensual total en UF")
    financial_dividend_uf: Optional[float] = Field(description="Monto del dividendo sin seguros en UF")
    life_insurance_uf: Optional[float] = Field(description="Monto cobrado por seguro de desgravamen en UF")
    fire_insurance_uf: Optional[float] = Field(description="Monto cobrado por seguro de incendio y sismo en UF")
    customer_age_years: Optional[int] = Field(description="Edad del titular si figura en el documento")


SYSTEM_PROMPT_EXTRACTION = """
Eres un asistente experto en ingeniería financiera y banca chilena.
Tu tarea es leer el texto extraído de una cartola de dividendo hipotecario o estado de cuenta
y extraer las variables críticas en formato JSON estricto cumpliendo el schema provisto.

Reglas:
1. Normaliza los montos a UF. Si un valor está en pesos ($ CLP), divídelo por el valor de la UF indicado en el documento o déjalo nulo si no es identificable.
2. Identifica si la tasa informada es anual o mensual. Debes entregar siempre la tasa anual en porcentaje (ej. 4.5% anual).
3. Asegúrate de diferenciar el saldo insoluto de capital del monto original del crédito.
"""
```

---

### 5.5. `src/scrapers/bcch_client.py`
Conector a la API oficial de Estadísticas del Banco Central de Chile (`si3.bcentral.cl`).

```python
"""Cliente para consumir series macroeconómicas de la API del Banco Central de Chile."""

import os
import requests
from typing import Dict, Any, Optional


class CentralBankChileClient:
    BASE_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.asmx/SearchSeries"

    # Códigos de serie estándar del BCCh
    SERIES_UF_DAILY = "F073.UFF.PRE.Z.D"          # Unidad de Fomento diaria
    SERIES_MORTGAGE_RATE = "F072.CLP.COL.VIV.Z.M" # Tasa colocación vivienda en UF (mensual)
    SERIES_TPM = "F073.TPM.TCM.G01.Z.D"          # Tasa de Política Monetaria

    def __init__(self, user: Optional[str] = None, password: Optional[str] = None):
        self.user = user or os.getenv("BCCH_API_USER")
        self.password = password or os.getenv("BCCH_API_PASS")

    def fetch_series(self, series_code: str, first_date: str, last_date: str) -> Dict[str, Any]:
        """
        Consulta una serie de tiempo en el Banco Central.
        Formato de fechas: YYYY-MM-DD
        """
        if not self.user or not self.password:
            raise ValueError("Credenciales del Banco Central (BCCH_API_USER, BCCH_API_PASS) no configuradas.")

        params = {
            "user": self.user,
            "pass": self.password,
            "firstdate": first_date,
            "lastdate": last_date,
            "timeseries": series_code
        }

        response = requests.get(self.BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("Codigo") != 0:
            raise RuntimeError(f"Error en API Banco Central: {data.get('Descripcion')}")

        return data.get("Series", {})
```

---

## 6. Plan de Trabajo e Hitos de Ejecución

| Semana / Hito | Estado | Entregable | Objetivos Específicos |
| :---: | :---: | :--- | :--- |
| **Hito 1 (S1)** | ✅ **Completado** | **Core Matemático & Unit Tests** | Implementar `amortizer.py`, `switching_costs.py` y `metrics.py`. Suite de pruebas unitarias con `pytest` validando contra estándares CMF y Ley N° 21.236. |
| **Hito 2 (S2)** | ✅ **Completado** | **Ingesta de Datos & Base DuckDB** | Construir cliente BCCh (`si3.bcentral.cl`), conector CMF, catálogo de entidades (`bank_simulators.py`) y persistencia robusta en `market_store.py` (DuckDB) con soporte de concurrencia. |
| **Hito 3 (S3)** | ✅ **Completado** | **Extracción de Cartolas (Heurística + LLM)** | Extractor dual con `pypdf`, parser heurístico multiformato (Banco de Chile, Estado, Santander, BCI) y fallback a LLMs estructurados con Pydantic. |
| **Hito 4 (S4)** | ✅ **Completado** | **API Backend (FastAPI)** | Endpoints REST `/simulate`, `/evaluate-refinance`, `/extract-statement` y `/market-rates` con validación de esquemas Pydantic y documentación OpenAPI/Swagger. |
| **Hito 5 (S5)** | ✅ **Completado** | **Interfaz de Usuario (Streamlit)** | Dashboard interactivo con 5 pestañas (Comparador, Payback, Simulador a Medida, Falacia del Dividendo, Tabla de Amortización), carga drag & drop y gráficos Plotly. |
| **Hito 6 (S6)** | ✅ **Completado** | **Despliegue, Contenedorización & CI/CD** | `Dockerfile` optimizado multi-servicio, `docker-compose.yml` con volumen DuckDB compartido, `.dockerignore`, workflow en GitHub Actions (`.github/workflows/ci.yml`) y configuración de linting con `ruff`. |
| **Hito 7 (S7)** | ✅ **Completado** | **Informe Ejecutivo y Dictamen en PDF** | Motor ReportLab (`ExecutiveReportGenerator`), gráficos vectoriales nativos de Payback/Break-Even, endpoint `POST /api/v1/reports/pdf` y botones de descarga directa en Streamlit. |
| **Hito 8 (S8)** | ✅ **Completado** | **Módulo Financiero y Normativo Avanzado** | Simulador de abonos extraordinarios (prepagos parciales), modelado de riesgo de tasa mixta vs. fija, reglas de asegurabilidad/desgravamen por edad y sistema de amortización alemán. |
| **Hito 9 (S9)** | ⏳ *Planificado* | **Ingesta en Vivo con Web Scraping Headless** | Scrapers automatizados con `playwright` sobre cotizadores bancarios abiertos de Chile para refrescar periódicamente la base `bank_offers` en DuckDB. |
| **Hito 10 (S10)** | ⏳ *Planificado* | **UX Comercial Avanzada & Persistencia** | Comparador Head-to-Head entre dos entidades, modal de confirmación de extracción documental y persistencia de simulaciones guardadas por usuario. |

---

## 7. Instrucciones para Arrancar el Entorno

### Opción A: Ejecución Local con Entorno Virtual
```bash
# 1. Activar entorno virtual
source .venv/bin/activate

# 2. Iniciar Dashboard Interactivo (Streamlit)
streamlit run src/app/dashboard.py
# Disponible en: http://localhost:8501

# 3. Iniciar API REST Backend (FastAPI) en terminal paralela
uvicorn src.app.api:app --reload --port 8000
# Documentación Swagger en: http://localhost:8000/docs

# 4. Ejecutar pruebas unitarias y linters
pytest tests/ -v
ruff check .
```

### Opción B: Ejecución con Docker y Docker Compose
```bash
# Construir y levantar tanto la API como el Dashboard en segundo plano
docker compose up --build -d

# Ver logs de los servicios
docker compose logs -f

# Detener los contenedores
docker compose down
```

---

## 8. Especificaciones Técnicas Detalladas de Hitos Futuros

### 📑 Hito 7: Generador de Informe Ejecutivo y Dictamen de Portabilidad en PDF
- **Objetivo de Negocio:** Permitir a usuarios particulares y a asesores hipotecarios descargar un documento formal listo para imprimir o presentar ante ejecutivos bancarios como respaldo técnico de negociación.
- **Componentes Arquitectónicos:**
  1. `src/reports/pdf_generator.py`: Motor de maquetación vectorial basado en `reportlab` o `weasyprint` con plantilla corporativa formal chilena.
  2. **Estructura del Informe (2 a 3 páginas):**
     - **Portada y Encabezado:** Identificación del deudor, fecha, valor UF vigente y entidad acreedora actual.
     - **Resumen Ejecutivo y Semáforo:** Dictamen cuantitativo destacado con recuadros de color (RECOMENDADO / EVALUAR CON CAUTELA / NO CONVIENE), VPN total en UF y CLP, y ahorro mensual.
     - **Desglose Jurídico de Costos:** Tabla pormenorizada con comisiones de prepago (Art. 100 LGB), aranceles CBR con 50% de beneficio (Ley 21.236), exención de timbres (D.L. 3475) y gastos notariales.
     - **Gráficos Embebidos:** Renderizado estático de la curva de Payback/Break-Even y de la comparativa de dividendos.
     - **Comparativa de Entidades:** Tabla con las 3 mejores opciones del mercado.
  3. **Integración:**
     - Endpoint API: `GET /api/v1/reports/pdf?balance_uf=...`
     - Botón de descarga en el Dashboard Streamlit en la pestaña de resultados.

### 🇨🇱 Hito 8: Módulo Financiero y Normativo Avanzado
- **Objetivo Cuantitativo:** Extender la granularidad del motor matemático para responder a escenarios sofisticados de la banca chilena:
  1. **Simulador de Abonos Extraordinarios (Prepagos Parciales):**
     - Modelar el impacto de inyectar liquidez al momento del refinanciamiento.
     - Función comparativa de optimización: ¿Conviene más reducir plazo manteniendo cuota o reducir dividendo manteniendo plazo?
  2. **Modelado de Riesgo en Tasa Mixta vs. Fija:**
     - Las opciones con tasa fija a 3 o 5 años suelen ofrecer tasas iniciales menores, pero trasladan el riesgo al cliente al año 4 o 6.
     - Generación de matrices de estrés proyectando trayectorias de TPM (escenario base, alcista +150 bps, bajista -150 bps) para evaluar la probabilidad de que una tasa mixta resulte destructiva de patrimonio frente a una fija pura.
  3. **Curva Actuarial de Desgravamen y Topes de Edad:**
     - Implementar escalamiento de prima de desgravamen por tramos de edad ($\tau(\text{edad})$).
     - Alerta de asegurabilidad: notificación técnica cuando la edad del titular al vencimiento del crédito supere los 75 u 80 años.
  4. **Amortización Alemana (Cuota Decreciente):**
     - Extender `amortizer.py` con `GermanAmortizer` para instituciones que ofrecen cuota fija de capital (como BancoEstado en ciertas líneas).

### 🤖 Hito 9: Ingesta en Vivo con Web Scraping Headless
- **Objetivo de Datos:** Automatizar la actualización de tasas reales directamente desde los cotizadores en línea de los bancos:
  1. `src/scrapers/headless_scrapers.py`: Implementación con `playwright` en modo headless para los simuladores públicos de BancoEstado, Santander y BCI.
  2. Extracción de dividendos brutos, primas de seguros y CAE informada.
  3. Script programable (`scripts/sync_live_market.py`) para ejecución semanal o bajo demanda, actualizando automáticamente la tabla `bank_offers` en DuckDB.

### 🎨 Hito 10: UX Comercial Avanzada y Persistencia de Sesiones
- **Objetivo de Producto:** Optimizar la experiencia de usuario y convertir el dashboard en una herramienta de productividad recurrente:
  1. **Comparador Lado a Lado (Head-to-Head):** Selector de dos bancos específicos para comparar simultáneamente dividendo, CAE, seguros, VPN y tabla cuota a cuota.
  2. **Modal Interactivo de Validación Documental:** Pre-visualización de las variables extraídas de la cartola PDF con posibilidad de ajuste manual antes de recalcular.
  3. **Persistencia de Simulaciones:** Capacidad de guardar escenarios de simulación y compartirlos vía URL parametrizada (`?balance=3200&rate=5.2&months=180`).