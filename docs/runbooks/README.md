# Runbooks operacionais

Procedimentos para incidentes e operações recorrentes do pipeline.

| Runbook | Quando usar |
|---|---|
| [ingestion-stopped](ingestion-stopped.md) | Sem eventos chegando na Bronze (alerta de ingestão). |
| [reprocess-silver](reprocess-silver.md) | Reprocessar uma fonte Silver desde a Bronze. |
| [streaming-checkpoint-reset](streaming-checkpoint-reset.md) | Checkpoint do streaming corrompido/incompatível. |

> Cada runbook segue o formato: **disparo → triagem → ação → validação**.
