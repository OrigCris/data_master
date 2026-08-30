"""Upsert incremental Bronze→Silver via Structured Streaming + MERGE.

Padrão:

* lê a Bronze como **fonte de streaming Delta** (`readStream.format("delta")`). A
  Bronze é **append-only**, então o próprio stream já entrega apenas as linhas novas
  — não é preciso Change Data Feed (que serve para capturar update/delete, ausentes
  aqui). `skipChangeCommits` ignora reescritas de manutenção (ex.: `OPTIMIZE`);
* usa **`Trigger.AvailableNow`** — processa todo o backlog disponível em
  micro-batches e encerra;
* aplica **`foreachBatch`** com **MERGE** idempotente por chave de negócio;
* o **checkpoint** do próprio stream controla o progresso (offset/versão) e dá
  backpressure. Como `foreachBatch` tem semântica **at-least-once**, a
  não-duplicidade não é assumida pelo checkpoint: ela vem do **MERGE por chave**,
  que absorve a reexecução de um micro-batch. Reprocessar do zero = resetar o
  checkpoint (ver runbook `streaming-checkpoint-reset`).

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
from .parse import validate_contract

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
    # Identificadores internos e validados (assert_fqn; chaves e view construídos em
    # código) — não há input de usuário nesta query, logo não há vetor de injeção.
    merge_sql = f"MERGE INTO {target_fqn} AS S USING {view} AS C ON {build_merge_on(keys)} WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *"  # nosec B608
    spark.sql(merge_sql)


@dataclass
class SilverStream:
    """Consome a Bronze como stream Delta e faz upsert idempotente na Silver.

    A Bronze é append-only: o stream Delta já entrega só as linhas novas. O primeiro
    run processa o snapshot existente (backfill) e depois o checkpoint assume o
    controle do progresso.
    """

    spark: SparkSession

    def read_stream(self, source_fqn: str) -> DataFrame:
        return (
            self.spark.readStream.format("delta")
            # ignora commits de manutenção (ex.: OPTIMIZE/compaction) — a Bronze só
            # cresce por append, então não há update/delete de negócio a considerar.
            .option("skipChangeCommits", "true")
            .table(source_fqn)
        )

    def _recompute_with_history(
        self,
        session: SparkSession,
        staged: DataFrame,
        target_fqn: str,
        keys: Sequence[str],
        recompute: Callable[[DataFrame], DataFrame],
        recompute_keys: Sequence[str],
    ) -> DataFrame:
        """Reprocessa cada grupo (`recompute_keys`) por inteiro, unindo o *staged* ao
        histórico já na Silver para as chaves tocadas neste batch.

        Para as chaves presentes no batch, traz do alvo os registros existentes
        (apenas os das mesmas chaves — a leitura é limitada), descarta as colunas
        derivadas (serão recalculadas), sobrepõe pelas linhas novas (`keys`) e chama
        `recompute` sobre o conjunto completo. Como o alvo é a fonte da verdade, um
        evento atrasado é reconciliado corretamente sem *watermark* e sem perda.

        Usa a sessão do micro-batch (`session`) para ler o alvo — dentro de
        `foreachBatch` o `staged` pertence a uma sessão clonada, e o join precisa
        acontecer na mesma sessão.
        """
        recompute_keys = list(recompute_keys)
        keys = list(keys)
        if not session.catalog.tableExists(target_fqn):
            return recompute(staged)

        touched = staged.select(*recompute_keys).distinct()
        existing = session.table(target_fqn).join(touched, recompute_keys, "left_semi")
        derived = [c for c in existing.columns if c not in staged.columns]
        existing_base = existing.drop(*derived) if derived else existing
        # linhas novas ganham das antigas de mesma chave; as demais do histórico entram
        combined = existing_base.join(staged, keys, "left_anti").unionByName(
            staged, allowMissingColumns=True
        )
        return recompute(combined)

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
        contract_schema=None,
        contract_required: Sequence[str] | None = None,
        quarantine_table: str | None = None,
        schema_version: str = "1.0",
        recompute: Callable[[DataFrame], DataFrame] | None = None,
        recompute_keys: Sequence[str] | None = None,
    ):
        """Executa o stream com Trigger.AvailableNow e bloqueia até terminar.

        Etapas por micro-batch, na ordem:

        1. **Data contract** (se `contract_schema` for informado): separa eventos
           que respeitam o schema/campos obrigatórios dos que violam. Os inválidos
           vão para `quarantine_table` (DLQ) com payload cru + motivo, em vez de
           serem descartados; só os válidos seguem para o `transform`.
        2. **Recomputação por chave** (se `recompute` for informado): junta o
           *staged* ao histórico já gravado na Silver para as chaves tocadas
           (`recompute_keys`) e reprocessa cada grupo por inteiro. Isso remove a
           dependência de eventos correlatos caírem no **mesmo micro-batch** —
           derivações que olham o vizinho (ex.: transferência entre atendimentos de
           uma chamada) ficam corretas mesmo com chegada em batches diferentes.
        3. **Gate de Data Quality** (se `expectations` for informado): valida o
           *staged*, persiste o relatório em `dq_results_table` e uma falha
           **crítica** interrompe o batch.
        4. **MERGE** idempotente por chave de negócio.
        """

        def _batch(micro_df: DataFrame, batch_id: int) -> None:
            if micro_df.isEmpty():
                return
            # Dentro de foreachBatch o micro-batch pertence a uma sessão CLONADA; usar
            # essa sessão em tudo (leitura do alvo, temp view, MERGE) evita "view não
            # encontrada" e joins entre sessões diferentes.
            session = micro_df.sparkSession
            changes = micro_df
            if contract_schema is not None:
                changes, quarantined = validate_contract(
                    changes,
                    contract_schema,
                    contract_required or [],
                    source=source_fqn,
                    schema_version=schema_version,
                )
                if quarantine_table:
                    quarantined.write.format("delta").mode("append").saveAsTable(quarantine_table)
                if changes.isEmpty():
                    return
            staged = transform(changes)
            if recompute is not None and recompute_keys:
                staged = self._recompute_with_history(session, staged, target_fqn, keys, recompute, recompute_keys)
            if expectations:
                from quality import run_expectations  # lazy: evita acoplar o import do módulo
                report = run_expectations(staged, expectations, dataset=target_fqn)
                print(report.summary())
                if dq_results_table:
                    report.to_table(session, dq_results_table)
                report.raise_if_critical_failed()
            merge_upsert(session, target_fqn, staged, keys, cluster_by=cluster_by)

        query = (
            self.read_stream(source_fqn)
            .writeStream
            .foreachBatch(_batch)
            .option("checkpointLocation", checkpoint_location)
            .trigger(availableNow=True)
            .start()
        )
        query.awaitTermination()
        return query
