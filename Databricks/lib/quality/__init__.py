"""Framework de Data Quality (expectations + relatório)."""
from .expectations import (
    Expectation,
    ExpectationResult,
    QualityReport,
    run_expectations,
)

__all__ = [
    "Expectation",
    "ExpectationResult",
    "QualityReport",
    "run_expectations",
]
