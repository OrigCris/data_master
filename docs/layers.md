# 03. Camadas do Data Lake (Medallion)

A plataforma organiza os dados em três camadas, cada uma em um **schema** próprio
do Unity Catalog, com **MANAGED LOCATION** por camada no ADLS Gen2.

| Camada | Schema | Conteúdo | Formato | Estratégia |
|---|---|---|---|---|
| **Bronze** | `b_dm_callcenter` | Dado cru (landing) + dimensões | Delta | append / overwrite |
| **Silver** | `s_dm_callcenter` | Dado limpo e normalizado | Delta | stream Delta → MERGE (incremental) |
| **Gold** | `g_dm_callcenter` | Visões analíticas D-1 | Delta | overwrite + `replaceWhere` |

## Bronze — landing imutável

- **Streaming**: Event Hubs → Delta via `readStream` com **`Trigger.AvailableNow`**. O
  schema cru preserva metadados do Event Hubs (`offset`, `enqueuedTime`, etc.) e
  acrescenta `ingestion_ts`/`ingestion_date`.
- **Dimensões**: geradas sinteticamente (Faker) e gravadas como tabelas managed.
- **Append-only**: como só cresce por append, é consumida pela Silver como **fonte de
  streaming Delta direto** (ver [ADR-0002](adrs/0002-incremental-streaming.md)).
- **Liquid clustering** por `ingestion_date`.

## Silver — incremental e idempotente

A Silver consome a Bronze (append-only) como **stream Delta + checkpoint**
(`Trigger.AvailableNow` + `foreachBatch` MERGE) e aplica **MERGE** por chave de
negócio. Detalhes em [Processamento](processing.md). Benefícios:

- **Progresso**: o checkpoint controla o offset/versão consumido por fonte.
- **Semântica**: com `foreachBatch` a escrita é **at-least-once** — um micro-batch
  pode reexecutar em retries. A **idempotência** vem do **MERGE por chave de negócio**,
  que absorve reprocessos sem duplicar ([ADR-0002](adrs/0002-incremental-streaming.md)).
- **Custo**: processa só o delta, não a tabela inteira.

## Gold — pronta para consumo

Visões diárias (**D-1**) materializadas com `replaceWhere` por `DT_REFE` — cada
execução reescreve apenas a partição do dia, mantendo o histórico. Clustering por
`(CD_PERI, DT_REFE, <chave>)` para *partition pruning* nos dashboards.

## Por que Delta + Unity Catalog?

O **Delta Lake** entrega ACID e time-travel nativos, e o **Unity Catalog**
centraliza catálogo, governança e *lineage* — ver [Trade-offs](trade-offs.md).

---

[← Anterior: Modelo de Dados](mer.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Arquitetura →](architecture.md)
