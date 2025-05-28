# Databricks notebook source
# MAGIC %md
# MAGIC ##### Imports

# COMMAND ----------

from pyspark.sql import functions as F, Window as W

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Variables

# COMMAND ----------

storage_account_name  = "stacjprd001"
database_name = "gold_users"
container_name = "contcjprd001"

container_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/gold/{database_name}"

table_country = "users_country" 
table_cont = "users_cont"
table_last_login = "users_doct"

delta_table_country_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/silver/{database_name}/{table_country}"
delta_table_cont_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/silver/{database_name}/{table_cont}"
delta_table_last_login_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/silver/{database_name}/{table_last_login}"

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Create Database

# COMMAND ----------

spark.sql(f"""CREATE DATABASE IF NOT EXISTS {database_name} LOCATION '{container_path}'""")

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Get Data from Silver

# COMMAND ----------

df_table_users_clean = spark.table('silver_users.users_clean')

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Gold Tables

# COMMAND ----------

df_groupby_country = df_table_users_clean.groupby('NM_PAIS', 'NM_ESTADO').agg(
    F.count('NM_USUA').alias('QTD_USUA')
)

south_american_countries = [
    "AR",
    "BO",
    "BR",
    "CL",
    "CO",
    "EC",
    "GY",
    "PY",
    "PE",
    "SR",
    "UY",
    "VE"
]

df_table_cont = df_table_users_clean \
    .filter(F.col('SG_PAIS').isin(south_american_countries)) \
    .groupby('NM_PAIS').agg(
        F.count('NM_USUA').alias('QTD_USUA')
    )

df_table_last_login = df_table_users_clean \
    .withColumn('RN', F.row_number().over(W.partitionBy('NM_USUA').orderBy(F.desc('DT_REFE_CRGA')))) \
    .filter(F.col('RN') == 1).drop('RN')

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Write Table

# COMMAND ----------

df_groupby_country.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", delta_table_country_path) \
    .saveAsTable(f"{database_name}.{table_country}")

df_table_cont.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", delta_table_cont_path) \
    .saveAsTable(f"{database_name}.{table_cont}")

df_table_last_login.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", delta_table_last_login_path) \
    .saveAsTable(f"{database_name}.{table_last_login}")

# COMMAND ----------

# MAGIC %md
# MAGIC ##### Output

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from gold_users.users_country

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from gold_users.users_cont

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from gold_users.users_doct