// Key Vault no modelo **Vault access policy** (não RBAC).
//
// Motivo: o **Azure Key Vault-backed secret scope** do Databricks só funciona com o
// modelo de *access policy* — ele não suporta o modelo Azure RBAC no Key Vault. Como o
// Databricks lê os segredos da SPN consumidora por um AKV-backed scope, o vault precisa
// estar nesse modelo. As policies (operador → Set; SP "AzureDatabricks" → Get/List) são
// aplicadas pelo bootstrap, pois dependem de object ids resolvidos via Microsoft Graph.
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
    enableRbacAuthorization: false      // access policy: exigido pelo AKV-backed scope
    accessPolicies: []                  // populadas pelo bootstrap (Set / Get-List)
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

output name string = kv.name
output id string = kv.id
output vaultUri string = kv.properties.vaultUri
