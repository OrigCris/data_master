"""Upsert incremental Bronze→Silver: stream Delta + foreachBatch + MERGE idempotente.

A Bronze é append-only, então o stream Delta entrega só as linhas novas
(`skipChangeCommits` ignora reescritas de OPTIMIZE). Com `AvailableNow` + `foreachBatch`
a escrita é at-least-once — a não-duplicidade vem do MERGE por chave de negócio, não do
checkpoint (que só controla o progresso). Ver ADR-0002.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from quality import run_expectations

from .parse import validate_contract

try:  # pragma: no cover - depende do runtime Spark
    from pyspark.sql import DataFrame, SparkSession, Window
    from pyspark.sql import functions as F
except (ImportError, ModuleNotFoundError):  # pragma: no cover
    DataFrame = object  # type: ignore
    SparkSession = object  # type: ignore
    Window = None  # type: ignore
    F = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - só para tipagem (contracts exige pyspark)
    from .contracts import Contract

# Chaves da recomputação de `tabe_calls`: a chamada (`ID_CHAM`) é o grupo recalculado
# por inteiro; a linha da Silver é o atendimento (`ID_CHAM` + `ID_ATEN`).
CALLS_RECOMPUTE_KEY = "ID_CHAM"
CALLS_ROW_KEYS = ["ID_CHAM", "ID_ATEN"]
# Recorte temporal da leitura do histórico: coluna de data da Silver (é `cluster_by`, o
# filtro faz *data skipping*) e a folga aplicada à data mais antiga do batch. Um dia
# cobre a chamada que vira a meia-noite e o evento que chega atrasado dentro do dia.
CALLS_DATE_COL = "DT_INIC"
CALLS_LOOKBACK_DAYS = 1


def add_transfer_indicators(calls_df: DataFrame) -> DataFrame:
    """Deriva os indicadores de transferência olhando a chamada **inteira**.

    A janela por `ID_CHAM` (ordenada por `DH_INIC`) precisa enxergar todos os
    atendimentos da chamada: `IN_TRAF` = houve próximo atendimento; `IN_TRAF_INDV` = a
    transferência foi para a mesma área (indevida). Espera o conjunto completo da
    chamada — em streaming, use `SilverStream(...).run(recompute_calls=True)`, que une o
    batch ao histórico antes de aplicar a janela.
    """
    w = Window.partitionBy(CALLS_RECOMPUTE_KEY).orderBy(F.asc("DH_INIC"))
    lead_asst = F.lead("ID_ASST", 1).over(w)
    lead_area = F.lead("DS_AREA_ATEN", 1).over(w)
    return calls_df.withColumn(
        "IN_TRAF", F.when(lead_asst.isNotNull(), F.lit(1)).otherwise(F.lit(0))
    ).withColumn(
        "IN_TRAF_INDV",
        F.when((F.col("IN_TRAF") == 1) & (F.col("DS_AREA_ATEN") == lead_area), F.lit(1)).otherwise(F.lit(0)),
    )


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


def ensure_table(spark: SparkSession, fqn: str, template_df: DataFrame, cluster_by: Sequence[str] | None = None) -> None:
    """Cria a tabela vazia com o schema de `template_df`, se ainda não existir."""
    assert_fqn(fqn)
    if not spark.catalog.tableExists(fqn):
        empty_df = spark.createDataFrame([], template_df.schema)
        empty_df.write.format("delta").mode("overwrite").saveAsTable(fqn)
        if cluster_by:
            cols = ", ".join(cluster_by)
            spark.sql(f"ALTER TABLE {fqn} CLUSTER BY ({cols})")


def merge_upsert(
    spark: SparkSession,
    target_table_fqn: str,
    transformed_df: DataFrame,
    keys: Sequence[str],
    cluster_by: Sequence[str] | None = None,
) -> None:
    """Aplica MERGE (upsert) idempotente de `transformed_df` na tabela alvo."""
    ensure_table(spark, target_table_fqn, transformed_df, cluster_by=cluster_by)
    source_view = "_stg_" + target_table_fqn.replace(".", "_")
    transformed_df.createOrReplaceTempView(source_view)
    # Identificadores internos e validados (assert_fqn; chaves e view construídos em
    # código) — sem input de usuário, logo sem vetor de injeção.
    merge_sql = f"MERGE INTO {target_table_fqn} AS S USING {source_view} AS C ON {build_merge_on(keys)} WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *"  # nosec B608
    spark.sql(merge_sql)


def merge_quarantine(spark: SparkSession, quarantine_table: str, quarantine_df: DataFrame) -> None:
    """Grava a DLQ de forma idempotente por `event_id`.

    O `foreachBatch` é at-least-once: um retry do mesmo micro-batch reapresenta o mesmo
    evento inválido. Como o `event_id` é a identidade do evento no Event Hub
    (`source|partition|offset`), o MERGE `WHEN NOT MATCHED` insere só a primeira
    ocorrência — sem duplicidade lógica na DLQ, e sem colapsar eventos distintos que por
    acaso tenham o mesmo payload.
    """
    ensure_table(spark, quarantine_table, quarantine_df)
    quarantine_view = "_dlq_" + quarantine_table.replace(".", "_")
    quarantine_df.createOrReplaceTempView(quarantine_view)
    merge_sql = f"MERGE INTO {quarantine_table} AS T USING {quarantine_view} AS S ON T.event_id = S.event_id WHEN NOT MATCHED THEN INSERT *"  # nosec B608
    spark.sql(merge_sql)


@dataclass
class SilverStream:
    """Consome a Bronze (append-only, já estruturada) como stream Delta e faz upsert
    idempotente na Silver.

    O primeiro run processa o snapshot existente (backfill); depois o checkpoint assume
    o controle do progresso.
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

    def _recompute_calls_with_history(
        self,
        session: SparkSession,
        transformed_df: DataFrame,
        target_table_fqn: str,
    ) -> DataFrame:
        """Reprocessa cada chamada (`ID_CHAM`) por inteiro, unindo o batch ao histórico
        já na Silver, e recalcula os indicadores de transferência.

        A leitura do alvo é limitada por **dois filtros**: o **temporal**
        (`DT_INIC >= menor data do batch - CALLS_LOOKBACK_DAYS`, que é *data skipping*
        sobre o `cluster_by`) e o das **chamadas tocadas** pelo batch — em vez de varrer
        o histórico inteiro. Sobre esse recorte, descarta as colunas derivadas (serão
        recalculadas), sobrepõe pelas linhas novas (`ID_CHAM` + `ID_ATEN`) e aplica a
        janela sobre a chamada completa.

        Como o alvo é a fonte da verdade, um atendimento atrasado é reconciliado sem
        *watermark* e sem perda — desde que dentro da janela de lookback; um atendimento
        cujo par esteja fora dela não reabre a chamada. Usa `session` (a do micro-batch)
        para que o join ocorra na mesma sessão do batch.
        """
        if not session.catalog.tableExists(target_table_fqn):
            return add_transfer_indicators(transformed_df)

        affected_calls = transformed_df.select(CALLS_RECOMPUTE_KEY).distinct()

        # Recorte temporal: da data mais antiga do batch (menos o lookback) em diante.
        # O `first()` roda uma agregação sobre o micro-batch — barato perto do ganho de
        # não varrer o histórico inteiro do alvo a cada batch. Sem data no batch (coluna
        # toda nula), resta o recorte por chamada.
        batch_min_date = transformed_df.agg(F.min(CALLS_DATE_COL).alias("min_date")).first()["min_date"]
        if batch_min_date is None:
            history_window = F.lit(True)
        else:
            history_start = batch_min_date - timedelta(days=CALLS_LOOKBACK_DAYS)
            history_window = F.col(CALLS_DATE_COL) >= F.lit(history_start)

        existing_calls = (
            session.table(target_table_fqn)
            .filter(history_window)
            .join(affected_calls, [CALLS_RECOMPUTE_KEY], "left_semi")
        )

        derived_cols = [c for c in existing_calls.columns if c not in transformed_df.columns]
        historical_calls = existing_calls.drop(*derived_cols) if derived_cols else existing_calls
        combined_calls = historical_calls.join(transformed_df, CALLS_ROW_KEYS, "left_anti").unionByName(
            transformed_df, allowMissingColumns=True
        )
        return add_transfer_indicators(combined_calls)

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
        contract: Contract | None = None,
        quarantine_table: str | None = None,
        recompute_calls: bool = False,
    ):
        """Roda o stream (AvailableNow) e bloqueia até terminar.

        Por micro-batch: (1) **contrato** da tabela (todas as colunas do schema) —
        inválidos vão à `quarantine_table` (idempotente por `event_id`), só os válidos
        seguem; (2) **transform** (renomeação/derivação, sem `from_json` — a Bronze já
        estruturou);
        (3) **recomputação da chamada**, se `recompute_calls` (junta o batch ao
        histórico e reprocessa a chamada inteira — corrige derivações entre batches);
        (4) **gate de DQ**, se informado (falha crítica interrompe); (5) **MERGE**
        idempotente por chave.
        """

        def _batch(micro_df: DataFrame, _batch_id: int) -> None:
            if micro_df.isEmpty():
                return
            # foreachBatch entrega o micro-batch numa sessão CLONADA; usá-la em tudo
            # (leitura do alvo, temp view, MERGE) evita "view não encontrada" e joins
            # entre sessões distintas.
            session = micro_df.sparkSession
            valid_events_df = micro_df
            if contract is not None:
                valid_events_df, quarantined_df = validate_contract(
                    valid_events_df, contract, source=source_table_fqn
                )
                if quarantine_table:
                    merge_quarantine(session, quarantine_table, quarantined_df)
                if valid_events_df.isEmpty():
                    return
            transformed_df = transform(valid_events_df)
            if recompute_calls:
                transformed_df = self._recompute_calls_with_history(
                    session, transformed_df, target_table_fqn
                )
            if expectations:
                dq_report = run_expectations(transformed_df, expectations, target_table_fqn)
                print(dq_report.summary())
                if dq_results_table:
                    dq_report.to_table(session, dq_results_table)
                dq_report.raise_if_critical_failed()
            merge_upsert(session, target_table_fqn, transformed_df, keys, cluster_by=cluster_by)

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
