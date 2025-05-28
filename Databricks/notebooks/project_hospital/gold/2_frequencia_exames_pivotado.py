# Databricks notebook source
from pyspark.sql import functions as F

# Leitura das tabelas Silver
exames = spark.table('prd.silver.fato_exames')
pacientes = spark.table('prd.silver.dim_pacientes')

# Join e agregação
df = (
    exames.join(pacientes, 'ID_PACIENTE')
    .groupBy('DS_ESTADO', 'SEXO')
    .pivot('TP_EXAME')
    .agg(F.count('*'))
    .na.fill(0)
    .withColumn('execution_time', F.current_timestamp())
)

# Escrita da Gold
df.write.format('delta').mode('overwrite').saveAsTable('prd.gold.frequencia_exames_pivotado')
