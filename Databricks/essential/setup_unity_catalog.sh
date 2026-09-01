#!/bin/bash
# =============================================================================
# setup_unity_catalog.sh — Plumbing do Unity Catalog + secret scope
#
# Cria, via Databricks CLI (sem operação manual no workspace):
#   1. secret scope AKV-backed (leitura de segredos do Key Vault pelos jobs)
#   2. storage credential a partir do Access Connector (identidade do UC no storage)
#   3. external location mapeando o container ADLS à storage credential
#   4. catalog `prd`
#
# Pré-requisitos:
#   - Recursos provisionados (Bicep) e identidade/segredos (bootstrap.sh)
#   - Profile do Databricks CLI configurado: `databricks configure --profile prd`
#   - Metastore do Unity Catalog já atribuído ao workspace (feito por account admin;
#     é a única etapa fora deste script, pois é no nível da conta, não do workspace)
#
# Uso: ./setup_unity_catalog.sh
# =============================================================================
set -euo pipefail

PROFILE="${DATABRICKS_PROFILE:-prd}"
DBX="databricks --profile ${PROFILE}"

# ----------------------------- Parâmetros ------------------------------------
RESOURCE_GROUP="rsgcjtecprd001"
STORAGE_ACCOUNT="stacjtecprd001"
CONTAINER="ctcjtecprd001"
KEY_VAULT="akvcjtecprd001"
ACCESS_CONNECTOR="ac-databricks-uc"

CATALOG="prd"
SECRET_SCOPE="data-master-akv"
STORAGE_CREDENTIAL="sc-dm-adls"
EXTERNAL_LOCATION="el-dm-lake"
LAKE_URL="abfss://${CONTAINER}@${STORAGE_ACCOUNT}.dfs.core.windows.net/"

# Ids resolvidos do Azure
AC_ID=$(az databricks access-connector show -g "${RESOURCE_GROUP}" -n "${ACCESS_CONNECTOR}" --query id -o tsv)
KV_ID=$(az keyvault show -n "${KEY_VAULT}" --query id -o tsv)
KV_DNS="https://${KEY_VAULT}.vault.azure.net/"

# --------------------- 1) Secret scope (AKV-backed) --------------------------
if ${DBX} secrets list-scopes 2>/dev/null | grep -qw "${SECRET_SCOPE}"; then
  echo "[=] secret scope '${SECRET_SCOPE}' já existe"
else
  ${DBX} secrets create-scope --json "{\"scope\":\"${SECRET_SCOPE}\",\"scope_backend_type\":\"AZURE_KEYVAULT\",\"backend_azure_keyvault\":{\"resource_id\":\"${KV_ID}\",\"dns_name\":\"${KV_DNS}\"}}"
  echo "[+] secret scope '${SECRET_SCOPE}' criado"
fi

# ------------- 2) Storage credential (a partir do Access Connector) ----------
if ${DBX} storage-credentials get "${STORAGE_CREDENTIAL}" >/dev/null 2>&1; then
  echo "[=] storage credential '${STORAGE_CREDENTIAL}' já existe"
else
  ${DBX} storage-credentials create --json "{\"name\":\"${STORAGE_CREDENTIAL}\",\"azure_managed_identity\":{\"access_connector_id\":\"${AC_ID}\"}}"
  echo "[+] storage credential '${STORAGE_CREDENTIAL}' criado"
fi

# ----------------------- 3) External location (container) --------------------
if ${DBX} external-locations get "${EXTERNAL_LOCATION}" >/dev/null 2>&1; then
  echo "[=] external location '${EXTERNAL_LOCATION}' já existe"
else
  ${DBX} external-locations create --json "{\"name\":\"${EXTERNAL_LOCATION}\",\"url\":\"${LAKE_URL}\",\"credential_name\":\"${STORAGE_CREDENTIAL}\"}"
  echo "[+] external location '${EXTERNAL_LOCATION}' criado"
fi

# ------------------------------- 4) Catalog ----------------------------------
# ------------------------------- 4) Catalog ----------------------------------
CATALOG_STORAGE="${LAKE_URL}managed/prd"

if ${DBX} catalogs get "${CATALOG}" >/dev/null 2>&1; then
  echo "[=] catalog '${CATALOG}' já existe"
else
  ${DBX} catalogs create --json "{
    \"name\": \"${CATALOG}\",
    \"storage_root\": \"${CATALOG_STORAGE}\"
  }"
  echo "[+] catalog '${CATALOG}' criado com managed storage em '${CATALOG_STORAGE}'"
fi

echo "[OK] Unity Catalog pronto. Em seguida rode o notebook essential/create_databases."
