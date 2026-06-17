# ADR-0003 — Processamento agendado (AvailableNow) em vez de streaming contínuo

- **Status**: Aceito
- **Contexto**: o consumo do Event Hubs (Bronze) e do CDF (Bronze→Silver) pode rodar
  como stream contínuo 24/7 ou como micro-batch agendado.

## Decisão
Usar **`Trigger.AvailableNow`** com agendamento: o job liga o cluster, processa todo
o backlog disponível em micro-batches e encerra (autotermination). Aplica-se tanto à
ingestão Bronze quanto ao processamento Bronze→Silver.

## Alternativas
- **Streaming contínuo** — latência de segundos, porém cluster ligado o tempo todo
  (custo alto) e desnecessário para analytics D-1.

## Consequências
- (+) **Custo muito menor**; o checkpoint garante exactly-once entre execuções.
- (−) Latência de até um ciclo de agendamento. Para tempo real, ver [Roadmap](../roadmap.md).

Relacionado: [FinOps](../finops.md), [Trade-offs](../trade-offs.md).
