"""Helpers de estruturação/normalização da camada Silver.

O parse estrutural (`from_json`) acontece na Bronze, contra o contrato versionado
(ver [`contracts`](contracts.py)). Estes helpers atuam na Silver, sobre os campos já
estruturados: separação por contrato de campos obrigatórios (com quarentena), projeção
com renomeação e derivação de datas — evitando repetição entre URA/CALLS/PESQUISA.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

try:  # pragma: no cover - depende do runtime Spark
    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F
except (ImportError, ModuleNotFoundError):  # pragma: no cover
    DataFrame = object  # type: ignore
    F = None  # type: ignore


def validate_contract(
    df: DataFrame,
    required: Sequence[str],
    *,
    source: str,
    schema_version: str = "1.0",
    payload_col: str = "raw_payload",
    partition_col: str = "partition",
    offset_col: str = "offset",
) -> tuple[DataFrame, DataFrame]:
    """Separa os eventos já estruturados da Bronze entre válidos e quarentena.

    O parse ocorreu na Bronze; aqui um evento é inválido quando algum campo
    **obrigatório** está nulo — ausente, incompatível ou vindo de um payload malformado
    (cujo parse na Bronze produziu nulos). O inválido não é descartado: vai para a DLQ
    com o **payload original** (auditável) e o motivo. `valid_df` mantém as colunas
    estruturadas para o `transform`; `quarantine_df` segue o schema da DLQ (`event_id`,
    `payload`, `error_reason`, `schema_version`, `ingestion_ts`, `source`).

    O `event_id` é a **identidade do evento no Event Hub** (`source|partition|offset`),
    não o hash do payload: um retry do mesmo offset gera o mesmo id (MERGE idempotente),
    mas dois eventos distintos com o **mesmo payload inválido** têm offsets diferentes e
    são preservados como duas ocorrências.
    """
    required = list(required)
    valid_cond = F.lit(True)
    for c in required:
        valid_cond = valid_cond & F.col(c).isNotNull()

    valid_df = df.filter(valid_cond)

    missing = F.array_compact(
        F.array(*[F.when(F.col(c).isNull(), F.lit(c)) for c in required])
    )
    event_id = F.sha2(
        F.concat_ws("|", F.lit(source), F.col(partition_col).cast("string"), F.col(offset_col).cast("string")),
        256,
    )
    quarantine_df = df.filter(~valid_cond).select(
        event_id.alias("event_id"),
        F.col(payload_col).cast("string").alias("payload"),
        F.concat(F.lit("missing_or_invalid: "), F.concat_ws(", ", missing)).alias("error_reason"),
        F.lit(schema_version).alias("schema_version"),
        F.current_timestamp().alias("ingestion_ts"),
        F.lit(source).alias("source"),
    )
    return valid_df, quarantine_df


def rename_columns(df: DataFrame, mapping: Mapping[str, str]) -> DataFrame:
    """Projeta só as colunas de negócio de `mapping` (origem→destino), renomeando.

    Descarta as colunas de infraestrutura que a Bronze carrega (payload original,
    offset, timestamps de ingestão), que não pertencem à Silver."""
    return df.select(*[F.col(src).alias(dst) for src, dst in mapping.items()])


def add_load_audit(df: DataFrame) -> DataFrame:
    """Adiciona a coluna de auditoria de carga (`DH_REFE_CRGA`)."""
    return df.withColumn("DH_REFE_CRGA", F.current_timestamp())


def add_period_and_dates(df: DataFrame, ts_col: str, prefix_start: str = "DT_INIC") -> DataFrame:
    """Deriva `CD_PERI` (yyyyMM) e a data do evento a partir de uma coluna timestamp."""
    return (
        df.withColumn("CD_PERI", F.date_format(F.col(ts_col), "yyyyMM").cast("int"))
        .withColumn(prefix_start, F.to_date(ts_col))
    )
