"""Helpers de parsing/normalização reutilizados pelos notebooks Silver.

A camada Silver recebe da Bronze um JSON cru na coluna `body`. Estes helpers
padronizam o parse (`from_json`), a renomeação para o padrão de nomenclatura do
projeto e a derivação de colunas de data — evitando código repetido entre URA,
CALLS e PESQUISA.
"""
from __future__ import annotations

from collections.abc import Mapping

try:  # pragma: no cover - depende do runtime Spark
    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql import types as T
except Exception:  # pragma: no cover
    DataFrame = object  # type: ignore
    F = None  # type: ignore
    T = None  # type: ignore


def parse_body(df: DataFrame, schema: T.StructType, keep_cdf_meta: bool = True) -> DataFrame:
    """Faz `from_json` da coluna `body`, descarta linhas inválidas e, opcionalmente,
    preserva os metadados de CDF (`_commit_version`/`_commit_timestamp`)."""
    parsed = (
        df.withColumn("body", F.from_json(F.col("body"), schema))
        .filter(F.col("body").isNotNull())
    )
    if keep_cdf_meta and "_commit_version" in df.columns:
        parsed = (
            parsed.withColumn("_cv", F.col("_commit_version").cast("long"))
            .withColumn("_ct", F.col("_commit_timestamp").cast("timestamp"))
            .select("body.*", "_cv", "_ct")
        )
    else:
        parsed = parsed.select("body.*")
    return parsed


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
