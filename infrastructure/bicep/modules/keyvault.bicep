// Key Vault com RBAC (sem access policies) — segredos do SPN e do Event Hubs.
@description('Nome do Key Vault')
param name string
param location string
param tags object

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true       // RBAC, alinhado ao restante do projeto
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

output name string = kv.name
output id string = kv.id
output vaultUri string = kv.properties.vaultUri
