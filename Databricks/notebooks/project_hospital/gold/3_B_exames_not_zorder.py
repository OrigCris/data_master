# Databricks notebook source
from pyspark.sql import functions as F

# Leitura da Silver
exames = spark.table('prd.silver.fato_exames')

# Mesma filtragem usada na versão otimizada
df_nao_clustered = (
    exames
    .filter("STATUS_EXAME = 'Finalizado'")
    .filter('DT_EXAME >= date_sub(current_date(), 90)')
    .withColumn('execution_time', F.current_timestamp())
)

# Escrita padrão sem otimizações
(
    df_nao_clustered.write
    .format('delta')
    .mode('overwrite')
    .saveAsTable('prd.gold.exames_not_zorder')
)