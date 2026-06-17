# 06. Trade-offs e Decisões de Arquitetura

Esta página registra as decisões mais relevantes, suas alternativas e os
*trade-offs* assumidos. Decisões estruturais têm um [ADR](adrs) dedicado.

## Ingestão e processamento

### Processamento agendado (AvailableNow) vs streaming contínuo ([ADR-0003](adrs/0003-scheduled-availablenow.md))
- **Decisão**: o consumo (Event Hubs e CDF) roda como *micro-batch* agendado com
  `Trigger.AvailableNow`, não como stream 24/7.
- **Por quê**: o volume é previsível e não exige latência de segundos; o job liga o
  cluster, processa o backlog e desliga — **custo muito menor**.
- **Trade-off**: latência de até um ciclo de agendamento (30 min). Aceitável para
  analytics D-1. Para tempo real, ver [Roadmap](roadmap.md).

### Silver incremental por streaming CDF + checkpoint ([ADR-0002](adrs/0002-incremental-streaming-cdf.md))
- **Decisão**: a Silver consome o Change Data Feed da Bronze por **streaming
  `AvailableNow` + `foreachBatch` MERGE**, com o **checkpoint** controlando o progresso.
- **Trade-off**: o progresso fica no checkpoint (opaco) em troca de **exactly-once**,
  **backpressure** e idempotência garantida pelo engine.

### Agendamento em cascata por horário (e não por evento)
- **Decisão**: bronze (02h) → silver (05h) → gold (06h).
- **Trade-off**: simples e previsível, mas acopla o início de cada etapa a um
  horário fixo (não ao término real da anterior). Evolução natural: orquestrar com
  dependências entre jobs / *file arrival trigger* ([Roadmap](roadmap.md)).

## Plataforma

### Delta + Unity Catalog ([ADR-0001](adrs/0001-medallion-delta-uc.md))
- ACID, time-travel e CDF nativos; catálogo, governança e lineage centralizados.

### Event Hubs ([ADR-0004](adrs/0004-eventhubs-vs-servicebus.md))
- **Event Hubs** (não Service Bus) por ser otimizado para *high-throughput
  ingestion* e integração nativa com o conector Spark.
- A **retenção** é um parâmetro de SLA/custo (dimensionada por ambiente); o
  checkpoint do consumo garante exactly-once dentro da janela de retenção.

## Regras de negócio (decisões explícitas)

### Faixa de NPS adaptada
- **Decisão**: numa escala 1–10, classifica-se **promotor ≥ 6**, **neutro = 5**,
  **detrator ≤ 4**.
- **Observação**: difere do NPS clássico (9–10 / 7–8 / 0–6). É uma **escolha de
  negócio explícita** para a escala adotada na pesquisa; documentada aqui para não
  ser confundida com erro. Trocar a faixa é um ajuste de uma linha em
  `visao_assistentes`.

### Métrica de rechamada (`IN_RECH`)
- **Definição**: uma chamada é **rechamada** quando o mesmo cliente teve uma chamada
  **anterior** (de `ID_CHAM` distinto) há no máximo **24h** — marca-se a chamada de
  retorno (ex.: ligou 12h e voltou às 16h → a das 16h é a rechamada).
- **Cálculo**: janela por `ID_CLIE` ordenada por `DH_INIC`, com `lag` para a chamada
  anterior e gap = `atual − anterior` (positivo) dentro de 24h.
- **Escopo atual**: a janela considera as chamadas do próprio dia; retornos que cruzam
  a meia-noite são um refinamento mapeado no [Roadmap](roadmap.md).

## Qualidade e operação
- **Data Quality como gate**: expectativas críticas (chaves não nulas/únicas,
  `VL_NOTA ∈ [1,10]`) podem **falhar o job**; *warns* apenas registram. Ver
  [`Databricks/lib/quality`](../Databricks/lib/quality).
- **PII no catálogo, não só no pipeline**: o mascaramento é imposto por *column
  mask* do Unity Catalog, então vale para qualquer consumidor — não depende de o
  ETL lembrar de mascarar.

---

[← Anterior: Componentização](stacks.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Pré-Requisitos →](pre-requirements.md)
