# 10. Ingestão de Dados (Bronze)

## Produção de eventos (Azure Functions)

O código vive em [`function_app/`](../function_app) e segue uma arquitetura limpa:

```
function_app/
├── function_app.py        # TimerTrigger (orquestra geração + envio)
├── auth/credentials.py    # SPN via Key Vault
├── config/settings.py     # configuração por env vars
├── generators/            # ura.py, calls.py, surveys.py
├── services/              # eventhub_client.py, keyvault.py
└── exceptions/            # exceções de domínio
```

- **TimerTrigger** dispara a cada 2 minutos. A cada execução gera de 8 a 30
  chamadas de URA e, para as **derivadas**, gera atendimentos e pesquisas
  **mantendo o mesmo `id_chamada`** (coerência referencial entre os hubs).
- **Autenticação**: `get_spn_credential()` lê `client_id`/`tenant_id`/`secret` do
  **Key Vault** (Managed Identity), montando uma `ClientSecretCredential`. Nenhum
  segredo fica em configuração.
- **Envio em lote**: `send_events()` agrupa eventos em `EventDataBatch`, respeitando
  o limite de tamanho do batch e reabrindo um novo quando estoura.

> **Coerência dos dados**: `calls` e `surveys` só existem para chamadas com
> `derivado_atendimento = true`, e `data_envio` da pesquisa é uma **data** (não
> timestamp) — alinhado ao tipo `DateType` esperado pela Silver.

## Landing na Bronze (Databricks)

O notebook [`bronze_streaming`](../Databricks/layer_bronze/notebooks/bronze_streaming.ipynb)
consome cada Event Hub com **`Trigger.AvailableNow`**:

1. Lê a *connection string* via **Secret Scope** (AKV).
2. Garante a tabela Delta com schema cru + `ingestion_ts`/`ingestion_date`, com
   **CDF habilitado** e **liquid clustering** por `ingestion_date`.
3. `writeStream ... trigger(availableNow=True)` grava em append, com **checkpoint** por
   `eventhub/table` (reprocesso seguro).
4. Imprime telemetria do último batch (linhas, duração).

As **dimensões** (`bronze_dim_clientes`, `bronze_dim_assistentes`) são geradas com
Faker e gravadas como tabelas managed (overwrite + `OPTIMIZE`).

## Parâmetros (DAB)
O bundle [`layer_bronze/databricks.yml`](../Databricks/layer_bronze/databricks.yml)
parametriza catálogo, schema, nomes de hubs, cron e quantidades via `variables` e
`base_parameters` — sem hardcode no notebook de streaming.

---

[← Anterior: Como Usar](how-to-use.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Processamento →](processing.md)
