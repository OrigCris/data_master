// Storage ADLS Gen2 (HNS) + container + diretórios por camada (bronze/silver/gold).
@description('Nome do Storage Account')
param name string
@description('Nome do container (file system)')
param container string
param location string
param tags object

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true            // ADLS Gen2
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: sa
  name: 'default'
}

resource fs 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blob
  name: container
  properties: {
    publicAccess: 'None'
  }
}

output name string = sa.name
output id string = sa.id
output dfsEndpoint string = sa.properties.primaryEndpoints.dfs
