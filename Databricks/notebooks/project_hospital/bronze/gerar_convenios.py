# Databricks notebook source
from pyspark.sql import functions as F, Window as W
import random, uuid
from datetime import datetime

# Lista fixa dos nomes de convênios
convenios = [
    "Unimed", "Amil", "Bradesco Saúde", "SulAmérica", "NotreDame Intermédica", 
    "Porto Seguro Saúde", "Hapvida", "Assim Saúde", "Golden Cross", "Cassi",
    "Caixa Saúde", "Samp", "São Francisco Saúde", "Smile Saúde", "Plena Saúde",
    "Biovida Saúde", "MedSênior", "Santa Casa Saúde", "Prevent Senior", "Vitallis"
]

# Criação do DataFrame base
df_convenios = spark.createDataFrame([
    {
        "NM_CONVENIO": nome,
        "TP_CONVENIO": random.choice(["Particular", "Empresarial", "Coletivo"])
    }
    for nome in convenios
])

# Adiciona colunas técnicas e ID incremental
df_convenios = df_convenios.withColumn("ID_CONVENIO", F.row_number().over(W.orderBy("NM_CONVENIO"))) \
    .select("ID_CONVENIO", "NM_CONVENIO", "TP_CONVENIO") \
    .withColumn("ingestion_date", F.current_date()) \
    .withColumn("ingestion_timestamp", F.current_timestamp()) \
    .withColumn("source", F.lit('gerador_faker')) \
    .withColumn("ingestion_id", F.lit(str(uuid.uuid4())))

df_convenios.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy('ingestion_date') \
    .saveAsTable(f'prd.bronze.convenios')