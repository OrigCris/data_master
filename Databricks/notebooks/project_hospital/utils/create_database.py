# Databricks notebook source
storage_account_name  = "stacjprd001"
container_name = "contcjprd001"

# COMMAND ----------

database_name = "bronze_hospital"
container_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/bronze/{database_name}"

spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name} LOCATION '{container_path}'")

# COMMAND ----------

database_name = "silver_hospital"
container_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/silver/{database_name}"

spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name} LOCATION '{container_path}'")

# COMMAND ----------

database_name = "gold_hospital"
container_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/gold/{database_name}"

spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name} LOCATION '{container_path}'")