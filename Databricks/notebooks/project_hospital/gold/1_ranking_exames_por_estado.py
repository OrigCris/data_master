# Databricks notebook source
from pyspark.sql import functions as F, Window as W

# Leitura das tabelas Silver
exames = spark.table('prd.silver.fato_exames')
pacientes = spark.table('prd.silver.dim_pacientes')

# Join e agregação
df_base = (
    exames.join(pacientes, 'ID_PACIENTE')
    .groupBy('DS_ESTADO', 'TP_EXAME')
    .agg(F.count('*').alias('TOTAL_EXAMES'))
)

# Aplica ranking por estado
window_estado = W.partitionBy('DS_ESTADO').orderBy(F.desc('TOTAL_EXAMES'))

df_rank = (
    df_base
    .withColumn('RANK_EXAME_ESTADO', F.dense_rank().over(window_estado))
    .withColumn('execution_time', F.current_timestamp())
)

# Escrita em Delta
df_rank.write.format('delta').mode('overwrite').saveAsTable('prd.gold.ranking_exames_por_estado')
