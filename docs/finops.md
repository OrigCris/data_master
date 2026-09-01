# 15. FinOps — Gestão de Custos

Gestão de custos com **Azure Cost Management**. O objetivo é tornar o custo
**observável** e guiar decisões de arquitetura por custo/benefício.

## Onde o custo nasce

| Componente | Driver de custo | Alavanca de otimização |
|---|---|---|
| Databricks | DBU × tempo de cluster | **`AvailableNow`** (micro-batch agendado) + `autotermination 20 min` + clusters pequenos (`Standard_D4ds_v6`, 1 worker) |
| Event Hubs | throughput units + retenção | plano `Standard`; retenção dimensionada ao SLA |
| ADLS Gen2 | GB armazenados + transações | Delta `OPTIMIZE` + liquid clustering (menos arquivos) |
| Function App | execuções | plano de Consumo `Y1` (escala a zero, cobra por execução); produção controlada por TimerTrigger |
| Log Analytics | GB ingeridos | retenção 30 dias |

## Decisões que reduzem custo
- **Processamento agendado (`AvailableNow`)** → o cluster só liga para processar o
  backlog e desliga (ver [Trade-offs](trade-offs.md)).
- **Processamento incremental (stream Delta)** → processa só o que chegou, não a tabela inteira.
- **`replaceWhere` na Gold** → reescreve só a partição do dia.
- **Liquid clustering** → menos arquivos pequenos, menos varredura.
- **Clusters job-scoped** (não all-purpose) com autotermination curto.

## Como acompanhar
```bash
# Custo por serviço no Resource Group (últimos 30 dias)
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/<sub>/resourceGroups/rsgcjtecprd001" \
  --dataset-aggregation '{"totalCost":{"name":"Cost","function":"Sum"}}' \
  --dataset-grouping name="ServiceName" type="Dimension"
```
- **Tags** (`project`, `domain`, `env`) propagadas pelo Bicep permitem *cost
  allocation* por projeto/ambiente.
- Um **Budget** com alerta no Cost Management fecha o ciclo (no [Roadmap](roadmap.md)).

---

[← Anterior: Governança](governance.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Benchmark →](benchmark.md)
