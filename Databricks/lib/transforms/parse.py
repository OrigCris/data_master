"""Helpers de parsing/normalização reutilizados pelos notebooks Silver.

A camada Silver recebe da Bronze um JSON cru na coluna `body`. Estes helpers
padronizam o parse (`from_json`), a renomeação para o padrão de nomenclatura do
projeto e a derivação de colunas de data — evitando código repetido entre URA,
CALLS e PESQUISA.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

try:  # pragma: no cover - depende do runtime Spark
    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql import types as T
except Exception:  # pragma: no cover
    DataFrame = object  # type: ignore
    F = None  # type: ignore
    T = None  # type: ignore


# Schema padrão da quarentena (DLQ): payload cru + contexto do erro para triagem.
QUARANTINE_COLUMNS = (
    "event_id",
    "payload",
    "error_reason",
    "schema_version",
    "ingestion_ts",
    "source",
)


def validate_contract(
    df: DataFrame,
    schema: T.StructType,
    required: Sequence[str],
    *,
    source: str,
    schema_version: str = "1.0",
    body_col: str = "body",
) -> tuple[DataFrame, DataFrame]:
    """Aplica o *data contract* e separa eventos válidos de inválidos.

    Um evento é **inválido** quando o JSON é malformado (o `from_json` devolve
    `null`) ou quando algum campo **obrigatório** vem nulo (ausente ou com tipo
    incompatível). Em vez de descartá-lo silenciosamente, ele é roteado para a
    **quarentena** (DLQ) com o payload cru e o motivo — dado ruim não some e nem
    contamina a camada confiável.

    Retorna `(valid_df, quarantine_df)`:
    - `valid_df` preserva as colunas originais (o `transform` segue o fluxo normal);
    - `quarantine_df` segue o schema de [`QUARANTINE_COLUMNS`](#).
    """
    required = list(required or [])
    parsed = df.withColumn("_parsed", F.from_json(F.col(body_col), schema))

    struct_null = F.col("_parsed").isNull()
    valid_cond = ~struct_null
    for c in required:
        valid_cond = valid_cond & F.col(f"_parsed.{c}").isNotNull()

    valid_df = parsed.filter(valid_cond).drop("_parsed")

    if required:
        missing = F.array_compact(
            F.array(*[F.when(F.col(f"_parsed.{c}").isNull(), F.lit(c)) for c in required])
        )
        reason = F.when(struct_null, F.lit("malformed_json")).otherwise(
            F.concat(F.lit("missing_or_invalid: "), F.concat_ws(", ", missing))
        )
    else:
        reason = F.lit("malformed_json")

    quarantine_df = parsed.filter(~valid_cond).select(
        F.sha2(F.col(body_col).cast("string"), 256).alias("event_id"),
        F.col(body_col).cast("string").alias("payload"),
        reason.alias("error_reason"),
        F.lit(schema_version).alias("schema_version"),
        F.current_timestamp().alias("ingestion_ts"),
        F.lit(source).alias("source"),
    )
    return valid_df, quarantine_df


def parse_body(df: DataFrame, schema: T.StructType) -> DataFrame:
    """Faz `from_json` da coluna `body` e projeta os campos do evento.

    Linhas com JSON incompatível viram `null` no `from_json` e são descartadas aqui;
    a separação explícita entre válido e inválido (quarentena) fica em
    [`validate_contract`](#), aplicada antes pelo `SilverStream`."""
    return (
        df.withColumn("body", F.from_json(F.col("body"), schema))
        .filter(F.col("body").isNotNull())
        .select("body.*")
    )


def rename_columns(df: DataFrame, mapping: Mapping[str, str]) -> DataFrame:
    """Renomeia colunas conforme o dicionário, preservando as não mapeadas."""
    return df.select([F.col(c).alias(mapping.get(c, c)) for c in df.columns])


def add_load_audit(df: DataFrame) -> DataFrame:
    """Adiciona a coluna de auditoria de carga (`DH_REFE_CRGA`)."""
    return df.withColumn("DH_REFE_CRGA", F.current_timestamp())


def add_period_and_dates(df: DataFrame, ts_col: str, prefix_start: str = "DT_INIC") -> DataFrame:
    """Deriva `CD_PERI` (yyyyMM) e a data do evento a partir de uma coluna timestamp."""
    return (
        df.withColumn("CD_PERI", F.date_format(F.col(ts_col), "yyyyMM").cast("int"))
        .withColumn(prefix_start, F.to_date(ts_col))
    )
