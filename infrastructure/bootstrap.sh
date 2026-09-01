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
#   - cria (ou reutiliza, rotacionando a credencial) a Service Principal consumidora
#     (Databricks → Event Hubs), com o mínimo de RBAC ('Azure Event Hubs Data
#     Receiver', no namespace). É **idempotente**: pode ser reexecutado com segurança.
#   - grava os segredos dessa SPN no Key Vault (lidos pelo secret scope do Databricks)
#   - aplica as **access policies** do Key Vault (operador → Set; SP "AzureDatabricks"
#     → Get/List), necessárias porque o AKV-backed secret scope do Databricks só
#     funciona com o modelo *access policy* (não com Azure RBAC)
#
# Autenticação por identidade (Entra ID), sem SAS keys:
#   - Produtor  : Managed Identity do Function App → 'Data Sender'  (papel dado pelo Bicep)
#   - Consumidor: SPN spn_dtb_consumer            → 'Data Receiver' (aqui)
#   - ADLS/UC   : Access Connector (MI)           → 'Storage Blob Data Contributor' (Bicep)
# Por isso a SPN consumidora NÃO recebe acesso ao storage (o UC usa o Access Connector).
#
# Pré-requisito: rode o Bicep ANTES (os recursos precisam já existir).
# Uso: az login && ./bootstrap.sh
# =============================================================================
set -euo pipefail
export MSYS_NO_PATHCONV=1
# ----------------------------- Variáveis -------------------------------------
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ACCOUNT_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

RESOURCE_GROUP="rsgcjtecprd001"
EVENTHUB_NAMESPACE="evhnscjtecprd001"
KEY_VAULT="akvcjtecprd001"

SPN_CONSUMER="spn_dtb_consumer"   # consome do Event Hubs (Databricks)

EVENTHUB_NS_ID="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.EventHub/namespaces/$EVENTHUB_NAMESPACE"

# ---- Access policy: operador pode gravar segredos no Key Vault (Set/Get/List) ----
# (o vault está no modelo access policy — ver keyvault.bicep)
az keyvault set-policy \
    --name $KEY_VAULT \
    --object-id $ACCOUNT_OBJECT_ID \
    --secret-permissions get list set

# --------- SPN consumidora (Databricks → Event Hubs), least privilege ---------
# Idempotente: se a SPN já existe, reutiliza a identidade e **rotaciona** a credencial
# (o segredo anterior não é recuperável, então geramos um novo e o regravamos no KV);
# se não existe, cria já com o único papel necessário, no escopo do namespace — sem
# Contributor e sem atribuição genérica no Resource Group.
EXISTING_APP_ID=$(az ad sp list --display-name "$SPN_CONSUMER" --query "[0].appId" -o tsv)
if [ -z "$EXISTING_APP_ID" ]; then
  # --query "[...]" -o tsv devolve os três campos separados por TAB numa linha; o
  # `read` os quebra sem depender de jq (o `az` é o único pré-requisito do script).
  read -r DTB_SP_APP_ID DTB_SP_SECRET DTB_TENANT_ID < <(az ad sp create-for-rbac \
      --name "$SPN_CONSUMER" \
      --role "Azure Event Hubs Data Receiver" \
      --scopes "$EVENTHUB_NS_ID" \
      --query "[appId,password,tenant]" -o tsv)
  echo "[+] SPN '$SPN_CONSUMER' criada (appId=$DTB_SP_APP_ID)"
else
  DTB_SP_APP_ID="$EXISTING_APP_ID"
  DTB_TENANT_ID=$(az account show --query tenantId -o tsv)
  DTB_SP_SECRET=$(az ad sp credential reset --id "$DTB_SP_APP_ID" --query password -o tsv)
  # garante o papel (idempotente — não falha se já existir)
  az role assignment create \
      --assignee "$DTB_SP_APP_ID" \
      --role "Azure Event Hubs Data Receiver" \
      --scope "$EVENTHUB_NS_ID" >/dev/null 2>&1 || true
  echo "[=] SPN '$SPN_CONSUMER' já existia (appId=$DTB_SP_APP_ID) — credencial rotacionada"
fi

az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalDTBAppId" --value $DTB_SP_APP_ID
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalDTBSecret" --value $DTB_SP_SECRET
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalDTBTenantId" --value $DTB_TENANT_ID

# Access policy para o secret scope (AKV-backed) do Databricks ler o Key Vault.
# A app first-party "AzureDatabricks" precisa de Get/List em secrets (modelo access
# policy — o AKV-backed scope não suporta RBAC no Key Vault).
DATABRICKS_SP_OBJECT_ID=$(az ad sp list --display-name "AzureDatabricks" --query "[0].id" -o tsv)
az keyvault set-policy \
    --name $KEY_VAULT \
    --object-id $DATABRICKS_SP_OBJECT_ID \
    --secret-permissions get list

echo "[OK] Bootstrap concluído: SPN consumidora criada (Data Receiver), segredos gravados, access policies aplicadas."
