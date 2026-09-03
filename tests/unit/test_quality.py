"""Testes da lógica pura do framework de Data Quality (sem Spark).

Construir uma `Expectation` não executa o predicado (que depende de Spark), então
metadados e a lógica do relatório/gate são testáveis no CI.
"""
import pytest
from quality import Expectation
from quality.expectations import ExpectationResult, QualityReport


def test_not_null_metadata():
    e = Expectation.not_null("ID_CHAM")
    assert e.name == "not_null[ID_CHAM]"
    assert e.column == "ID_CHAM"
    assert e.severity == "critical"


def test_between_metadata():
    e = Expectation.between("VL_NOTA", 0, 10)
    assert e.name == "between[VL_NOTA,0,10]"
    assert e.severity == "critical"


def test_accepted_values_is_warn_by_default():
    assert Expectation.accepted_values("IN_AUTN", [True, False]).severity == "warn"


def test_severity_override():
    assert Expectation.unique("ID_PESQ", severity="warn").severity == "warn"


def test_report_passed_when_no_failures():
    rep = QualityReport("ds", [ExpectationResult("a", "x", "critical", 0)])
    assert rep.passed
    assert rep.critical_failures == []


def test_report_detects_critical_failure_and_raises():
    rep = QualityReport(
        "ds",
        [
            ExpectationResult("ok", "x", "critical", 0),
            ExpectationResult("bad", "y", "critical", 3),
        ],
    )
    assert not rep.passed
    assert len(rep.critical_failures) == 1
    with pytest.raises(AssertionError):
        rep.raise_if_critical_failed()


def test_warn_failure_does_not_raise():
    rep = QualityReport("ds", [ExpectationResult("w", "z", "warn", 5)])
    assert not rep.passed
    assert rep.critical_failures == []
    rep.raise_if_critical_failed()  # não levanta
