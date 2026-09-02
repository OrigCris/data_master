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
