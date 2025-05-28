# Databricks notebook source
# MAGIC %md
# MAGIC ##### Imports

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Variables

# COMMAND ----------

storage_account_name  = "stacjprd001"
database_name = "silver_users"

table_name = "users_clean" 
container_name = "contcjprd001"

container_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/silver/{database_name}"
delta_table_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/silver/{database_name}/{table_name}"

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Create Database

# COMMAND ----------

spark.sql(f"""CREATE DATABASE IF NOT EXISTS {database_name} LOCATION '{container_path}'""")

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Get Data from Bronze

# COMMAND ----------

df_table_users = spark.table('bronze_users.users')

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Clean Data

# COMMAND ----------

df_users_clean = df_table_users\
    .select('dat_ref_carga', 'name', 'gender', 'nat', 'id', 'location') \
    .withColumn('location_split', F.split(F.col('location'), ',')) \
    .withColumn('NM_ESTADO', F.col('location_split')[3]) \
    .withColumn('NM_PAIS', F.col('location_split')[4]) \
    .withColumn('SG_PAIS', F.col('nat')) \
    .withColumn('NM_USUA', F.split(F.col('name'), ',')) \
    .withColumn('NM_USUA', F.concat(F.col('NM_USUA')[1], F.regexp_extract(F.col('NM_USUA')[2], r'([\sA-z]+)', 1))) \
    .withColumn('TP_DOCT', F.regexp_extract(F.col('id'), r'([A-z]+)', 1)) \
    .withColumnRenamed('gender', 'NM_GENERO')\
    .withColumnRenamed('first_name', 'NM_USUA')\
    .withColumnRenamed('dat_ref_carga', 'DT_REFE_CRGA')\
    .select('NM_USUA', 'TP_DOCT', 'NM_GENERO', 'SG_PAIS','NM_PAIS', 'NM_ESTADO', 'DT_REFE_CRGA')

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Write Table

# COMMAND ----------

df_users_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy('DT_REFE_CRGA') \
    .option("path", delta_table_path) \
    .saveAsTable(f"{database_name}.{table_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Output

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from silver_users.users_clean