# Databricks notebook source
from pyspark.sql import functions as F

# Leitura da Silver
exames = spark.table('prd.silver.fato_exames')

# Filtra exames recentes e válidos
df_cluster = (
    exames
    .filter("STATUS_EXAME = 'Finalizado'")
    .filter('DT_EXAME >= date_sub(current_date(), 90)')
    .withColumn('execution_time', F.current_timestamp())
)

(
    df_cluster.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable("prd.gold.exames_zorder")
)

# Otimização com ZORDER
spark.sql("""
  OPTIMIZE prd.gold.exames_zorder ZORDER BY (TP_EXAME, STATUS_EXAME)
""")