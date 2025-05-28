# Databricks notebook source
from pyspark.sql import functions as F

# Leitura da Bronze
df_bronze = spark.table('prd.bronze.exames')

# Limpeza e validações
df_silver = (
    df_bronze
    # 1. Data de exame válida
    .withColumn("DT_EXAME", F.to_date("DT_EXAME", "yyyy-MM-dd"))

    # 2. Convertendo o resultado para numérico
    .withColumn("VL_RSLT_EXAME", F.col("RESULTADO_EXAME").cast("double"))

    # 3. Renomeando colunas
    .withColumnRenamed('TIPO_EXAME', 'TP_EXAME')
    .withColumnRenamed('VALOR_REFERENCIA', 'VL_REFE')

    # 4. Filtrando registros válidos
    .filter(
        (F.col('ID_PACIENTE').isNotNull())
        & (F.col('ID_PACIENTE').isNotNull())
        & (F.col('RESULTADO_EXAME') != 'erro')
        & (F.col("STATUS_EXAME").isin("Pendente", "Finalizado", "Cancelado", "Alterado"))
    )

    # 5. Adicionando coluna de data da carga
    .withColumn('DH_REFE_CRGA', F.current_timestamp())

    # 6. Retirando colunas não usadas
    .drop('ingestion_date', 'ingestion_timestamp', 'source', 'ingestion_id', 'RESULTADO_EXAME')
)

df_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f'prd.silver.fato_exames')
