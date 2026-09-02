// Azure Workbook operacional — jornada do dado. O template (workbook.json) traz
// placeholders que são substituídos pelos resource ids/urls reais dos módulos em
// deploy-time — nenhum id de ambiente fica hardcoded no repositório.
@description('Nome de exibição do workbook')
param workbookDisplayName string = 'Data Master — Observabilidade'
param location string
param tags object
@description('Resource ID do Log Analytics (scope/fallback do workbook)')
param logAnalyticsId string
@description('Resource ID do Application Insights (telemetria da Function)')
param appInsightsId string
@description('Resource ID do namespace Event Hubs')
param eventHubNamespaceId string
@description('URL do workspace Databricks (links para a observabilidade de jobs/dados)')
param databricksWorkspaceUrl string

var serialized = replace(
  replace(
    replace(
      replace(loadTextContent('workbook.json'), '__APPINSIGHTS_ID__', appInsightsId),
      '__EVENTHUB_ID__', eventHubNamespaceId
    ),
    '__LAW_ID__', logAnalyticsId
  ),
  '__DATABRICKS_URL__', databricksWorkspaceUrl
)

resource workbook 'Microsoft.Insights/workbooks@2023-06-01' = {
  // Nome do workbook é um GUID determinístico por Resource Group (idempotente).
  name: guid(resourceGroup().id, 'dm-observability-workbook')
  location: location
  tags: tags
  kind: 'shared'
  properties: {
    displayName: workbookDisplayName
    serializedData: serialized
    category: 'workbook'
    sourceId: logAnalyticsId
    version: '1.0'
  }
}

output workbookId string = workbook.id
