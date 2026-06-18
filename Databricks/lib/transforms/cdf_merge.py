"""Upsert incremental Bronze→Silver via Structured Streaming + MERGE.

Padrão:

* lê o **Change Data Feed** da Bronze como uma **fonte de streaming**;
* usa **`Trigger.AvailableNow`** — processa todo o backlog disponível em
  micro-batches e encerra;
* aplica **`foreachBatch`** com **MERGE** idempotente por chave de negócio;
* o **checkpoint** do próprio stream controla o progresso (offset/versão),
  garantindo *exactly-once* e backpressure — reprocessar = resetar o checkpoint
  (ver runbook `streaming-checkpoint-reset`).

Uso típico (dentro de um notebook, com `spark` disponível):

    from transforms import SilverStream

    stream = SilverStream(spark)
    stream.run(
        source_fqn="prd.b_dm_callcenter.ura_once",
        target_fqn="prd.s_dm_callcenter.tabe_ura_anlt",
        transform=transform,                       # callable: micro_df -> staged_df
        keys=["ID_CHAM"],
        checkpoint_location="/Volumes/.../checkpoints/silver/tabe_ura_anlt",
        cluster_by=["CD_PERI", "DT_INIC", "ID_CHAM"],
    )
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

# pyspark é resolvido em runtime no cluster Databricks; o import é protegido para
# permitir importar as funções puras (build_merge_on, assert_fqn) em testes.
try:  # pragma: no cover - depende do runtime Spark
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
except Exception:  # pragma: no cover
    DataFrame = object  # type: ignore
    SparkSession = object  # type: ignore
    F = None  # type: ignore


def build_merge_on(keys: Sequence[str], target_alias: str = "S", source_alias: str = "C") -> str:
    """Monta a cláusula ON do MERGE a partir das chaves de negócio.

    Função pura (sem Spark) para ser exercitada em testes unitários.

    >>> build_merge_on(["ID_CHAM", "ID_ATEN"])
    'S.ID_CHAM = C.ID_CHAM AND S.ID_ATEN = C.ID_ATEN'
    """
    if not keys:
        raise ValueError("É necessário ao menos uma chave de negócio para o MERGE.")
    return " AND ".join(f"{target_alias}.{k} = {source_alias}.{k}" for k in keys)


def assert_fqn(fqn: str) -> tuple[str, str, str]:
    """Valida e quebra um FQN `catalog.schema.table`."""
    parts = fqn.split(".")
    if len(parts) != 3 or not all(parts):
        raise ValueError(f"FQN inválido: {fqn!r}. Use catalog.schema.table")
    return parts[0], parts[1], parts[2]


def ensure_table(spark: SparkSession, fqn: str, staged_df: DataFrame, cluster_by: Sequence[str] | None = None) -> None:
    """Cria a tabela vazia com o schema do staged, se ainda não existir."""
    assert_fqn(fqn)
    if not spark.catalog.tableExists(fqn):
        empty = spark.createDataFrame([], staged_df.schema)
        empty.write.format("delta").mode("overwrite").saveAsTable(fqn)
        if cluster_by:
            cols = ", ".join(cluster_by)
            spark.sql(f"ALTER TABLE {fqn} CLUSTER BY ({cols})")


def merge_upsert(
    spark: SparkSession,
    target_fqn: str,
    staged_df: DataFrame,
    keys: Sequence[str],
    cluster_by: Sequence[str] | None = None,
) -> None:
    """Aplica MERGE (upsert) idempotente do staged na tabela alvo."""
    ensure_table(spark, target_fqn, staged_df, cluster_by=cluster_by)
    view = "_stg_" + target_fqn.replace(".", "_")
    staged_df.createOrReplaceTempView(view)
    spark.sql(
        f"""
        MERGE INTO {target_fqn} AS S
        USING {view} AS C
        ON {build_merge_on(keys)}
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
        """
    )


@dataclass
class SilverStream:
    """Consome o CDF da Bronze como stream e faz upsert idempotente na Silver.

    `change_types` filtra os tipos de mudança do CDF (Bronze é append-only, então
    o default é apenas `insert`). `starting_version=0` garante que o **primeiro**
    run faça backfill de todo o histórico; depois o checkpoint assume o controle.
    """

    spark: SparkSession
    change_types: Sequence[str] = ("insert",)
    starting_version: int = 0

    def read_cdf_stream(self, source_fqn: str) -> DataFrame:
        return (
            self.spark.readStream.format("delta")
            .option("readChangeFeed", "true")
            .option("startingVersion", self.starting_version)
            .table(source_fqn)
        )

    def run(
        self,
        source_fqn: str,
        target_fqn: str,
        transform: Callable[[DataFrame], DataFrame],
        keys: Sequence[str],
        checkpoint_location: str,
        cluster_by: Sequence[str] | None = None,
        expectations: list | None = None,
        dq_results_table: str | None = None,
    ):
        """Executa o stream com Trigger.AvailableNow e bloqueia até terminar.

        Se `expectations` for informado, cada micro-batch passa por um **gate de
        Data Quality** antes do MERGE: o relatório é (opcionalmente) persistido em
        `dq_results_table` e uma falha **crítica** interrompe o batch.
        """

        def _batch(micro_df: DataFrame, batch_id: int) -> None:
            changes = micro_df.filter(F.col("_change_type").isin(list(self.change_types)))
            if changes.isEmpty():
                return
            staged = transform(changes)
            if expectations:
                from quality import run_expectations  # lazy: evita acoplar o import do módulo
                report = run_expectations(staged, expectations, dataset=target_fqn)
                print(report.summary())
                if dq_results_table:
                    report.to_table(self.spark, dq_results_table)
                report.raise_if_critical_failed()
            merge_upsert(self.spark, target_fqn, staged, keys, cluster_by=cluster_by)

        query = (
            self.read_cdf_stream(source_fqn)
            .writeStream
            .foreachBatch(_batch)
            .option("checkpointLocation", checkpoint_location)
            .trigger(availableNow=True)
            .start()
        )
        query.awaitTermination()
        return query
