// Function App (Linux, Python 3.11) com Managed Identity + App Service Plan.
@description('Nome do Function App')
param name string
@description('Nome do App Service Plan')
param planName string
@description('Storage Account de runtime da Function')
param storageAccountName string
param appInsightsConnectionString string
param location string
param tags object
@description('App settings de domínio (Event Hubs / Key Vault)')
param appSettings object

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  sku: { name: 'B1', tier: 'Basic' }
  kind: 'linux'
  properties: { reserved: true }
}

// Settings de runtime que dependem de valores em tempo de deploy (listKeys) ficam
// num array literal; os settings de domínio vêm do parâmetro via for-expression.
var runtimeSettings = [
  { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
  { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
  { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${sa.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${sa.listKeys().keys[0].value}' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
]

var domainSettings = [for k in items(appSettings): {
  name: k.key
  value: k.value
}]

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: concat(runtimeSettings, domainSettings)
    }
  }
}

output name string = func.name
output principalId string = func.identity.principalId
