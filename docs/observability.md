# 13. DataViz e Observabilidade

A observabilidade combina **monitoramento operacional** (saúde do pipeline) e
**dados analíticos** (consumo de negócio).

## Stack
- **Azure Monitor / Log Analytics** — métricas e logs de todos os recursos.
- **Application Insights** — telemetria da Function App.
- **Action Group + Metric Alerts** — notificação proativa.
- Dashboard versionado em [`monitoring/Monitor Case.json`](../monitoring/Monitor%20Case.json).

## O que é monitorado

| Recurso | Métricas-chave | Por quê |
|---|---|---|
| Event Hubs | `IncomingMessages`, `OutgoingMessages` | Saúde da ingestão |
| Function App | execuções, `Http5xx`, memória | Saúde do produtor |
| Storage | transações | Saúde do lake |
| Databricks | CPU/memória do cluster, duração dos jobs | Saúde do processamento |

## Alertas (como código)

Definidos em [`monitoring/alerts/alert-rules.bicep`](../monitoring/alerts/alert-rules.bicep):

| Alerta | Condição | Ação |
|---|---|---|
| `evh-sem-ingestao` | `IncomingMessages = 0` por 30 min | e-mail (Action Group) |
| `func-falhas-execucao` | `Http5xx > 0` em 15 min | e-mail (Action Group) |

Esses dois fecham o ciclo **observar → notificar** para os pontos de falha mais
prováveis (produtor parado, SPN sem permissão, falha de execução).

## Telemetria no código
- A Function App loga contagens de envio por hub (`extra={"counts": {...}}`).
- O notebook Bronze imprime `numInputRows`/`batchDuration` do último batch.
- A Data Quality grava resultados em `__dq_results` para auditoria histórica.

## DataViz (negócio)
As tabelas `g_dm_callcenter.visao_*` alimentam dashboards de BI (Power BI / Grafana
sobre o SQL Warehouse do Databricks). O clustering por período garante consultas
baratas. Evoluções (dashboards versionados) no [Roadmap](roadmap.md).

---

[← Anterior: Analytics](analytics.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Governança →](governance.md)
