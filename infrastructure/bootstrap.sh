#!/bin/bash
# =============================================================================
# bootstrap.sh — Identidade e segredos (o que o Bicep não faz)
#
# O provisionamento dos RECURSOS (storage, Event Hubs, Key Vault, Function App,
# Databricks, RBAC, app settings) é feito pelo Bicep:
#   dm provision -g <rg>      (ou az deployment group create ...)
#
# Este script cuida APENAS do que depende do Microsoft Graph / segredos rotativos,
# fora do escopo declarativo do ARM/Bicep:
#   - cria os Service Principals (produtor e consumidor)
#   - grava os segredos no Key Vault (credenciais dos SPNs + connection string do EH)
#   - concede os papéis (RBAC) que dependem desses SPNs
#
# Pré-requisito: rode o Bicep ANTES (os recursos precisam já existir).
# Uso: az login && ./bootstrap.sh
# =============================================================================

# ----------------------------- Variáveis -------------------------------------
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ACCOUNT_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

RESOURCE_GROUP="rsgcjtecprd001"
STORAGE_ACCOUNT="stacjtecprd001"
EVENTHUB_NAMESPACE="evhnscjtecprd001"
KEY_VAULT="akvcjtecprd001"

SPN_PRODUCER="spn_func_send"      # produz eventos (Function App → Event Hubs)
SPN_CONSUMER="spn_dtb_consumer"   # consome/processa (Databricks → Storage)

KV_ID=$(az keyvault show --name $KEY_VAULT --query id -o tsv)

# ------- Permissão para o operador gravar segredos no Key Vault (RBAC) --------
az role assignment create \
    --role "Key Vault Secrets Officer" \
    --assignee-object-id $ACCOUNT_OBJECT_ID \
    --scope $KV_ID

# ------------------ SPN produtor (Function App → Event Hubs) ------------------
SP_DETAILS=$(az ad sp create-for-rbac --name $SPN_PRODUCER --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP)
SP_APP_ID=$(echo $SP_DETAILS | jq -r '.appId')
SP_SECRET=$(echo $SP_DETAILS | jq -r '.password')
TENANT_ID=$(echo $SP_DETAILS | jq -r '.tenant')

az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalAppId" --value $SP_APP_ID
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalSecret" --value $SP_SECRET
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalTenantId" --value $TENANT_ID

# Ler segredos do Key Vault + enviar para o Event Hubs
az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee $SP_APP_ID \
    --scope $KV_ID

az role assignment create \
    --assignee $SP_APP_ID \
    --role "Azure Event Hubs Data Sender" \
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.EventHub/namespaces/$EVENTHUB_NAMESPACE"

# ------------------- SPN consumidor (Databricks → Storage) -------------------
DTB_SP_DETAILS=$(az ad sp create-for-rbac --name $SPN_CONSUMER --role "Contributor" --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP)
DTB_SP_APP_ID=$(echo $DTB_SP_DETAILS | jq -r '.appId')
DTB_SP_SECRET=$(echo $DTB_SP_DETAILS | jq -r '.password')
DTB_TENANT_ID=$(echo $DTB_SP_DETAILS | jq -r '.tenant')

az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalDTBAppId" --value $DTB_SP_APP_ID
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalDTBSecret" --value $DTB_SP_SECRET
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalDTBTenantId" --value $DTB_TENANT_ID

az role assignment create \
    --role "Storage Blob Data Contributor" \
    --assignee $DTB_SP_APP_ID \
    --scope $(az storage account show --name $STORAGE_ACCOUNT --query id -o tsv)

# Permitir que o secret scope (AKV-backed) do Databricks leia o Key Vault
az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee $(az ad sp list --display-name "AzureDatabricks" --query "[].{Id:id}" --output tsv) \
    --scope $KV_ID

# ------------------ Connection string do Event Hubs → Key Vault --------------
EVENTHUB_CONNECTION_STRING=$(az eventhubs namespace authorization-rule keys list \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $EVENTHUB_NAMESPACE \
    --name RootManageSharedAccessKey \
    --query primaryConnectionString \
    --output tsv)

az keyvault secret set --vault-name $KEY_VAULT --name "EventhubConnectionString" --value $EVENTHUB_CONNECTION_STRING

echo "[OK] Bootstrap concluído: SPNs criados, segredos gravados e papéis atribuídos."
