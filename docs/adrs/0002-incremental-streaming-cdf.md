# ADR-0002 — Consumo incremental Bronze→Silver via streaming CDF + checkpoint

- **Status**: Aceito
- **Contexto**: a Silver precisa atualizar com baixo custo, ser idempotente em
  reprocessos e consumir apenas o que mudou na Bronze.

## Decisão
Consumir o **Change Data Feed** da Bronze como **fonte de Structured Streaming**,
com **`Trigger.AvailableNow`** (processa o backlog disponível em micro-batches e
encerra) e **`foreachBatch`** aplicando **MERGE** idempotente por chave de negócio.
O **checkpoint** do stream controla o progresso (offset/versão).

## Alternativas
- **Full reload diário** — simples, porém caro e cresce com a tabela.
- **Streaming contínuo 24/7** — latência de segundos, desnecessária para analytics
  D-1 e com custo de cluster sempre ligado (ver [ADR-0003](0003-scheduled-availablenow.md)).

## Consequências
- (+) **Exactly-once** e **backpressure** garantidos pelo engine; sem estado custom
  para gerenciar.
- (+) Padrão idiomático no Databricks/Delta; menos código.
- (−) O progresso vive no checkpoint (opaco); reprocessar = resetar o checkpoint da
  fonte (ver runbook). Encapsulado e testado em
  [`Databricks/lib/transforms`](../../Databricks/lib/transforms).

Relacionado: [Processamento](../processing.md), [ADR-0003](0003-scheduled-availablenow.md).
