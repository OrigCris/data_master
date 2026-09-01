# ADR-0002 — Consumo incremental Bronze→Silver via streaming Delta + checkpoint

- **Status**: Aceito
- **Contexto**: a Silver precisa atualizar com baixo custo, ser idempotente em
  reprocessos e consumir apenas o que chegou de novo na Bronze.

## Decisão
Consumir a Bronze como **fonte de Structured Streaming Delta**
(`readStream.format("delta")`), com **`Trigger.AvailableNow`** (processa o backlog
disponível em micro-batches e encerra) e **`foreachBatch`** aplicando **MERGE**
idempotente por chave de negócio. O **checkpoint** do stream controla o progresso.

Como a Bronze é **append-only**, o stream Delta já entrega exatamente as linhas novas.
`skipChangeCommits` ignora reescritas de manutenção (ex.: `OPTIMIZE`) e, mesmo que uma
reescrita re-emita linhas, o MERGE idempotente as absorve.

## Alternativas
- **Full reload diário** — simples, porém caro e cresce com a tabela.
- **Streaming contínuo 24/7** — latência de segundos, desnecessária para analytics
  D-1 e com custo de cluster sempre ligado (ver [ADR-0003](0003-scheduled-availablenow.md)).

## Consequências
- (+) **Backpressure** e controle de progresso pelo engine; sem estado custom.
- (+) `foreachBatch` dá semântica **at-least-once**; a **idempotência** não é assumida
  pelo checkpoint e sim **desenhada no sink** — o MERGE por chave de negócio garante
  que um micro-batch reexecutado não duplique registros.
- (−) O progresso vive no checkpoint (opaco); reprocessar = resetar o checkpoint da
  fonte (ver runbook). Encapsulado e testado em
  [`Databricks/lib/transforms`](../../Databricks/lib/transforms).

Relacionado: [Processamento](../processing.md), [ADR-0003](0003-scheduled-availablenow.md).
