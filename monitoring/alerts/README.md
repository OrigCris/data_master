# Alertas — Azure Monitor

Regras de alerta que cobrem os pontos de falha mais prováveis do pipeline.
Definidas como código em [`alert-rules.bicep`](alert-rules.bicep) e ligadas ao
Action Group provisionado pelo módulo de observabilidade.

| Alerta | Sinal | Janela | Severidade | Por quê |
|---|---|---|---|---|
| `evh-sem-ingestao` | `IncomingMessages = 0` no Event Hubs | 30 min | 2 (warning) | Detecta produtor (Function App) parado ou SPN sem permissão de envio. |
| `func-falhas-execucao` | `Http5xx > 0` no Function App | 15 min | 1 (error) | Falhas de execução do gerador/produtor de eventos. |

## Deploy

```bash
az deployment group create -g rsgcjtecprd001 \
  -f monitoring/alerts/alert-rules.bicep \
  -p eventHubNamespaceId=<id-do-namespace> \
     functionAppId=<id-da-function> \
     actionGroupId=<id-do-action-group>
```

> O dashboard operacional (`../Monitor Case.json`) cobre as métricas de Event Hubs,
> Function App, Storage e Databricks. Os alertas acima fecham o ciclo
> *observar → notificar*, encaminhando para o e-mail do Action Group.
