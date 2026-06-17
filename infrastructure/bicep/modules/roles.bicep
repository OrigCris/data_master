// RBAC mínimo do pipeline (least privilege):
//  - Function App (MI)   → Key Vault Secrets User  (ler segredos do SPN)
//  - Access Connector    → Storage Blob Data Contributor (Unity Catalog managed location)
@description('Storage Account alvo do RBAC')
param storageAccountName string
@description('Key Vault alvo do RBAC')
param keyVaultName string
@description('PrincipalId da MI do Function App')
param functionPrincipalId string
@description('PrincipalId da MI do Access Connector do Databricks')
param accessConnectorPrincipalId string

// IDs de role built-in
var roleKeyVaultSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
var roleStorageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource funcKvSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, functionPrincipalId, roleKeyVaultSecretsUser)
  scope: kv
  properties: {
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
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
