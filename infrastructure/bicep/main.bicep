// =============================================================================
// main.bicep — Orquestrador da infraestrutura do Data Master (Azure)
//
// Espelha a ideia de "componentização por stacks" do case de referência, porém
// com Bicep modular e idempotente. Cada domínio é um módulo isolado em ./modules,
// o que permite revisar, versionar e fazer `what-if` por componente.
//
// Escopo: Resource Group. Deploy:
//   az deployment group create -g <rg> \
//     -f infrastructure/bicep/main.bicep \
//     -p infrastructure/bicep/params/prd.bicepparam
//
// Observação de fronteira: a criação dos Service Principals (Entra ID) e o seed
// de secrets no Key Vault permanecem no bootstrap (`scripts`), pois exigem
// Microsoft Graph e segredos rotativos — fora do escopo declarativo do ARM.
// =============================================================================

targetScope = 'resourceGroup'

@description('Prefixo curto de nomenclatura, ex.: cjtecprd001')
param namePrefix string

@description('Região do Azure')
param location string = resourceGroup().location

@description('Tags aplicadas a todos os recursos')
param tags object = {
  project: 'data-master'
  domain: 'callcenter'
  env: 'prd'
  managedBy: 'bicep'
}

// ----------------------------- Storage (ADLS Gen2) ---------------------------
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: 'sta${namePrefix}'
    container: 'ct${namePrefix}'
    location: location
    tags: tags
  }
}

// ------------------------------- Event Hubs ----------------------------------
module eventhub 'modules/eventhub.bicep' = {
  name: 'eventhub'
  params: {
    namespaceName: 'evhns${namePrefix}'
    location: location
    tags: tags
    hubs: [
      'evh_cj_tec_ura'
      'evh_cj_tec_calls'
      'evh_cj_tec_surveys'
    ]
  }
}

// -------------------------------- Key Vault ----------------------------------
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    name: 'akv${namePrefix}'
    location: location
    tags: tags
  }
}

// ------------------------- Observabilidade (Azure Monitor) -------------------
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    workspaceName: 'log${namePrefix}'
    actionGroupName: 'ag${namePrefix}'
    location: location
    tags: tags
  }
}

// ------------------------------ Function App ---------------------------------
module functionApp 'modules/functionapp.bicep' = {
  name: 'functionapp'
  params: {
    name: 'func${namePrefix}'
    planName: 'asp${namePrefix}'
    storageAccountName: storage.outputs.name
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    location: location
    tags: tags
    appSettings: {
      EVENTHUB_NAMESPACE_FQDN: eventhub.outputs.namespaceFqdn
      EH_NAME_URA: 'evh_cj_tec_ura'
      EH_NAME_CALLS: 'evh_cj_tec_calls'
      EH_NAME_SURVEYS: 'evh_cj_tec_surveys'
      KV_URL: keyvault.outputs.vaultUri
      KV_SECRET_SPN_CLIENT_ID: 'ServicePrincipalAppId'
      KV_SECRET_SPN_TENANT_ID: 'ServicePrincipalTenantId'
      KV_SECRET_SPN_CLIENT_SECRET: 'ServicePrincipalSecret'
    }
  }
}

// ------------------------------- Databricks ----------------------------------
module databricks 'modules/databricks.bicep' = {
  name: 'databricks'
  params: {
    workspaceName: 'dbw${namePrefix}'
    accessConnectorName: 'ac-databricks-uc'
    location: location
    tags: tags
  }
}

// --------------------------------- RBAC --------------------------------------
module roles 'modules/roles.bicep' = {
  name: 'roles'
  params: {
    storageAccountName: storage.outputs.name
    keyVaultName: keyvault.outputs.name
    functionPrincipalId: functionApp.outputs.principalId
    accessConnectorPrincipalId: databricks.outputs.accessConnectorPrincipalId
  }
}

output storageAccount string = storage.outputs.name
output eventHubNamespaceFqdn string = eventhub.outputs.namespaceFqdn
output keyVaultUri string = keyvault.outputs.vaultUri
output functionApp string = functionApp.outputs.name
output databricksWorkspaceUrl string = databricks.outputs.workspaceUrl
