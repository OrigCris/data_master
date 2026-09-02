# 10. Ingestão de Dados (Bronze)

## Produção de eventos (Azure Functions)

O código vive em [`function_app/`](../function_app) e segue uma arquitetura limpa:

```
function_app/
├── function_app.py        # TimerTrigger (orquestra geração + envio)
├── auth/credentials.py    # credencial da Managed Identity (DefaultAzureCredential)
├── config/settings.py     # configuração por env vars
├── generators/            # ura.py, calls.py, surveys.py
├── services/              # eventhub_client.py
└── exceptions/            # exceções de domínio
```

- **TimerTrigger** dispara a cada 2 minutos. A cada execução gera de 8 a 30
  chamadas de URA e, para as **derivadas**, gera atendimentos e pesquisas
  **mantendo o mesmo `id_chamada`** (coerência referencial entre os hubs).
- **Autenticação**: `get_credential()` devolve a **Managed Identity** do Function App
  (`DefaultAzureCredential`), que tem `Azure Event Hubs Data Sender` no namespace.
  Nenhum segredo em configuração nem no Key Vault — autenticação por identidade (OAuth).
- **Envio em lote**: `send_events()` agrupa eventos em `EventDataBatch`, respeitando
  o limite de tamanho do batch e reabrindo um novo quando estoura.

> **Coerência dos dados**: `calls` e `surveys` só existem para chamadas com
> `derivado_atendimento = true`, e `data_envio` da pesquisa é uma **data** (não
> timestamp) — alinhado ao tipo `DateType` do contrato da Bronze.

## Landing na Bronze (Databricks)

O notebook [`bronze_streaming`](../Databricks/layer_bronze/notebooks/bronze_streaming.ipynb)
consome cada Event Hub com **`Trigger.AvailableNow`**:

1. Conecta ao **endpoint Kafka** do Event Hubs com **OAuth/Entra ID** (SASL
   `OAUTHBEARER`): a SPN consumidora — com o papel *Azure Event Hubs Data Receiver* —
   obtém o token via client-credentials, sem SAS keys. As credenciais da SPN vêm do
   **Key Vault** por **Secret Scope** (AKV).
2. **Parseia** o evento contra o **contrato versionado** da tabela
   (`transforms.contracts`) e persiste já **estruturado**, preservando o **payload
   original** (`raw_payload`) para auditoria. Payload malformado não é descartado — os
   campos parseados ficam nulos, auditáveis pelo `raw_payload`. **Sem regras de negócio**
   (isso é da Silver).
3. Garante a tabela Delta **append-only** (schema estruturado + metadados +
   `schema_version` + `ingestion_date`) com **liquid clustering** por `ingestion_date`.
4. `writeStream ... trigger(availableNow=True)` grava em append, com **checkpoint** por
   `eventhub/table` (reprocesso seguro).
5. Reporta as **linhas gravadas** via commit do Delta (fonte de verdade no `AvailableNow`).

As **dimensões** (`bronze_dim_clientes`, `bronze_dim_assistentes`) são geradas com
Faker e gravadas como tabelas managed (overwrite + `OPTIMIZE`).

## Parâmetros (DAB)
O bundle [`layer_bronze/databricks.yml`](../Databricks/layer_bronze/databricks.yml)
parametriza catálogo, schema, nomes de hubs, cron e quantidades via `variables` e
`base_parameters` — sem hardcode no notebook de streaming.

---

[← Anterior: Como Usar](how-to-use.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Processamento →](processing.md)
