// Observabilidade: Log Analytics + Application Insights + Action Group (alertas).
@description('Nome do workspace Log Analytics')
param workspaceName string
@description('Nome do Action Group (destino dos alertas)')
param actionGroupName string
param location string
param tags object
@description('E-mail que recebe os alertas')
param alertEmail string = 'cristiano.tecnologia.data@hotmail.com'

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${workspaceName}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

resource ag 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'dmalerts'
    enabled: true
    emailReceivers: [
      {
        name: 'owner'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

output workspaceId string = law.id
output actionGroupId string = ag.id
output appInsightsConnectionString string = appi.properties.ConnectionString
