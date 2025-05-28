# Databricks notebook source
# MAGIC %md
# MAGIC ##### Imports

# COMMAND ----------

from pyspark.sql import functions as F, types as T
from pyspark.sql.avro.functions import from_avro
from cryptography.fernet import Fernet
import base64

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Variables

# COMMAND ----------


eh_namespace = 'evhnscjprd001'
eventhub_name = "evh_user_random_schema"
connection_string = dbutils.secrets.get(scope="data-master-akv", key="EventhubConnectionString")
storage_account_name  = "stacjprd001"
database_name = "bronze_users"
table_name = "users" 
container_name = "contcjprd001"
container_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/bronze/{database_name}"
delta_table_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/bronze/{database_name}/{table_name}"

with open("/Workspace/Users/cristianoprojeto@hotmail.com/project_users/user_schema.avsc", "r") as file:
    schema_json = file.read()

eh_conf = {
   'eventhubs.connectionString': sc._jvm.org.apache.spark.eventhubs.EventHubsUtils.encrypt(f"{connection_string};EntityPath={eventhub_name}"),
    'eventhubs.startingPosition': '{"offset": "-1", "seqNo": -1, "enqueuedTime": null, "isInclusive": true}'
}


# COMMAND ----------

# MAGIC %md
# MAGIC ##### Function Encrypt

# COMMAND ----------

key = Fernet.generate_key()
fernet = Fernet(key)

def encrypt_data(data):
    return fernet.encrypt(data.encode()).decode() if data else None

spark.udf.register("encrypt_data", lambda z: encrypt_data(z))

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Read Stream

# COMMAND ----------

df = (spark.readStream
    .format("eventhubs")
    .options(**eh_conf)
    .load())
df.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Edit columns

# COMMAND ----------

df = df.select(from_avro(F.col("body"), schema_json).alias("data")) \
    .select('data.*') \
    .withColumn('ingest_time', F.current_timestamp())\
    .withColumn('dat_ref_carga', F.to_date('ingest_time')) 

for col in df.columns:
    df = df.withColumn(col, F.col(col).cast('string'))

df = df.withColumn("email", F.expr("encrypt_data(email)")) \
    .withColumn("phone", F.expr("encrypt_data(phone)")) \
    .withColumn("cell", F.expr("encrypt_data(cell)"))

schema_df = ', '.join(f"{col} string" for col in df.columns)

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Create Database

# COMMAND ----------

spark.sql(f"""CREATE DATABASE IF NOT EXISTS {database_name} LOCATION '{container_path}'""")

spark.sql(f"""CREATE TABLE IF NOT EXISTS {database_name}.{table_name} (
            {schema_df}
        )
    USING DELTA
    PARTITIONED BY (dat_ref_carga)
    LOCATION '{delta_table_path}'
    """)

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Write table

# COMMAND ----------

query = (df.writeStream
         .format("delta")
         .outputMode("append")
         .trigger(once=True)
         .option("checkpointLocation", f"{delta_table_path}/_checkpoints/")
         .start(delta_table_path))

try:
    query.awaitTermination()
except Exception as e:
    print(f"Consulta falhou: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Output

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from bronze_users.users