# Alertas — Azure Monitor

Regras de alerta que cobrem os pontos de falha mais prováveis do pipeline.
Definidas como código em [`alert-rules.bicep`](alert-rules.bicep) e ligadas ao
Action Group provisionado pelo módulo de observabilidade.

| Alerta | Sinal | Janela | Severidade | Por quê |
|---|---|---|---|---|
| `evh-sem-ingestao` | `IncomingMessages = 0` no Event Hubs | 30 min | 2 (warning) | Detecta produtor (Function App) parado ou MI sem permissão de envio. |
| `func-falhas-execucao` | `exceptions/count > 0` no Application Insights | 15 min | 1 (error) | Exceção na execução da Function (TimerTrigger). |

> A Function é uma **TimerTrigger**: uma falha é uma **exceção** na execução, não um
> HTTP 5xx. Por isso o alerta observa a métrica `exceptions/count` do Application
> Insights, não `Http5xx` do Function App.

## Deploy

```bash
az deployment group create -g rsgcjtecprd001 \
  -f monitoring/alerts/alert-rules.bicep \
  -p eventHubNamespaceId=<id-do-namespace> \
     appInsightsId=<id-do-application-insights> \
     actionGroupId=<id-do-action-group>
```

> O dashboard operacional (`../Monitor Case.json`) cobre as métricas de Event Hubs,
> Function App, Storage e Databricks. Os alertas acima fecham o ciclo
> *observar → notificar*, encaminhando para o e-mail do Action Group.
