#!/bin/bash

# Defina as variáveis
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ACCOUNT_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
LOCATION="brazilsouth"

RESOURCE_GROUP="rsgcjprd001"

STORAGE_ACCOUNT="stacjprd001"
CONTAINER="cont-dt-mst"

EVENTHUB_NAMESPACE_FULLY="evhnscjprd001.servicebus.windows.net"
EVENTHUB_NAMESPACE="evhnscjprd001"
EVENTHUB_NAME_USER="evh_user_random"
EVENTHUB_NAME_USER_SCHEMA="evh_user_random_schema"

FUNCTION_APP="funccjprd001"
PLAN_NAME="aspcjprd001"

KEY_VAULT="akvcjprd001"
SPN_PRODUCER="spn_func_send"

SCHEMAREGISTRY_FQDN="evhnscjprd001.servicebus.windows.net"
SCHEMA_GROUP="SchemaFunctions"
SCHEMA_NAME="UserRandom"

DATABRICKS_WORKSPACE="dbwcjprd001"
DATABRICKS_PLAN="Premium"

############################################# GERANDO TODOS OS RECUROS #####################################################

# Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION
az group create --name $RESOURCE_GROUP_DTB --location $LOCATION

# Storage Account com suporte a ADLS Gen2
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS --kind StorageV2 --hns true

# Container e Pastas
az storage container create --name $CONTAINER --account-name $STORAGE_ACCOUNT --auth-mode login
az storage fs directory create --account-name $STORAGE_ACCOUNT --file-system $CONTAINER --name bronze
az storage fs directory create --account-name $STORAGE_ACCOUNT --file-system $CONTAINER --name silver
az storage fs directory create --account-name $STORAGE_ACCOUNT --file-system $CONTAINER --name gold

# Criação do Namespace e Event Hub com o SKU Basic
az eventhubs namespace create --resource-group $RESOURCE_GROUP --name $EVENTHUB_NAMESPACE --location $LOCATION --sku Standard
az eventhubs eventhub create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name $EVENTHUB_NAME_USER --cleanup-policy Delete --retention-time-in-hours 1 --partition-count 1
az eventhubs eventhub create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name $EVENTHUB_NAME_USER_SCHEMA --cleanup-policy Delete --retention-time-in-hours 1 --partition-count 1

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

##################################################### MANAGED IDENTITY ###########################################################

# Function App
FUNC_MANAGED_ID=$(az functionapp identity show --resource-group $RESOURCE_GROUP --name $FUNCTION_APP --query principalId -o tsv)

#####################################################    PERMISSOES    ###########################################################

az role assignment create \
    --role "Key Vault Secrets Officer" \
    --assignee-object-id $ACCOUNT_OBJECT_ID \
    --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

# Criação do Service Principal e armazenando a senha no Key Vault
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

# Dar acesso de envio para a SPN
az role assignment create \
  --assignee $SP_APP_ID \
  --role "Azure Event Hubs Data Sender" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.EventHub/namespaces/$EVENTHUB_NAMESPACE"
 
# Dar acesso de leitura ao AKV para o Function App
az role assignment create \
    --assignee $FUNC_MANAGED_ID \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

################################################### VARIAVEIS DE AMBIENTE ####################################################

# Configurar Variáveis de Ambiente na Function App (não para usar diretamente)
az functionapp config appsettings set --name $FUNCTION_APP --resource-group $RESOURCE_GROUP --settings \
    EVENTHUB_NAMESPACE_FULLY=$EVENTHUB_NAMESPACE_FULLY \
    EVENTHUB_NAME_USER=$EVENTHUB_NAME_USER \
    EVENTHUB_NAME_USER_SCHEMA=$EVENTHUB_NAME_USER_SCHEMA \
    SCHEMAREGISTRY_FQDN=$SCHEMAREGISTRY_FQDN \
    SCHEMA_GROUP=$SCHEMA_GROUP \
    SCHEMA_NAME=$SCHEMA_NAME