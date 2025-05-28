# Databricks notebook source
from pyspark.sql import functions as F, Window as W
from faker import Faker
import random, uuid

# Inicializa o Faker
fake = Faker('pt_BR')

# Número de pacientes a gerar
num_pacientes = 100_000

# Geração do DataFrame de pacientes
df_pacientes = spark.createDataFrame([
    {
        "NOME": fake.name(),
        "SEXO": random.choice(["M", "F", "Outro"]),
        "DT_NASCIMENTO": fake.date_of_birth(minimum_age=0, maximum_age=100).strftime("%Y-%m-%d") if random.random() > 0.01 else "31-02-2020",  # 1% inválida
        "DS_ESTADO": fake.estado_sigla(),
        "EMAIL": fake.email() if random.random() > 0.05 else None,  # 5% nulos
        "ID_CONVENIO": random.randint(1, 20)
    }
    for _ in range(num_pacientes)
])

df_pacientes = df_pacientes \
    .withColumn("ID_PACIENTE", F.row_number().over(W.orderBy("NOME"))) \
    .select("ID_PACIENTE", "NOME", "SEXO", "DT_NASCIMENTO", "DS_ESTADO", "EMAIL", "ID_CONVENIO") \
    .withColumn("ingestion_date", F.current_date()) \
    .withColumn("ingestion_timestamp", F.current_timestamp()) \
    .withColumn("source", F.lit('gerador_faker')) \
    .withColumn("ingestion_id", F.lit(str(uuid.uuid4())))

df_pacientes.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy('ingestion_date') \
    .saveAsTable(f'prd.bronze.pacientes')
