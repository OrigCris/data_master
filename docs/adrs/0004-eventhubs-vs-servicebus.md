# ADR-0004 — Event Hubs como camada de ingestão

- **Status**: Aceito
- **Contexto**: precisamos de um broker para ingestão de eventos em tempo real,
  consumível pelo Spark.

## Decisão
Usar **Azure Event Hubs** (um hub por fonte: ura/calls/surveys), com o conector
Spark `azure-eventhubs-spark`.

## Alternativas
- **Azure Service Bus** — orientado a mensagens/filas com semântica transacional;
  menos otimizado para *high-throughput streaming* e integração analítica.
- **Kafka (HDInsight/Confluent)** — poderoso, porém mais custo/operacionalização do
  que o necessário aqui.

## Consequências
- (+) Alto throughput, integração nativa com Spark, simples de provisionar.
- (−) Retenção curta no plano enxuto (1h) → risco de perda se o consumo falhar por
  muito tempo. Mitigação (buffer com Service Bus) no [Roadmap](../roadmap.md).

Relacionado: [Ingestão](../ingestion.md).
