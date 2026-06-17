// Event Hubs Namespace (Standard) + hubs de ingestão (URA, Calls, Surveys).
@description('Nome do namespace Event Hubs')
param namespaceName string
param location string
param tags object
@description('Lista de Event Hubs a criar')
param hubs array
@description('Retenção em horas (demo: 1h é suficiente para trigger-once)')
param retentionHours int = 1
@description('Partições por hub')
param partitionCount int = 1

resource ns 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: namespaceName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    minimumTlsVersion: '1.2'
    disableLocalAuth: false
  }
}

resource eh 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = [for h in hubs: {
  parent: ns
  name: h
  properties: {
    messageRetentionInDays: 1
    partitionCount: partitionCount
    retentionDescription: {
      cleanupPolicy: 'Delete'
      retentionTimeInHours: retentionHours
    }
  }
}]

output namespaceName string = ns.name
output namespaceFqdn string = '${ns.name}.servicebus.windows.net'
output namespaceId string = ns.id
