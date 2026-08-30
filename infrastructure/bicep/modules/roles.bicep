// RBAC mínimo do pipeline (least privilege), por identidade:
//  - Function App (MI)  → Azure Event Hubs Data Sender   (produzir eventos)
//  - Access Connector   → Storage Blob Data Contributor  (managed location do Unity Catalog)
@description('Storage Account alvo do RBAC')
param storageAccountName string
@description('Namespace Event Hubs alvo do RBAC')
param eventHubNamespaceName string
@description('PrincipalId da MI do Function App')
param functionPrincipalId string
@description('PrincipalId da MI do Access Connector do Databricks')
param accessConnectorPrincipalId string

// IDs de role built-in
var roleEventHubsDataSender = '2b629674-e913-4c01-ae53-ef4638d8f975'
var roleStorageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource ehNamespace 'Microsoft.EventHub/namespaces@2024-01-01' existing = {
  name: eventHubNamespaceName
}

// Function App produz via Managed Identity — sem SAS keys, sem segredo no Key Vault.
resource funcEventHubSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ehNamespace.id, functionPrincipalId, roleEventHubsDataSender)
  scope: ehNamespace
  properties: {
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleEventHubsDataSender)
  }
}

resource acBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(sa.id, accessConnectorPrincipalId, roleStorageBlobDataContributor)
  scope: sa
  properties: {
    principalId: accessConnectorPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageBlobDataContributor)
  }
}
