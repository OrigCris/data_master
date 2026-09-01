# 13. DataViz e Observabilidade

A observabilidade combina **monitoramento operacional** (saúde do pipeline),
**observabilidade de dados** (comportamento dos datasets) e **dados analíticos**
(consumo de negócio).

## Stack
- **Azure Monitor / Log Analytics** — métricas e logs de todos os recursos.
- **Application Insights** — telemetria da Function App.
- **Action Group + Metric Alerts** — notificação proativa.
- Dashboard versionado em [`monitoring/Monitor Case.json`](../monitoring/Monitor%20Case.json).

## O que é monitorado

| Recurso | Métricas-chave | Por quê |
|---|---|---|
| Event Hubs | `IncomingMessages`, `OutgoingMessages` | Saúde da ingestão |
| Function App | execuções, exceções (App Insights), memória | Saúde do produtor |
| Storage | transações | Saúde do lake |
| Databricks | CPU/memória do cluster, duração dos jobs | Saúde do processamento |

## Alertas (como código)

Definidos em [`monitoring/alerts/alert-rules.bicep`](../monitoring/alerts/alert-rules.bicep):

| Alerta | Condição | Ação |
|---|---|---|
| `evh-sem-ingestao` | `IncomingMessages = 0` por 30 min | e-mail (Action Group) |
| `func-falhas-execucao` | `exceptions/count > 0` (App Insights) em 15 min | e-mail (Action Group) |

Esses dois fecham o ciclo **observar → notificar** para os pontos de falha mais
prováveis (produtor parado, identidade sem permissão de envio, exceção na execução).

## Observabilidade de dados (Silver)
Além da saúde de infraestrutura, o pipeline observa o **comportamento dos datasets**:

| Sinal | O que detecta | Onde |
|---|---|---|
| **Volume vs média móvel** | queda/pico anômalo de linhas (fora de `[0.7, 1.3] × média`) | `__dataset_metrics` |
| **Freshness** | dado mais velho que o limite (atraso na ingestão) | `__dataset_metrics` |
| **Quarentena (DLQ)** | eventos que violam o data contract (schema/campos) | `__quarantine` |

O volume e o freshness são registrados por [`run_observability`](../Databricks/lib/quality/observability.py)
a cada execução; a quarentena cresce quando um evento não respeita o contrato
(ver [Processamento](processing.md)). Monitorar a **contagem da `__quarantine`** e as
**anomalias de volume** transforma Data Quality em **Data Reliability**.

## Telemetria no código
- A Function App loga contagens de envio por hub (`extra={"counts": {...}}`).
- O notebook Bronze imprime as **linhas gravadas no run** (via `numOutputRows` do commit
  Delta) e o total acumulado — no `AvailableNow`, o `numInputRows` do stream pode vir 0
  mesmo com dados processados, então o commit transacional do Delta é a fonte de verdade.
- A Data Quality grava resultados em `__dq_results`; a observabilidade grava métricas
  em `__dataset_metrics`; ambos servem de auditoria histórica.

## DataViz (negócio)
As tabelas `g_dm_callcenter.visao_*` alimentam dashboards de BI (Power BI / Grafana
sobre o SQL Warehouse do Databricks). O clustering por período garante consultas
baratas. Evoluções (dashboards versionados) no [Roadmap](roadmap.md).

---

[← Anterior: Analytics](analytics.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Governança →](governance.md)
