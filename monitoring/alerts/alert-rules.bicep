// Regras de alerta (Azure Monitor) para a saúde do pipeline.
// Deploy independente do main.bicep (após os recursos existirem):
//   az deployment group create -g <rg> -f monitoring/alerts/alert-rules.bicep \
//     -p eventHubNamespaceId=<id> functionAppId=<id> actionGroupId=<id>
@description('Resource ID do namespace Event Hubs')
param eventHubNamespaceId string
@description('Resource ID do Function App')
param functionAppId string
@description('Resource ID do Action Group de destino')
param actionGroupId string
param location string = resourceGroup().location

// 1) Ingestão parada: nenhuma mensagem recebida no Event Hubs por 30 min.
resource ehNoIngestion 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'evh-sem-ingestao'
  location: 'global'
  properties: {
    severity: 2
    enabled: true
    scopes: [eventHubNamespaceId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT30M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'IncomingMessages'
          metricNamespace: 'Microsoft.EventHub/namespaces'
          metricName: 'IncomingMessages'
          operator: 'LessThanOrEqual'
          threshold: 0
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

// 2) Falhas na Function App: execuções com erro nos últimos 15 min.
resource funcFailures 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'func-falhas-execucao'
  location: 'global'
  properties: {
    severity: 1
    enabled: true
    scopes: [functionAppId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'Http5xx'
          metricNamespace: 'Microsoft.Web/sites'
          metricName: 'Http5xx'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

output configured array = [ehNoIngestion.name, funcFailures.name]
output noted string = location
