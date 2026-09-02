// =============================================================================
// main.bicep — Orquestrador da infraestrutura do Data Master (Azure)
//
// Infraestrutura modular e idempotente: cada domínio é um módulo isolado em
// ./modules, o que permite revisar, versionar e fazer `what-if` por componente.
//
// Escopo: Resource Group. Deploy:
//   az deployment group create -g <rg> \
//     -f infrastructure/bicep/main.bicep \
//     -p infrastructure/bicep/params/prd.bicepparam
//
// Observação de fronteira: a criação da Service Principal consumidora (Entra ID) e o
// seed de secrets no Key Vault ficam no `dm setup-spn`, pois exigem Microsoft Graph e
// segredos rotativos — fora do escopo declarativo do ARM. O produtor usa a Managed
// Identity do Function App (papel Data Sender atribuído aqui, via RBAC).
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

@description('E-mail de destino dos alertas (Action Group) — configurável por parâmetro')
param alertEmail string

// Nomes dos Event Hubs (URA/Calls/Surveys) — usados pelo namespace e pelo alerta de
// "sem ingestão" por hub (dimensão EntityName), evitando hardcode em dois lugares.
var eventHubNames = [
  'evh_cj_tec_ura'
  'evh_cj_tec_calls'
  'evh_cj_tec_surveys'
]

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
    hubs: eventHubNames
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

// ------------------------- Observabilidade — núcleo (Azure Monitor) ----------
// Log Analytics + App Insights + Action Group. Criado cedo: a Function App consome a
// connection string do App Insights. Alertas e workbook são módulos à parte, deployados
// depois que Event Hubs/Function/Databricks existem (precisam dos ids deles).
module monitoring 'modules/monitoring/core.bicep' = {
  name: 'monitoring'
  params: {
    workspaceName: 'log${namePrefix}'
    actionGroupName: 'ag${namePrefix}'
    alertEmail: alertEmail
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
    eventHubNamespaceName: eventhub.outputs.namespaceName
    functionPrincipalId: functionApp.outputs.principalId
    accessConnectorPrincipalId: databricks.outputs.accessConnectorPrincipalId
  }
}

// ------------------------------ Alertas (Azure Monitor) ----------------------
// Regras por severidade (crítico/operacional/warning). Thresholds nos defaults do
// módulo (parametrizáveis). Deployadas aqui pois dependem dos ids de Event Hubs e
// Application Insights.
module alerts 'modules/monitoring/alert-rules.bicep' = {
  name: 'alerts'
  params: {
    eventHubNamespaceId: eventhub.outputs.namespaceId
    appInsightsId: monitoring.outputs.appInsightsId
    actionGroupId: monitoring.outputs.actionGroupId
    eventHubNames: eventHubNames
  }
}

// ------------------------------ Workbook (Azure Monitor) ---------------------
// Workbook operacional da jornada do dado. Recebe os ids reais dos recursos por
// parâmetro (o template usa placeholders) — sem id de ambiente hardcoded.
module workbook 'modules/monitoring/workbook.bicep' = {
  name: 'workbook'
  params: {
    location: location
    tags: tags
    logAnalyticsId: monitoring.outputs.workspaceId
    appInsightsId: monitoring.outputs.appInsightsId
    eventHubNamespaceId: eventhub.outputs.namespaceId
    databricksWorkspaceUrl: databricks.outputs.workspaceUrl
  }
}

output storageAccount string = storage.outputs.name
output eventHubNamespaceFqdn string = eventhub.outputs.namespaceFqdn
output keyVaultUri string = keyvault.outputs.vaultUri
output functionApp string = functionApp.outputs.name
output databricksWorkspaceUrl string = databricks.outputs.workspaceUrl

// IDs úteis para redeployar os módulos de observabilidade isoladamente, se preciso.
output eventHubNamespaceId string = eventhub.outputs.namespaceId
output appInsightsId string = monitoring.outputs.appInsightsId
output actionGroupId string = monitoring.outputs.actionGroupId
