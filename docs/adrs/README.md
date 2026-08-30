# Architecture Decision Records (ADRs)

Registro das decisões arquiteturais relevantes e seus trade-offs.

| ADR | Decisão |
|---|---|
| [0001](0001-medallion-delta-uc.md) | Medallion com Delta Lake + Unity Catalog |
| [0002](0002-incremental-streaming.md) | Consumo incremental Bronze→Silver via streaming Delta + checkpoint |
| [0003](0003-scheduled-availablenow.md) | Processamento agendado (AvailableNow) vs streaming contínuo |
| [0004](0004-eventhubs-vs-servicebus.md) | Event Hubs como camada de ingestão |
| [0005](0005-pii-masking-unity-catalog.md) | Mascaramento de PII no catálogo |
| [0006](0006-data-contracts-dlq-observability.md) | Data contracts, quarentena (DLQ) e observabilidade de dados |

> Novas decisões devem seguir o mesmo formato (Status / Contexto / Decisão /
> Alternativas / Consequências).
