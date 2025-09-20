#!/bin/bash

# Defina as variáveis
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ACCOUNT_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
LOCATION="brazilsouth"
RESOURCE_GROUP="rsgcjtecprd001"

# Storage account e container
STORAGE_ACCOUNT="stacjtecprd001"
CONTAINER="ctcjtecprd001"

# Eventhub Namespace e instâncias
EVENTHUB_NAMESPACE_FQDN="evhnscjtecprd001.servicebus.windows.net"
EVENTHUB_NAMESPACE="evhnscjtecprd001"
EVENTHUB_NAME_URA="evh_cj_tec_ura"
EVENTHUB_NAME_CALLS="evh_cj_tec_calls"
EVENTHUB_NAME_SURVEYS="evh_cj_tec_surveys"

FUNCTION_APP="funccjtecprd001"
PLAN_NAME="aspcjtecprd001"

KEY_VAULT_URL="https://akvcjtecprd001.vault.azure.net/"
KEY_VAULT="akvcjtecprd001"
SPN_PRODUCER="spn_func_send"
SPN_CONSUMER="spn_dtb_consumer"

DATABRICKS_WORKSPACE="dbwcjtecprd001"
DATABRICKS_PLAN="Premium"

### Criando todos os recursos necessários

# Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Storage Account com suporte a ADLS Gen2
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS --kind StorageV2 --hns true

# Container e Pastas
az storage container create --name $CONTAINER --account-name $STORAGE_ACCOUNT --auth-mode login
az storage fs directory create --account-name $STORAGE_ACCOUNT --file-system $CONTAINER --name bronze
az storage fs directory create --account-name $STORAGE_ACCOUNT --file-system $CONTAINER --name silver
az storage fs directory create --account-name $STORAGE_ACCOUNT --file-system $CONTAINER --name gold

# Criação do Namespace e Event Hub com o SKU Basic
az eventhubs namespace create --resource-group $RESOURCE_GROUP --name $EVENTHUB_NAMESPACE --location $LOCATION --sku Standard
az eventhubs eventhub create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name $EVENTHUB_NAME_URA --cleanup-policy Delete --retention-time-in-hours 1 --partition-count 1
az eventhubs eventhub create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name $EVENTHUB_NAME_CALLS --cleanup-policy Delete --retention-time-in-hours 1 --partition-count 1
az eventhubs eventhub create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name $EVENTHUB_NAME_SURVEYS --cleanup-policy Delete --retention-time-in-hours 1 --partition-count 1

# Criação do Plano de Serviço de Aplicativo
az appservice plan create --name $PLAN_NAME --resource-group $RESOURCE_GROUP --sku B1 --is-linux

# Criação do Function App e habilitação da Managed Identity
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP \
    --storage-account $STORAGE_ACCOUNT \
    --plan $PLAN_NAME \
    --runtime "python" \
    --runtime-version "3.11" \
    --os-type "Linux" \
    --functions-version 4 \
    --assign-identity \
    --disable-app-insights

# Criação do Key Vault
az keyvault create --name $KEY_VAULT --resource-group $RESOURCE_GROUP --location $LOCATION

# Databricks Workspace
az config set extension.use_dynamic_install=yes_without_prompt
az databricks workspace create --name $DATABRICKS_WORKSPACE \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku $DATABRICKS_PLAN

AC_PRINCIPAL_ID=$(
  az databricks access-connector create \
    --resource-group $RESOURCE_GROUP \
    --name ac-databricks-uc \
    --location $LOCATION \
    --identity-type SystemAssigned \
    --query identity.principalId -o tsv
)

az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee-object-id $AC_PRINCIPAL_ID \
  --scope $(az storage account show -n $STORAGE_ACCOUNT -g $RESOURCE_GROUP --query id -o tsv)

##################################################### MANAGED IDENTITY ###########################################################

# Function App
FUNC_MANAGED_ID=$(az functionapp identity show --resource-group $RESOURCE_GROUP --name $FUNCTION_APP --query principalId -o tsv)

#####################################################    PERMISSOES    ###########################################################

az role assignment create \
    --role "Key Vault Secrets Officer" \
    --assignee-object-id $ACCOUNT_OBJECT_ID \
    --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

# Criação do Service Principal para uso da função e armazenando a senha no Key Vault
SP_DETAILS=$(az ad sp create-for-rbac --name $SPN_PRODUCER --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP)
SP_APP_ID=$(echo $SP_DETAILS | jq -r '.appId')
SP_SECRET=$(echo $SP_DETAILS | jq -r '.password')
TENANT_ID=$(echo $SP_DETAILS | jq -r '.tenant')

az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalAppId" --value $SP_APP_ID
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalSecret" --value $SP_SECRET
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalTenantId" --value $TENANT_ID

# Atribuir Permissões ao Service Principal para Acessar o Key Vault
az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee $SP_APP_ID \
    --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

# Dar acesso de envio ao EventHub para a SPN
az role assignment create \
  --assignee $SP_APP_ID \
  --role "Azure Event Hubs Data Sender" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.EventHub/namespaces/$EVENTHUB_NAMESPACE"

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

# Dar acesso de leitura ao AKV para o Function App (usando o ManagedIdentity)
az role assignment create \
    --assignee $FUNC_MANAGED_ID \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $(az ad sp list --display-name "AzureDatabricks" --query "[].{Id:id}" --output tsv) \
  --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

################################################### VARIAVEIS DE AMBIENTE ####################################################

# Obter o Connection String do Event Hub
EVENTHUB_CONNECTION_STRING=$(az eventhubs namespace authorization-rule keys list \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $EVENTHUB_NAMESPACE \
    --name RootManageSharedAccessKey \
    --query primaryConnectionString \
    --output tsv)

# Armazenar o Connection String no Key Vault
az keyvault secret set --vault-name $KEY_VAULT --name "EventhubConnectionString" --value $EVENTHUB_CONNECTION_STRING

# Configurar Variáveis de Ambiente na Function App (não para usar diretamente)
az functionapp config appsettings set --name $FUNCTION_APP --resource-group $RESOURCE_GROUP --settings \
    EVENTHUB_NAMESPACE_FQDN=$EVENTHUB_NAMESPACE_FQDN \
    EH_NAME_URA=$EVENTHUB_NAME_URA \
    EH_NAME_CALLS=$EVENTHUB_NAME_CALLS \
    EH_NAME_SURVEYS=$EVENTHUB_NAME_SURVEYS \
    KV_URL=$KEY_VAULT_URL \
    KV_SECRET_SPN_CLIENT_ID="ServicePrincipalAppId" \
    KV_SECRET_SPN_TENANT_ID="ServicePrincipalTenantId" \
    KV_SECRET_SPN_CLIENT_SECRET="ServicePrincipalSecret"