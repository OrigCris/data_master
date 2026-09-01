"""Observabilidade de dados (métricas de dataset, não de linha).

As *expectations* de [`expectations`](expectations.py) olham a linha (not_null, between,
unique). Aqui as checagens olham o **comportamento do dataset ao longo do tempo**:
volume contra a média histórica e *freshness* (quão recente é o dado). São sinais que
nenhuma regra de linha captura — um dia com 40 mil eventos onde normalmente entram 10
milhões não viola `not_null` nem `between`, mas é claramente uma anomalia.

O histórico de métricas fica em uma tabela Delta (`__dataset_metrics`); cada execução
registra o volume e o freshness observados e os compara com a janela anterior.

A lógica de decisão (anomalia de volume, corte de freshness, média móvel) é **pura** e
testada no CI sem Spark; só a coleta das métricas depende do runtime.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

try:  # pragma: no cover - runtime Spark
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
except Exception:  # pragma: no cover
    SparkSession = object  # type: ignore
    F = None  # type: ignore


# --------------------------- lógica pura (testável) --------------------------- #
def rolling_average(values: Sequence[float]) -> float:
    """Média dos valores históricos; 0.0 quando não há histórico."""
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def volume_anomaly(
    current: int,
    baseline_avg: float,
    *,
    lo: float = 0.7,
    hi: float = 1.3,
) -> tuple[bool, str]:
    """Decide se o volume atual destoa da média histórica.

    Fora da faixa `[lo, hi] * baseline_avg` é anomalia. Sem histórico
    (`baseline_avg <= 0`) não há base de comparação — não é anomalia.

    Retorna `(is_anomaly, detalhe)`.
    """
    if baseline_avg <= 0:
        return False, f"sem histórico (volume={current})"
    ratio = current / baseline_avg
    lower, upper = lo * baseline_avg, hi * baseline_avg
    if current < lower or current > upper:
        return True, f"volume={current} fora de [{lower:.0f}, {upper:.0f}] (média={baseline_avg:.0f}, ratio={ratio:.2f})"
    return False, f"volume={current} dentro de [{lower:.0f}, {upper:.0f}] (ratio={ratio:.2f})"


def freshness_exceeded(freshness_minutes: float | None, max_minutes: float | None) -> bool:
    """`True` quando o dado está mais velho que o limite (ou não há dado algum)."""
    if max_minutes is None:
        return False
    if freshness_minutes is None:
        return True
    return freshness_minutes > max_minutes


# ------------------------------- relatório ----------------------------------- #
@dataclass
class ObservationResult:
    metric: str
    value: float | None
    severity: str  # "critical" | "warn"
    ok: bool
    detail: str


@dataclass
class ObservabilityReport:
    dataset: str
    observed_date: date
    results: list[ObservationResult] = field(default_factory=list)
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def passed(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def critical_failures(self) -> list[ObservationResult]:
        return [r for r in self.results if not r.ok and r.severity == "critical"]

    def raise_if_critical_failed(self) -> None:
        if self.critical_failures:
            detail = "; ".join(f"{r.metric}: {r.detail}" for r in self.critical_failures)
            raise AssertionError(f"[OBS] Anomalias críticas em {self.dataset}: {detail}")

    def summary(self) -> str:
        lines = [f"Observabilidade — {self.dataset} ({self.observed_date.isoformat()})"]
        for r in self.results:
            status = "OK" if r.ok else "ALERTA"
            lines.append(f"  [{r.severity:<8}] {r.metric:<16} {status:<6} {r.detail}")
        return "\n".join(lines)


# ------------------------------ parte Spark ---------------------------------- #
def _read_history(spark: SparkSession, metrics_table: str, target_table_fqn: str, metric: str, before: date, window: int) -> list[float]:
    """Lê os valores da métrica nas últimas `window` **datas** anteriores a `before`.

    Consolida uma linha por `observed_date` (o valor da execução mais recente daquela
    data, via `max_by(..., observed_at)`), para que reexecuções do mesmo dia não
    ocupem múltiplos pontos do baseline — assim a "média de 7 dias" é de fato 7 datas.
    """
    if not spark.catalog.tableExists(metrics_table):
        return []
    hist = (
        spark.table(metrics_table)
        .filter((F.col("dataset") == target_table_fqn) & (F.col("metric") == metric))
        .filter(F.col("observed_date") < F.lit(before))
        .groupBy("observed_date")
        .agg(F.expr("max_by(metric_value, observed_at)").alias("metric_value"))
        .orderBy(F.col("observed_date").desc())
        .limit(window)
    )
    return [row["metric_value"] for row in hist.collect()]


def run_observability(
    spark: SparkSession,
    target_table_fqn: str,
    metrics_table: str,
    *,
    date_col: str,
    timestamp_col: str | None = None,
    window: int = 7,
    volume_bounds: tuple[float, float] = (0.7, 1.3),
    max_freshness_minutes: float | None = None,
    freshness_severity: str = "warn",
    volume_severity: str = "warn",
) -> ObservabilityReport:
    """Perfila a tabela, compara com o histórico e registra as métricas.

    - **Volume**: conta as linhas da data mais recente presente (`date_col`) e a
      confronta com a média das últimas `window` datas registradas no histórico.
    - **Freshness** (opcional): minutos desde o `timestamp_col` mais recente.

    O resultado é persistido em `metrics_table` (append) para alimentar as próximas
    comparações. A severidade das checagens é `warn` por padrão — observabilidade
    sinaliza, não interrompe o pipeline — mas pode ser elevada a `critical`.
    """
    lo, hi = volume_bounds
    tbl = spark.table(target_table_fqn)

    observed = tbl.agg(F.max(date_col).alias("d")).collect()[0]["d"]
    observed_date = observed if observed is not None else date.today()
    current_volume = tbl.filter(F.col(date_col) == F.lit(observed_date)).count()

    baseline = rolling_average(_read_history(spark, metrics_table, target_table_fqn, "row_count", observed_date, window))
    is_anom, vol_detail = volume_anomaly(current_volume, baseline, lo=lo, hi=hi)

    results = [
        ObservationResult("row_count", float(current_volume), volume_severity, not is_anom, vol_detail),
    ]

    freshness_minutes: float | None = None
    if timestamp_col:
        seconds = (
            tbl.agg((F.unix_timestamp(F.current_timestamp()) - F.unix_timestamp(F.max(timestamp_col))).alias("s"))
            .collect()[0]["s"]
        )
        freshness_minutes = seconds / 60 if seconds is not None else None
        stale = freshness_exceeded(freshness_minutes, max_freshness_minutes)
        if freshness_minutes is None:
            detail = "sem dado para medir freshness"
        else:
            limite = f" (limite={max_freshness_minutes:.0f}min)" if max_freshness_minutes is not None else ""
            detail = f"freshness={freshness_minutes:.0f}min{limite}"
        results.append(ObservationResult("freshness_minutes", freshness_minutes, freshness_severity, not stale, detail))

    report = ObservabilityReport(dataset=target_table_fqn, observed_date=observed_date, results=results)
    _persist_metrics(spark, metrics_table, report)
    return report


def _persist_metrics(spark: SparkSession, metrics_table: str, report: ObservabilityReport) -> None:
    """Grava as métricas observadas no histórico (append)."""
    rows = [
        (report.dataset, r.metric, float(r.value), report.observed_date, report.observed_at)
        for r in report.results
        if r.value is not None
    ]
    if not rows:
        return
    cols = ["dataset", "metric", "metric_value", "observed_date", "observed_at"]
    spark.createDataFrame(rows, cols).write.format("delta").mode("append").saveAsTable(metrics_table)
