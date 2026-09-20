"""Módulos del motor cuantitativo financiero de HipoRefi-CL."""

from src.core.amortizer import FrenchAmortizer, GermanAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator, SwitchingCostBreakdown
from src.core.metrics import RefinanceAnalyzer, RefinanceDecision
from src.core.advanced_financial import (
    PrepaymentSimulator,
    PrepaymentEvaluation,
    PrepaymentOptionResult,
    MixedRateRiskAnalyzer,
    MixedRateStressResponseData,
    StressScenarioResult,
    LifeInsuranceActuary,
    InsurabilityEvaluation,
)

__all__ = [
    "FrenchAmortizer",
    "GermanAmortizer",
    "MortgageParams",
    "SwitchingCostCalculator",
    "SwitchingCostBreakdown",
    "RefinanceAnalyzer",
    "RefinanceDecision",
    "PrepaymentSimulator",
    "PrepaymentEvaluation",
    "PrepaymentOptionResult",
    "MixedRateRiskAnalyzer",
    "MixedRateStressResponseData",
    "StressScenarioResult",
    "LifeInsuranceActuary",
    "InsurabilityEvaluation",
]

