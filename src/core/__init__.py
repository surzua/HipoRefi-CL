"""Módulos del motor cuantitativo financiero de HipoRefi-CL."""

from src.core.amortizer import FrenchAmortizer, MortgageParams
from src.core.switching_costs import SwitchingCostCalculator, SwitchingCostBreakdown
from src.core.metrics import RefinanceAnalyzer, RefinanceDecision

__all__ = [
    "FrenchAmortizer",
    "MortgageParams",
    "SwitchingCostCalculator",
    "SwitchingCostBreakdown",
    "RefinanceAnalyzer",
    "RefinanceDecision",
]
