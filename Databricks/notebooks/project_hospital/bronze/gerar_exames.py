# Databricks notebook source
from pyspark.sql import functions as F, Window as W
from faker import Faker
import random, uuid

# Inicializa o Faker
fake = Faker('pt_BR')

# Número de exames a gerar
num_exames = 200_000

# Funções auxiliares
def random_tipo_exame():
    return random.choice(["Hemograma", "Glicemia", "Colesterol", "TSH", "PCR", "Covid-19", "Ureia", "Creatinina"])

def random_status_exame():
    return random.choice(["Pendente", "Finalizado", "Cancelado", "Alterado"])

# Geração dos dados
df_exames = spark.createDataFrame([
    {
        "ID_EXAME": str(uuid.uuid4()),
        "ID_PACIENTE": random.randint(1, 100_000) if random.random() > 0.01 else None,  # 1% inválidos
        "DT_EXAME": fake.date_between(start_date='-2y', end_date='today').strftime("%Y-%m-%d") if random.random() > 0.01 else "32-13-2023",  # 1% inválidas
        "TIPO_EXAME": random_tipo_exame(),
        "RESULTADO_EXAME": (round(random.uniform(0.0, 500.0), 2) if random.random() > 0.03 else "erro"),  # 3% erros
        "UNIDADE_MEDIDA": random.choice(["mg/dL", "mmol/L", "ng/mL", "u/L"]),
        "VALOR_REFERENCIA": random.choice(["<100", "70-110", "<5.6", "0-30"]),
        "STATUS_EXAME": random_status_exame()
    }
    for _ in range(num_exames)
])

df_exames = df_exames \
    .withColumn("ingestion_date", F.current_date()) \
    .withColumn("ingestion_timestamp", F.current_timestamp()) \
    .withColumn("source", F.lit('gerador_faker')) \
    .withColumn("ingestion_id", F.lit(str(uuid.uuid4())))

df_exames.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy('ingestion_date') \
    .saveAsTable(f'prd.bronze.exames')