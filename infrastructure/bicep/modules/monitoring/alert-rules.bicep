// Regras de alerta (Azure Monitor) da saúde do pipeline, provisionadas pelo main.bicep.
// Divisão por severidade — nem toda anomalia é incidente:
//   Crítico     (sev 1): falha que exige ação (exceção da Function, ServerErrors do EH)
//   Operacional (sev 2): degradação de operação (sem ingestão, throttling)
//   Warning     (sev 3): comportamento anômalo a observar (duração acima do esperado)
// Os thresholds são parâmetros — sem números mágicos espalhados. A observabilidade de
// DADOS (volume/freshness/qualidade) vive nas tabelas Delta e no gate do pipeline
// (raise_if_critical_failed), não aqui: uma falha crítica de dados aparece como falha
// do job Databricks.
@description('Resource ID do namespace Event Hubs')
param eventHubNamespaceId string
@description('Resource ID do Application Insights (telemetria da Function)')
param appInsightsId string
@description('Resource ID do Action Group de destino')
param actionGroupId string
@description('Nomes dos Event Hubs — o alerta de "sem ingestão" avalia cada um (dimensão EntityName)')
param eventHubNames array

@description('Exceções da Function acima disto disparam Crítico')
param thresholdExceptions int = 0
@description('ServerErrors do Event Hubs acima disto disparam Crítico')
param thresholdServerErrors int = 0
@description('ThrottledRequests do Event Hubs acima disto disparam Operacional')
param thresholdThrottledRequests int = 0
@description('Duração média de execução (ms) acima disto dispara Warning')
param thresholdRequestDurationMs int = 60000
@description('Janela sem ingestão que dispara Operacional (ISO8601)')
param ingestionWindowSize string = 'PT30M'
@description('Frequência de avaliação dos alertas (ISO8601)')
param evaluationFrequency string = 'PT5M'

var sevCritical = 1
var sevOperational = 2
var sevWarning = 3

// ------------------------------- Crítico ------------------------------------- //
// A Function é TimerTrigger: uma falha é uma exceção Python na execução, não um HTTP
// 5xx. O sinal é `exceptions/count` do Application Insights (só admite agregação Count).
resource funcExceptions 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'crit-func-excecao'
  location: 'global'
  properties: {
    severity: sevCritical
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: evaluationFrequency
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'FunctionExceptions'
          metricNamespace: 'microsoft.insights/components'
          metricName: 'exceptions/count'
          operator: 'GreaterThan'
          threshold: thresholdExceptions
          timeAggregation: 'Count'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

// Erros do lado do serviço no Event Hubs (rejeição/indisponibilidade da ingestão).
resource ehServerErrors 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'crit-evh-server-errors'
  location: 'global'
  properties: {
    severity: sevCritical
    enabled: true
    scopes: [eventHubNamespaceId]
    evaluationFrequency: evaluationFrequency
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'ServerErrors'
          metricNamespace: 'Microsoft.EventHub/namespaces'
          metricName: 'ServerErrors'
          operator: 'GreaterThan'
          threshold: thresholdServerErrors
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

// ----------------------------- Operacional ----------------------------------- //
// Sem ingestão POR HUB: a dimensão EntityName faz o alerta avaliar cada Event Hub
// (URA/Calls/Surveys) separadamente e disparar por hub — se só a URA para, o alerta
// dispara, mesmo com Calls/Surveys ainda recebendo (um alerta namespace-wide não pegaria).
resource ehNoIngestion 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'oper-evh-sem-ingestao'
  location: 'global'
  properties: {
    severity: sevOperational
    enabled: true
    scopes: [eventHubNamespaceId]
    evaluationFrequency: evaluationFrequency
    windowSize: ingestionWindowSize
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
          dimensions: [
            {
              name: 'EntityName'
              operator: 'Include'
              values: eventHubNames
            }
          ]
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

// Throttling: o namespace está batendo no limite de throughput units.
resource ehThrottling 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'oper-evh-throttling'
  location: 'global'
  properties: {
    severity: sevOperational
    enabled: true
    scopes: [eventHubNamespaceId]
    evaluationFrequency: evaluationFrequency
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'ThrottledRequests'
          metricNamespace: 'Microsoft.EventHub/namespaces'
          metricName: 'ThrottledRequests'
          operator: 'GreaterThan'
          threshold: thresholdThrottledRequests
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

// ------------------------------- Warning ------------------------------------- //
// Duração média de execução acima do esperado — anomalia a observar, não incidente.
resource funcDuration 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'warn-func-duracao'
  location: 'global'
  properties: {
    severity: sevWarning
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: evaluationFrequency
    windowSize: 'PT30M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'RequestDuration'
          metricNamespace: 'microsoft.insights/components'
          metricName: 'requests/duration'
          operator: 'GreaterThan'
          threshold: thresholdRequestDurationMs
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroupId }]
  }
}

output configured array = [
  funcExceptions.name
  ehServerErrors.name
  ehNoIngestion.name
  ehThrottling.name
  funcDuration.name
]
