// Regras de alerta (Azure Monitor) para a saúde do pipeline.
// Provisionadas pelo main.bicep (módulo `alerts`). Também executável de forma
// independente, para manutenção/testes:
//   az deployment group create -g <rg> -f monitoring/alerts/alert-rules.bicep \
//     -p eventHubNamespaceId=<id> appInsightsId=<id> actionGroupId=<id>
@description('Resource ID do namespace Event Hubs')
param eventHubNamespaceId string
@description('Resource ID do Application Insights (telemetria da Function)')
param appInsightsId string
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

// 2) Falhas na Function App: exceções nas execuções nos últimos 15 min.
// A Function é uma TimerTrigger — uma falha é uma exceção Python na execução, não um
// HTTP 5xx. Por isso o sinal é a métrica `exceptions/count` do Application Insights
// (a telemetria de exceção do runtime), e não `Http5xx` do Microsoft.Web/sites.
resource funcFailures 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'func-falhas-execucao'
  location: 'global'
  properties: {
    severity: 1
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'FunctionExceptions'
          metricNamespace: 'microsoft.insights/components'
          metricName: 'exceptions/count'
          operator: 'GreaterThan'
          threshold: 0
          // exceptions/count só admite a agregação Count (contagem de exceções).
          timeAggregation: 'Count'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

output configured array = [ehNoIngestion.name, funcFailures.name]
output noted string = location
