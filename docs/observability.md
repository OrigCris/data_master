# 13. DataViz e Observabilidade

A observabilidade tem **dois planos**, cada um na ferramenta mais apropriada:

- **Infraestrutura / operação → Azure Monitor.** Saúde da ingestão (Event Hubs) e do
  produtor (Function App): métricas, logs, alertas e um **Azure Workbook** — tudo por
  IaC, provisionado junto da solução pelo `dm provision`.
- **Dados → tabelas Delta no Databricks.** Contrato, qualidade e observabilidade dos
  datasets (volume/freshness) vivem em tabelas Delta, consultáveis no Databricks. **Não
  há export automático dessas tabelas para o Azure Monitor** — integrá-las exigiria
  arquitetura nova, então não é feito.

## Stack de infraestrutura (Azure Monitor — IaC)

Provisionado pelo `dm provision` (Bicep, em `infrastructure/bicep/modules/monitoring/`):

- **Log Analytics Workspace** — métricas e logs.
- **Application Insights** — telemetria da Function App (execuções, exceções, duração).
- **Action Group** — notificação por e-mail (destinatário via parâmetro `alertEmail`,
  sem hardcode).
- **Alert Rules** — metric alerts por severidade ([`alert-rules.bicep`](../infrastructure/bicep/modules/monitoring/alert-rules.bicep)).
- **Azure Workbook** — dashboard operacional da jornada do dado ([`workbook.bicep`](../infrastructure/bicep/modules/monitoring/workbook.bicep)
  + `workbook.json`), criado **sem configuração manual**; recebe os resource ids reais
  por parâmetro (nenhum id de ambiente hardcoded).

## Azure Workbook — jornada do dado

O workbook responde a perguntas operacionais ("se ficar vermelho, o que investigar?"):

| Seção | Fonte | Cobre |
|---|---|---|
| 1 · Overview | App Insights + Event Hubs | está entrando dado? a Function está saudável? há falhas? |
| 2 · Ingestion | App Insights + Event Hubs | execuções/exceções/duração/erros; Incoming/Outgoing (mensagens e bytes), Throttled, ServerErrors |
| 3 · Processing | *(Databricks)* | link + query `system.lakeflow` — jobs ficam no Databricks, não no Azure |
| 4 · Data Reliability | *(Delta)* | distinção Contract/DQ/Observability + tabelas `__quarantine`/`__dq_results`/`__dataset_metrics` |
| 5 · Performance | App Insights | duração das execuções; latência de ingestão/jobs fica no Databricks/Delta |
| 6 · FinOps | *(Databricks / Cost Mgmt)* | custo/DBU em `system.billing`; custo Azure no Cost Management |

As seções **3, 4 e 6 são documentais** (texto + link para o Databricks): não existe
integração Azure↔Databricks que justifique replicar esses dados no workbook sem
arquitetura nova. As métricas de Event Hubs podem ser separadas por **URA/Calls/Surveys**
pela dimensão `EntityName` no seletor do tile.

## Alertas implementados (como código, por severidade)

Thresholds parametrizáveis (defaults no módulo). Todos notificam o **Action Group**:

| Severidade | Alerta | Condição |
|---|---|---|
| **Crítico** | `crit-func-excecao` | exceções da Function (`exceptions/count`) acima do threshold |
| **Crítico** | `crit-evh-server-errors` | `ServerErrors` do Event Hubs acima do threshold |
| **Operacional** | `oper-evh-sem-ingestao` | `IncomingMessages = 0` na janela esperada |
| **Operacional** | `oper-evh-throttling` | `ThrottledRequests` acima do threshold |
| **Warning** | `warn-func-duracao` | duração média de execução acima do threshold |

Nem toda anomalia vira incidente: **Crítico** exige ação; **Operacional** é degradação de
operação; **Warning** é comportamento a observar.

## Data Reliability (dados — no Databricks/Delta)

Três camadas distintas, todas em tabelas Delta:

| Camada | O que garante | Tabela | Como sinaliza |
|---|---|---|---|
| **Data Contract** | estrutura mínima + campos obrigatórios | `__quarantine` | evento inválido isolado (idempotente por `event_id`) |
| **Data Quality** | regras de qualidade + quality gate | `__dq_results` | falha crítica **interrompe o job** (`raise_if_critical_failed`) |
| **Data Observability** | volume / freshness / comportamento do dataset | `__dataset_metrics` | anomalia registrada (`warn`) e comparada à média móvel |

- Sinais que **geram alerta automático**: os 5 metric alerts acima (Azure Monitor).
- Sinais **apenas historizados/analisados**: volume/freshness (`__dataset_metrics`),
  contagem da quarentena e resultados de DQ (`__dq_results`) — ficam em Delta e são
  analisados no Databricks. Uma falha **crítica** de DQ interrompe o job e aparece como
  **falha do job Databricks** (alertável pelo próprio Databricks/System Tables).

> Não há integração automática entre `__dq_results`/`__dataset_metrics` e o Azure Monitor;
> a observabilidade de dados é consultada no Databricks.

## Telemetria no código
- A Function App loga contagens de envio por hub (`extra={"counts": {...}}`) → App Insights.
- O notebook Bronze imprime as **linhas gravadas no run** (via `numOutputRows` do commit
  Delta) e o total acumulado — no `AvailableNow`, `numInputRows` pode vir 0, então o
  commit transacional do Delta é a fonte de verdade.

## DataViz (negócio)
As tabelas `g_dm_callcenter.visao_*` alimentam dashboards de BI (Power BI / Grafana sobre
o SQL Warehouse do Databricks). O clustering por período garante consultas baratas.

---

[← Anterior: Analytics](analytics.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Governança →](governance.md)
