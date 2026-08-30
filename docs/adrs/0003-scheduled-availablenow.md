# ADR-0003 — Processamento agendado (AvailableNow) em vez de streaming contínuo

- **Status**: Aceito
- **Contexto**: o consumo do Event Hubs (Bronze) e da Bronze (Bronze→Silver) pode rodar
  como stream contínuo 24/7 ou como micro-batch agendado.

## Decisão
Usar **`Trigger.AvailableNow`** com agendamento: o job liga o cluster, processa todo
o backlog disponível em micro-batches e encerra (autotermination). Aplica-se tanto à
ingestão Bronze quanto ao processamento Bronze→Silver.

## Alternativas
- **Streaming contínuo** — latência de segundos, porém cluster ligado o tempo todo
  (custo alto) e desnecessário para analytics D-1.

## Consequências
- (+) **Custo muito menor**; o checkpoint mantém o progresso entre execuções (não
  reprocessa o que já leu). Na Bronze, o **exactly-once** vem de offsets no checkpoint +
  fonte replayable + sink transacional Delta (não do checkpoint isolado); na Silver
  (`foreachBatch`) a escrita é at-least-once e a não-duplicidade vem do MERGE idempotente
  ([ADR-0002](0002-incremental-streaming.md)).
- (−) Latência de até um ciclo de agendamento. Para tempo real, ver [Roadmap](../roadmap.md).

Relacionado: [FinOps](../finops.md), [Trade-offs](../trade-offs.md).
