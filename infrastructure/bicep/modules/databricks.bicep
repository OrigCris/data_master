// Databricks Workspace (Premium) + Access Connector (Managed Identity p/ Unity Catalog).
@description('Nome do workspace Databricks')
param workspaceName string
@description('Nome do Access Connector usado pelo Unity Catalog')
param accessConnectorName string
param location string
param tags object

var managedRgName = 'mrg-${workspaceName}'

resource ac 'Microsoft.Databricks/accessConnectors@2024-05-01' = {
  name: accessConnectorName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
}

resource workspace 'Microsoft.Databricks/workspaces@2024-05-01' = {
  name: workspaceName
  location: location
  tags: tags
  sku: { name: 'premium' }
  properties: {
    managedResourceGroupId: subscriptionResourceId('Microsoft.Resources/resourceGroups', managedRgName)
  }
}

output workspaceUrl string = 'https://${workspace.properties.workspaceUrl}'
output accessConnectorPrincipalId string = ac.identity.principalId
