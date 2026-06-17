# 03. Camadas do Data Lake (Medallion)

A plataforma organiza os dados em três camadas, cada uma em um **schema** próprio
do Unity Catalog, com **MANAGED LOCATION** por camada no ADLS Gen2.

| Camada | Schema | Conteúdo | Formato | Estratégia |
|---|---|---|---|---|
| **Bronze** | `b_dm_callcenter` | Dado cru (landing) + dimensões | Delta + CDF | append / overwrite |
| **Silver** | `s_dm_callcenter` | Dado limpo e normalizado | Delta | CDF → MERGE (incremental) |
| **Gold** | `g_dm_callcenter` | Visões analíticas D-1 | Delta | overwrite + `replaceWhere` |

## Bronze — landing imutável

- **Streaming**: Event Hubs → Delta via `readStream` com **trigger once**. O
  schema cru preserva metadados do Event Hubs (`offset`, `enqueuedTime`, etc.) e
  acrescenta `ingestion_ts`/`ingestion_date`.
- **Dimensões**: geradas sinteticamente (Faker) e gravadas como tabelas managed.
- **Change Data Feed habilitado** (`delta.enableChangeDataFeed = true`) para que a
  Silver consuma apenas as mudanças.
- **Liquid clustering** por `ingestion_date`.

## Silver — incremental e idempotente

A Silver consome o **CDF** da Bronze por **streaming + checkpoint**
(`Trigger.AvailableNow` + `foreachBatch` MERGE) e aplica **MERGE** por chave de
negócio. Detalhes em [Processamento](processing.md). Benefícios:

- **Idempotência**: reprocessos não duplicam dados.
- **Custo**: processa só o delta, não a tabela inteira.
- **Exactly-once**: o checkpoint do stream controla o progresso por fonte
  ([ADR-0002](adrs/0002-incremental-streaming-cdf.md)).

## Gold — pronta para consumo

Visões diárias (**D-1**) materializadas com `replaceWhere` por `DT_REFE` — cada
execução reescreve apenas a partição do dia, mantendo o histórico. Clustering por
`(CD_PERI, DT_REFE, <chave>)` para *partition pruning* nos dashboards.

## Por que Delta + Unity Catalog (e não Iceberg + Glue)?

É o equivalente Azure ao Iceberg/Glue do case de referência: **Delta Lake** entrega
ACID, time-travel e CDF nativos, e o **Unity Catalog** centraliza catálogo,
governança e *lineage* — ver [Trade-offs](trade-offs.md).

---

[← Anterior: Modelo de Dados](mer.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Arquitetura →](architecture.md)
