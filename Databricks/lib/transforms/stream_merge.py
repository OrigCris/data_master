"""Upsert incremental Bronze→Silver: stream Delta + foreachBatch + MERGE idempotente.

A Bronze é append-only, então o stream Delta entrega só as linhas novas
(`skipChangeCommits` ignora reescritas de OPTIMIZE). Com `AvailableNow` + `foreachBatch` a escrita é
at-least-once — a não-duplicidade vem do MERGE por chave de negócio, não do checkpoint
(que só controla o progresso). Ver ADR-0002 e o runbook `streaming-checkpoint-reset`.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .parse import validate_contract

# pyspark é resolvido no runtime do cluster; o import é protegido para permitir testar
# as funções puras (build_merge_on, assert_fqn) sem Spark.
try:  # pragma: no cover - depende do runtime Spark
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
except Exception:  # pragma: no cover
    DataFrame = object  # type: ignore
    SparkSession = object  # type: ignore
    F = None  # type: ignore


def build_merge_on(keys: Sequence[str], target_alias: str = "S", source_alias: str = "C") -> str:
    """Monta a cláusula ON do MERGE a partir das chaves de negócio (função pura).

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
    """Cria a tabela vazia com o schema do staged_df, se ainda não existir."""
    assert_fqn(fqn)
    if not spark.catalog.tableExists(fqn):
        empty = spark.createDataFrame([], staged_df.schema)
        empty.write.format("delta").mode("overwrite").saveAsTable(fqn)
        if cluster_by:
            cols = ", ".join(cluster_by)
            spark.sql(f"ALTER TABLE {fqn} CLUSTER BY ({cols})")


def merge_upsert(
    spark: SparkSession,
    target_table_fqn: str,
    staged_df: DataFrame,
    keys: Sequence[str],
    cluster_by: Sequence[str] | None = None,
) -> None:
    """Aplica MERGE (upsert) idempotente do staged_df na tabela alvo."""
    ensure_table(spark, target_table_fqn, staged_df, cluster_by=cluster_by)
    view = "_stg_" + target_table_fqn.replace(".", "_")
    staged_df.createOrReplaceTempView(view)
    # Identificadores internos e validados (assert_fqn; chaves e view construídos em
    # código) — sem input de usuário, logo sem vetor de injeção.
    merge_sql = f"MERGE INTO {target_table_fqn} AS S USING {view} AS C ON {build_merge_on(keys)} WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *"  # nosec B608
    spark.sql(merge_sql)


@dataclass
class SilverStream:
    """Consome a Bronze (append-only) como stream Delta e faz upsert idempotente na Silver.

    O primeiro run processa o snapshot existente (backfill); depois o checkpoint
    assume o controle do progresso.
    """

    spark: SparkSession

    def read_stream(self, source_table_fqn: str) -> DataFrame:
        return (
            self.spark.readStream.format("delta")
            # ignora commits de manutenção (OPTIMIZE/compaction): a Bronze só cresce
            # por append, não há update/delete de negócio a considerar.
            .option("skipChangeCommits", "true")
            .table(source_table_fqn)
        )

    def _recompute_with_history(
        self,
        session: SparkSession,
        staged_df: DataFrame,
        target_table_fqn: str,
        keys: Sequence[str],
        recompute: Callable[[DataFrame], DataFrame],
        recompute_keys: Sequence[str],
    ) -> DataFrame:
        """Reprocessa cada grupo (`recompute_keys`) por inteiro, unindo o batch ao
        histórico já na Silver para as chaves tocadas.

        Traz do alvo apenas os registros das mesmas chaves (leitura limitada), descarta
        as colunas derivadas (serão recalculadas), sobrepõe pelas linhas novas e chama
        `recompute` sobre o conjunto completo. Como o alvo é a fonte da verdade, um
        evento atrasado é reconciliado sem *watermark* e sem perda. Usa `session` (a do
        micro-batch) para que o join ocorra na mesma sessão do batch.
        """
        recompute_keys = list(recompute_keys)
        keys = list(keys)
        if not session.catalog.tableExists(target_table_fqn):
            return recompute(staged_df)

        batch_keys = staged_df.select(*recompute_keys).distinct()
        existing = session.table(target_table_fqn).join(batch_keys, recompute_keys, "left_semi")
        derived = [c for c in existing.columns if c not in staged_df.columns]
        existing_base = existing.drop(*derived) if derived else existing
        # linhas novas ganham das antigas de mesma chave; as demais do histórico entram
        combined = existing_base.join(staged_df, keys, "left_anti").unionByName(
            staged_df, allowMissingColumns=True
        )
        return recompute(combined)

    def run(
        self,
        source_table_fqn: str,
        target_table_fqn: str,
        transform: Callable[[DataFrame], DataFrame],
        keys: Sequence[str],
        checkpoint_location: str,
        cluster_by: Sequence[str] | None = None,
        expectations: list | None = None,
        dq_results_table: str | None = None,
        contract_schema=None,
        contract_required: Sequence[str] | None = None,
        quarantine_table: str | None = None,
        schema_version: str = "1.0",
        recompute: Callable[[DataFrame], DataFrame] | None = None,
        recompute_keys: Sequence[str] | None = None,
    ):
        """Roda o stream (AvailableNow) e bloqueia até terminar.

        Por micro-batch: (1) **data contract** — inválidos vão para `quarantine_table`,
        só os válidos seguem; (2) **recompute** por chave, se informado (junta ao
        histórico e reprocessa o grupo inteiro — corrige derivações entre batches);
        (3) **gate de DQ**, se informado (falha crítica interrompe); (4) **MERGE**
        idempotente por chave.
        """

        def _batch(micro_df: DataFrame, batch_id: int) -> None:
            if micro_df.isEmpty():
                return
            # foreachBatch entrega o micro-batch numa sessão CLONADA; usá-la em tudo
            # (leitura do alvo, temp view, MERGE) evita "view não encontrada" e joins
            # entre sessões distintas.
            session = micro_df.sparkSession
            events = micro_df
            if contract_schema is not None:
                events, quarantined = validate_contract(
                    events,
                    contract_schema,
                    contract_required or [],
                    source=source_table_fqn,
                    schema_version=schema_version,
                )
                if quarantine_table:
                    quarantined.write.format("delta").mode("append").saveAsTable(quarantine_table)
                if events.isEmpty():
                    return
            staged_df = transform(events)
            if recompute is not None and recompute_keys:
                staged_df = self._recompute_with_history(session, staged_df, target_table_fqn, keys, recompute, recompute_keys)
            if expectations:
                from quality import run_expectations  # lazy: evita acoplar o import do módulo
                report = run_expectations(staged_df, expectations, target_table_fqn)
                print(report.summary())
                if dq_results_table:
                    report.to_table(session, dq_results_table)
                report.raise_if_critical_failed()
            merge_upsert(session, target_table_fqn, staged_df, keys, cluster_by=cluster_by)

        query = (
            self.read_stream(source_table_fqn)
            .writeStream
            .foreachBatch(_batch)
            .option("checkpointLocation", checkpoint_location)
            .trigger(availableNow=True)
            .start()
        )
        query.awaitTermination()
        return query
