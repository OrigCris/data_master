"""Framework leve de Data Quality para os pipelines do call center.

Em vez de depender de uma dependência pesada, este módulo oferece um conjunto de
*expectations* declarativas que rodam sobre um DataFrame Spark e produzem um
relatório consolidado. Cada checagem retorna a contagem de linhas que **violam**
a regra; o resultado pode ser persistido em uma tabela de quarentena/auditoria e
usado para falhar o job (gate de qualidade) quando uma regra crítica é quebrada.

Exemplo:

    from quality.expectations import Expectation, run_expectations

    checks = [
        Expectation.not_null("ID_CHAM"),
        Expectation.unique("ID_CHAM"),
        Expectation.between("VL_NOTA", 1, 10),
        Expectation.accepted_values("IN_AUTN", [True, False]),
    ]
    report = run_expectations(df, checks, "prd.s_dm_callcenter.tabe_ura_anlt")
    report.raise_if_critical_failed()
    report.to_table(spark, "prd.s_dm_callcenter.__dq_results")
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

try:  # pragma: no cover - runtime Spark
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
except Exception:  # pragma: no cover
    DataFrame = object  # type: ignore
    SparkSession = object  # type: ignore
    F = None  # type: ignore


@dataclass
class Expectation:
    """Uma regra de qualidade. `predicate` recebe o DataFrame e devolve a
    contagem de linhas que **violam** a regra."""

    name: str
    column: str
    severity: str  # "critical" | "warn"
    predicate: Callable[[DataFrame], int]

    # -------- construtores de regras comuns -------- #
    @staticmethod
    def not_null(column: str, severity: str = "critical") -> Expectation:
        return Expectation(
            name=f"not_null[{column}]",
            column=column,
            severity=severity,
            predicate=lambda df: df.filter(F.col(column).isNull()).count(),
        )

    @staticmethod
    def unique(column: str, severity: str = "critical") -> Expectation:
        def _dups(df: DataFrame) -> int:
            grouped = df.groupBy(column).count().filter(F.col("count") > 1)
            return grouped.count()

        return Expectation(name=f"unique[{column}]", column=column, severity=severity, predicate=_dups)

    @staticmethod
    def between(column: str, lo: Any, hi: Any, severity: str = "critical") -> Expectation:
        return Expectation(
            name=f"between[{column},{lo},{hi}]",
            column=column,
            severity=severity,
            predicate=lambda df: df.filter(
                F.col(column).isNotNull() & (~F.col(column).between(lo, hi))
            ).count(),
        )

    @staticmethod
    def accepted_values(column: str, values: Sequence[Any], severity: str = "warn") -> Expectation:
        return Expectation(
            name=f"accepted_values[{column}]",
            column=column,
            severity=severity,
            predicate=lambda df: df.filter(
                F.col(column).isNotNull() & (~F.col(column).isin(list(values)))
            ).count(),
        )

    @staticmethod
    def non_negative(column: str, severity: str = "critical") -> Expectation:
        return Expectation(
            name=f"non_negative[{column}]",
            column=column,
            severity=severity,
            predicate=lambda df: df.filter(F.col(column) < 0).count(),
        )


@dataclass
class ExpectationResult:
    name: str
    column: str
    severity: str
    failed_rows: int

    @property
    def passed(self) -> bool:
        return self.failed_rows == 0


@dataclass
class QualityReport:
    dataset: str
    results: list[ExpectationResult] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def critical_failures(self) -> list[ExpectationResult]:
        return [r for r in self.results if not r.passed and r.severity == "critical"]

    def raise_if_critical_failed(self) -> None:
        if self.critical_failures:
            detail = ", ".join(f"{r.name}={r.failed_rows}" for r in self.critical_failures)
            raise AssertionError(f"[DQ] Falhas críticas em {self.dataset}: {detail}")

    def summary(self) -> str:
        lines = [f"Data Quality — {self.dataset} ({self.checked_at.isoformat()})"]
        for r in self.results:
            status = "PASS" if r.passed else f"FAIL({r.failed_rows})"
            lines.append(f"  [{r.severity:<8}] {r.name:<32} {status}")
        return "\n".join(lines)

    def to_table(self, spark: SparkSession, table_fqn: str) -> None:
        rows = [
            (self.dataset, r.name, r.column, r.severity, r.failed_rows, r.passed, self.checked_at)
            for r in self.results
        ]
        cols = ["dataset", "expectation", "column", "severity", "failed_rows", "passed", "checked_at"]
        df = spark.createDataFrame(rows, cols)
        df.write.format("delta").mode("append").saveAsTable(table_fqn)


def run_expectations(df: DataFrame, checks: Sequence[Expectation], target_table_fqn: str) -> QualityReport:
    """Executa todas as expectations e devolve o relatório consolidado.

    `target_table_fqn` identifica o dataset checado (vira a coluna `dataset` no
    histórico). Faz `cache()` no DataFrame para não reprocessar a cada checagem.
    """
    df.cache()
    try:
        results = [
            ExpectationResult(c.name, c.column, c.severity, int(c.predicate(df)))
            for c in checks
        ]
    finally:
        df.unpersist()
    return QualityReport(dataset=target_table_fqn, results=results)
