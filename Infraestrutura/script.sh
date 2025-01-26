#!/bin/bash

# Defina as variáveis
RESOURCE_GROUP="rgprd001"
LOCATION="brazilsouth"
STORAGE_ACCOUNT="stprd001"
EVENTHUB_NAMESPACE="evhnsprd001"
EVENTHUB_NAME="evh_clientes"
FUNCTION_APP="funcprd001"
PLAN_NAME="aspprd001"
KEY_VAULT="kvprd001"
SERVICE_PRINCIPAL_NAME="spnauth"

# Criação do Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Criação do Storage Account com suporte a ADLS Gen2
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS --kind StorageV2 --hns true

# Criação do Namespace e Event Hub
az eventhubs namespace create --resource-group $RESOURCE_GROUP --name $EVENTHUB_NAMESPACE --location $LOCATION
az eventhubs eventhub create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name $EVENTHUB_NAME

# Criação do Plano de Serviço de Aplicativo
az appservice plan create --name $PLAN_NAME --resource-group $RESOURCE_GROUP --sku B1 --is-linux

# Criação do Function App
az functionapp create --resource-group $RESOURCE_GROUP --consumption-plan-location $LOCATION --runtime python --runtime-version 3.8 --functions-version 3 --name $FUNCTION_APP --storage-account $STORAGE_ACCOUNT

# Criação do Key Vault
az keyvault create --name $KEY_VAULT --resource-group $RESOURCE_GROUP --location $LOCATION

# Criação do Service Principal e armazenando a senha no Key Vault
SP_DETAILS=$(az ad sp create-for-rbac --name $SERVICE_PRINCIPAL_NAME --skip-assignment)
SP_APP_ID=$(echo $SP_DETAILS | jq -r '.appId')
SP_SECRET=$(echo $SP_DETAILS | jq -r '.password')
TENANT_ID=$(echo $SP_DETAILS | jq -r '.tenant')

az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalAppId" --value $SP_APP_ID
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalSecret" --value $SP_SECRET
az keyvault secret set --vault-name $KEY_VAULT --name "ServicePrincipalTenantId" --value $TENANT_ID

# Criar uma Regra de Autorização para Enviar Mensagens no Event Hub
az eventhubs namespace authorization-rule create --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name MeuSendPolicy --rights Send

# Obter a Connection String da Regra de Autorização
EVENTHUB_CONN_STRING=$(az eventhubs namespace authorization-rule keys list --resource-group $RESOURCE_GROUP --namespace-name $EVENTHUB_NAMESPACE --name MeuSendPolicy --query primaryConnectionString -o tsv)

# Armazenar a Connection String no Key Vault
az keyvault secret set --vault-name $KEY_VAULT --name "EventHubSendConnectionString" --value $EVENTHUB_CONN_STRING

# Atribuir Permissões ao Service Principal para Acessar o Key Vault
az keyvault set-policy --name $KEY_VAULT --spn $SP_APP_ID --secret-permissions get list

# Configurar Variáveis de Ambiente na Function App para Usar a SPN
az functionapp config appsettings set --name $FUNCTION_APP --resource-group $RESOURCE_GROUP --settings \
AZURE_CLIENT_ID=$SP_APP_ID \
AZURE_CLIENT_SECRET=$SP_SECRET \
AZURE_TENANT_ID=$TENANT_ID

echo "Todos os recursos foram criados e configurados com sucesso!"