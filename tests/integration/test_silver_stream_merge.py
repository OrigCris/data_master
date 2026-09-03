"""Teste de integração: streaming Delta + checkpoint + MERGE idempotente (Spark + Delta).

Exercita a parte arquitetural central do pipeline Bronze→Silver com um Spark real:
uma primeira execução faz o backfill do snapshot da Bronze; uma segunda, após uma
atualização e uma inserção na Bronze, prova que o MERGE é **idempotente** (atualiza sem
duplicar) e que o **checkpoint** só reprocessa o que mudou.

Auto-skip onde não há `pyspark`/`delta` (ex.: job de testes unitários); roda no job de
CI dedicado que instala Java + Spark + Delta.
"""
import pytest

pytest.importorskip("pyspark")
pytest.importorskip("delta")

from delta import configure_spark_with_delta_pip  # noqa: E402
from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from transforms import SilverStream  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def spark(tmp_path_factory):
    warehouse = tmp_path_factory.mktemp("warehouse")
    builder = (
        SparkSession.builder.master("local[2]")
        .appName("it-silver-stream")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", str(warehouse))
        .config("spark.sql.shuffle.partitions", "2")
    )
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    yield session
    session.stop()


def _append_events(spark, fqn, events):
    """Grava eventos já estruturados na Bronze (append-only → o stream Delta os entrega)."""
    spark.createDataFrame(list(events), ["id", "val"]).write.format("delta").mode("append").saveAsTable(fqn)


def _transform(df):
    # A Bronze já entrega os campos estruturados; a Silver apenas projeta/renomeia.
    return df.select(F.col("id").alias("ID"), F.col("val").alias("VAL"))


def test_stream_checkpoint_merge_idempotente(spark, tmp_path):
    spark.sql("CREATE DATABASE IF NOT EXISTS it")
    bronze = "spark_catalog.it.bronze_ura"
    silver = "spark_catalog.it.silver_ura"
    checkpoint = str(tmp_path / "ckpt")

    # Bronze append-only (já estruturada): consumida como fonte de streaming Delta.
    spark.sql(f"CREATE TABLE {bronze} (id STRING, val STRING) USING DELTA")
    _append_events(spark, bronze, [("1", "a"), ("2", "b"), ("3", "c")])

    stream = SilverStream(spark)
    stream.run(bronze, silver, _transform, keys=["ID"], checkpoint_location=checkpoint)

    first = {r["ID"]: r["VAL"] for r in spark.table(silver).collect()}
    assert first == {"1": "a", "2": "b", "3": "c"}

    # Atualiza o ID 2 e adiciona o ID 4; reexecuta com o MESMO checkpoint.
    _append_events(spark, bronze, [("2", "B2"), ("4", "d")])
    stream.run(bronze, silver, _transform, keys=["ID"], checkpoint_location=checkpoint)

    rows = spark.table(silver).collect()
    result = {r["ID"]: r["VAL"] for r in rows}
    assert len(rows) == 4, "MERGE deve fazer upsert sem duplicar"
    assert result == {"1": "a", "2": "B2", "3": "c", "4": "d"}


def _append_calls(spark, fqn, rows):
    """Grava atendimentos já estruturados na Bronze de CALLS."""
    df = spark.createDataFrame(list(rows), ["id_cham", "id_aten", "id_asst", "area", "dh_inic"])
    df.withColumn("dh_inic", F.to_timestamp("dh_inic")).write.format("delta").mode("append").saveAsTable(fqn)


def _transform_calls(df):
    # `DT_INIC` é a coluna do recorte temporal da recomputação (lookback), como na Silver.
    return df.select(
        F.col("id_cham").alias("ID_CHAM"),
        F.col("id_aten").alias("ID_ATEN"),
        F.col("id_asst").alias("ID_ASST"),
        F.col("area").alias("DS_AREA_ATEN"),
        F.col("dh_inic").alias("DH_INIC"),
        F.to_date("dh_inic").alias("DT_INIC"),
    )


def test_recompute_calls_reconcilia_atendimento_de_outro_batch(spark, tmp_path):
    """Um atendimento que chega depois corrige os indicadores da chamada inteira.

    A janela `lead` por `ID_CHAM` só está correta se o batch for unido ao histórico já
    gravado na Silver: no primeiro batch o atendimento é o último da chamada
    (`IN_TRAF=0`); quando o segundo atendimento chega, o primeiro passa a `IN_TRAF=1` —
    e a `IN_TRAF_INDV=1`, por ser transferência para a mesma área.
    """
    spark.sql("CREATE DATABASE IF NOT EXISTS it")
    bronze = "spark_catalog.it.bronze_calls"
    silver = "spark_catalog.it.silver_calls"
    checkpoint = str(tmp_path / "ckpt_calls")

    spark.sql(
        f"CREATE TABLE {bronze} "
        "(id_cham STRING, id_aten STRING, id_asst STRING, area STRING, dh_inic TIMESTAMP) USING DELTA"
    )
    _append_calls(spark, bronze, [("C1", "A1", "X", "SUPORTE", "2026-01-01 10:00:00")])

    stream = SilverStream(spark)

    def run():
        stream.run(
            bronze,
            silver,
            _transform_calls,
            keys=["ID_CHAM", "ID_ATEN"],
            checkpoint_location=checkpoint,
            recompute_calls=True,
        )

    run()

    first = {r["ID_ATEN"]: (r["IN_TRAF"], r["IN_TRAF_INDV"]) for r in spark.table(silver).collect()}
    assert first == {"A1": (0, 0)}

    # Segundo atendimento da MESMA chamada, em outro micro-batch.
    _append_calls(spark, bronze, [("C1", "A2", "Y", "SUPORTE", "2026-01-01 10:05:00")])
    run()

    rows = spark.table(silver).collect()
    assert len(rows) == 2, "recomputação reescreve o histórico da chamada, sem duplicar"
    assert {r["ID_ATEN"]: (r["IN_TRAF"], r["IN_TRAF_INDV"]) for r in rows} == {"A1": (1, 1), "A2": (0, 0)}
