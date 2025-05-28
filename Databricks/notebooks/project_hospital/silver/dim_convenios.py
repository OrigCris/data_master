# Databricks notebook source
from pyspark.sql import functions as F

# Leitura da camada Bronze
df_bronze = spark.table('prd.bronze.convenios')

df_silver = df_bronze \
    .withColumn('NM_CONVENIO', F.initcap(F.trim(F.col('NM_CONVENIO')))) \
    .withColumn('TP_CONVENIO', F.col('TP_CONVENIO').isin('Particular', 'Empresarial', 'Coletivo')) \
    .withColumn('DH_REFE_CRGA', F.current_timestamp()) \
    .drop('ingestion_date', 'ingestion_timestamp', 'source', 'ingestion_id')

df_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f'prd.silver.dim_convenios')