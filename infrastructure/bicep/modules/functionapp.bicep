// Function App (Linux, Python 3.11) com Managed Identity em plano Flex Consumption.
@description('Nome do Function App')
param name string
@description('Nome do plano Flex Consumption')
param planName string
@description('Storage Account de runtime da Function')
param storageAccountName string
param appInsightsConnectionString string
param location string
param tags object
@description('App settings de domínio (Event Hubs)')
param appSettings object

@description('Container de blobs onde o Flex Consumption guarda o pacote de deploy')
param deploymentContainerName string = 'deploymentpackage'

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

// Container dedicado ao pacote de deploy do Flex Consumption (precisa existir antes
// do site referenciá-lo).
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' existing = {
  parent: sa
  name: 'default'
}

resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: deploymentContainerName
  properties: { publicAccess: 'None' }
}

// Plano Flex Consumption (serverless): escala a zero, cobra por execução e não
// consome quota de VM dedicada. Cold start menor e concorrência por instância.
resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  tags: tags
  sku: { name: 'FC1', tier: 'FlexConsumption' }
  kind: 'functionapp'
  properties: { reserved: true }
}

// No Flex, o runtime (python 3.11) vai em functionAppConfig, não em linuxFxVersion;
// e não há Oryx via app setting — o build remoto do pacote é feito pelo próprio Flex.
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${sa.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${sa.listKeys().keys[0].value}'

var runtimeSettings = [
  { name: 'AzureWebJobsStorage', value: storageConnectionString }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
  // Referenciado por functionAppConfig.deployment.storage.authentication.
  { name: 'DEPLOYMENT_STORAGE_CONNECTION_STRING', value: storageConnectionString }
]

var domainSettings = [for k in items(appSettings): {
  name: k.key
  value: k.value
}]

resource func 'Microsoft.Web/sites@2024-04-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${sa.properties.primaryEndpoints.blob}${deploymentContainerName}'
          authentication: {
            type: 'StorageAccountConnectionString'
            storageAccountConnectionStringName: 'DEPLOYMENT_STORAGE_CONNECTION_STRING'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 40
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
    }
    siteConfig: {
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: concat(runtimeSettings, domainSettings)
    }
  }
  dependsOn: [ deploymentContainer ]
}

output name string = func.name
output principalId string = func.identity.principalId
