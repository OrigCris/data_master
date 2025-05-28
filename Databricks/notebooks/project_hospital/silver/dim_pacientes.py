# Databricks notebook source
from pyspark.sql import functions as F

# Leitura da camada Bronze
df_bronze = spark.table('prd.bronze.pacientes')

df_silver = df_bronze \
    .withColumn('NOME', F.upper(F.col('NOME'))) \
    .withColumn("DT_NASCIMENTO", F.to_date("DT_NASCIMENTO", "yyyy-MM-dd")) \
    .withColumn('DH_REFE_CRGA', F.current_timestamp()) \
    .drop('ingestion_date', 'ingestion_timestamp', 'source', 'ingestion_id')

df_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f'prd.silver.dim_pacientes')