# 06. Trade-offs e Decisões de Arquitetura

Esta página registra as decisões mais relevantes, suas alternativas e os
*trade-offs* assumidos. Decisões estruturais têm um [ADR](adrs) dedicado.

## Ingestão e processamento

### Processamento agendado (AvailableNow) vs streaming contínuo ([ADR-0003](adrs/0003-scheduled-availablenow.md))
- **Decisão**: o consumo (Event Hubs e Bronze→Silver) roda como *micro-batch* agendado
  com `Trigger.AvailableNow`, não como stream 24/7.
- **Por quê**: o volume é previsível e não exige latência de segundos; o job liga o
  cluster, processa o backlog e desliga — **custo muito menor**.
- **Trade-off**: latência de até um ciclo de agendamento (30 min). Aceitável para
  analytics D-1. Para tempo real, ver [Roadmap](roadmap.md).

### Silver incremental por streaming Delta + checkpoint ([ADR-0002](adrs/0002-incremental-streaming.md))
- **Decisão**: a Silver consome a Bronze (append-only) como **stream Delta** por
  **`AvailableNow` + `foreachBatch` MERGE**, com o **checkpoint** controlando o
  progresso. Sem CDF: numa fonte append-only ele não agrega nada (ver ADR-0002).
- **Trade-off**: o progresso fica no checkpoint (opaco). Com `foreachBatch` a escrita é
  **at-least-once**; a não-duplicidade não é assumida pelo checkpoint e sim garantida
  pelo **MERGE idempotente por chave de negócio** (o sink absorve retries).

### Orquestração por dependência (e não por horário)
- **Decisão**: um job orquestrador (`dm-pipeline`) encadeia dims → silver → gold com
  `depends_on` via `run_job_task`; só o orquestrador tem schedule. A ingestão de
  streaming roda em cadência própria (contínua).
- **Trade-off**: o orquestrador resolve os job ids das camadas por nome (`lookup`),
  então as camadas precisam ser publicadas antes dele. Em troca, cada etapa começa
  ao **término real** da anterior, não num horário fixo.

## Plataforma

### Delta + Unity Catalog ([ADR-0001](adrs/0001-medallion-delta-uc.md))
- ACID, time-travel e CDF nativos; catálogo, governança e lineage centralizados.

### Event Hubs ([ADR-0004](adrs/0004-eventhubs-vs-servicebus.md))
- **Event Hubs** (não Service Bus) por ser otimizado para *high-throughput
  ingestion* e integração nativa com o conector Spark.
- A **retenção** é um parâmetro de SLA/custo (dimensionada por ambiente). Na Bronze, a
  semântica **exactly-once** vem da combinação **offsets no checkpoint + fonte replayable
  (Event Hubs/Kafka) + sink transacional Delta** — reprocessável dentro da janela de
  retenção; o checkpoint sozinho não garante exactly-once.

## Regras de negócio (decisões explícitas)

### Faixa de NPS (clássica)
- **Decisão**: NPS clássico na escala **0–10** — **promotor 9–10**, **passivo 7–8**,
  **detrator 0–6**; `VL_NPS = (promotores − detratores) / total × 100`.
- **Onde**: classificação em `visao_assistentes` (`IN_PRMT`/`IN_NTRO`/`IN_DETR`); a
  escala é validada no gate (`VL_NOTA ∈ [0,10]`).

### Métrica de rechamada (`IN_RECH`)
- **Definição**: uma chamada é **rechamada** quando o mesmo cliente teve uma chamada
  **anterior** (de `ID_CHAM` distinto) há no máximo **24h** — marca-se a chamada de
  retorno (ex.: ligou 12h e voltou às 16h → a das 16h é a rechamada).
- **Cálculo**: janela por `ID_CLIE` ordenada por `DH_INIC`, com `lag` para a chamada
  anterior e gap = `atual − anterior` (positivo) dentro de 24h.
- **Cobertura**: a base da janela inclui **D-1** além de `odate`, então retornos que
  cruzam a meia-noite (ex.: 23h → 01h) são capturados; a saída materializa apenas as
  chamadas de `odate`.

## Qualidade e operação
- **Data Quality como gate**: expectativas críticas (chaves não nulas/únicas,
  `VL_NOTA ∈ [0,10]`) podem **falhar o job**; *warns* apenas registram. Ver
  [`Databricks/lib/quality`](../Databricks/lib/quality).
- **PII no catálogo, não só no pipeline**: o mascaramento é imposto por *column
  mask* do Unity Catalog, então vale para qualquer consumidor — não depende de o
  ETL lembrar de mascarar.

---

[← Anterior: Componentização](stacks.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Pré-Requisitos →](pre-requirements.md)
