#!/bin/bash

# Defina as variáveis
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RESOURCE_GROUP="rsgcjprd001"
LOCATION="brazilsouth"
STORAGE_ACCOUNT="stacjprd001"
EVENTHUB_NAMESPACE="evhnscjprd001"
EVENTHUB_NAME="evh_neg_prod"
FUNCTION_APP="funccjprd001"
PLAN_NAME="aspcjprd001"
KEY_VAULT="akvcjprd001"
SERVICE_PRINCIPAL_NAME="spn_func_send"
ACCOUNT_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

# Criação do Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Criação do Storage Account com suporte a ADLS Gen2
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS --kind StorageV2 --hns true

# Criação do Namespace e Event Hub com o SKU Basic
az eventhubs namespace create --resource-group $RESOURCE_GROUP --name $EVENTHUB_NAMESPACE --location $LOCATION --sku Basic
az eventhubs eventhub create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name $EVENTHUB_NAME --cleanup-policy Delete --retention-time-in-hours 1

# Criação do Plano de Serviço de Aplicativo
az appservice plan create --name $PLAN_NAME --resource-group $RESOURCE_GROUP --sku B1 --is-linux

# Criação do Function App
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP \
    --storage-account $STORAGE_ACCOUNT \
    --plan $PLAN_NAME \
    --runtime "python" \
    --runtime-version "3.11" \
    --os-type "Linux" \
    --functions-version 4 \
    --disable-app-insights

# Criação do Key Vault
az keyvault create --name $KEY_VAULT --resource-group $RESOURCE_GROUP --location $LOCATION

# Criação do Service Principal e armazenando a senha no Key Vault
SP_DETAILS=$(az ad sp create-for-rbac --name $SERVICE_PRINCIPAL_NAME --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP)
SP_APP_ID=$(echo $SP_DETAILS | jq -r '.appId')
SP_SECRET=$(echo $SP_DETAILS | jq -r '.password')
TENANT_ID=$(echo $SP_DETAILS | jq -r '.tenant')

az role assignment create \
    --role "Key Vault Secrets Officer" \
    --assignee-object-id $ACCOUNT_OBJECT_ID \
    --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalAppId" --value $SP_APP_ID
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalSecret" --value $SP_SECRET
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalTenantId" --value $TENANT_ID

# Criar uma Regra de Autorização para Enviar Mensagens no Event Hub
az eventhubs namespace authorization-rule create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name PermissaoEnviar --rights Send

# Obter a Connection String da Regra de Autorização (não armazenar no Key Vault)
EVENTHUB_CONN_STRING=$(az eventhubs namespace authorization-rule keys list --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name PermissaoEnviar --query primaryConnectionString -o tsv)

# Atribuir Permissões ao Service Principal para Acessar o Key Vault
az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee $SP_APP_ID \
    --scope $(az keyvault show --name $KEY_VAULT --query id -o tsv)

# Configurar Variáveis de Ambiente na Function App para Usar a SPN e a Connection String
az functionapp config appsettings set --name $FUNCTION_APP --resource-group $RESOURCE_GROUP --settings \
    AZURE_CLIENT_ID=$SP_APP_ID \
    AZURE_CLIENT_SECRET=$SP_SECRET \
    AZURE_TENANT_ID=$TENANT_ID \
    EVENTHUB_CONN_STRING=$EVENTHUB_CONN_STRING

echo "Todos os recursos foram criados e configurados com sucesso!"
