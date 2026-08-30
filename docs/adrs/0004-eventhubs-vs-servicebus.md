# ADR-0004 — Event Hubs como camada de ingestão

- **Status**: Aceito
- **Contexto**: precisamos de um broker para ingestão de eventos em tempo real,
  consumível pelo Spark.

## Decisão
Usar **Azure Event Hubs** (um hub por fonte: ura/calls/surveys), consumido pelo Spark
via **endpoint Kafka** com autenticação **OAuth/Entra ID** (SASL `OAUTHBEARER`) — o
conector Kafka é nativo do Databricks Runtime e a identidade dispensa SAS keys.

## Alternativas
- **Azure Service Bus** — orientado a mensagens/filas com semântica transacional;
  menos otimizado para *high-throughput streaming* e integração analítica.
- **Kafka (HDInsight/Confluent)** — poderoso, porém mais custo/operacionalização do
  que o necessário aqui.

## Consequências
- (+) Alto throughput, integração nativa com Spark, simples de provisionar.
- (+) Autenticação por identidade (RBAC) ponta a ponta — *Data Sender* no produtor e
  *Data Receiver* no consumidor — sem SAS keys.
- A **retenção** é dimensionada por ambiente (SLA × custo) e configurável no IaC.

Relacionado: [Ingestão](../ingestion.md).
