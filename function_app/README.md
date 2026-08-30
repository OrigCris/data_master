# Azure Functions — Produtor de eventos (Event Hubs via Managed Identity)

**Azure Function (TimerTrigger)** que gera dados sintéticos de chamadas de URA,
atendimentos humanos e pesquisas de satisfação e os envia para **Azure Event Hubs**.
A autenticação é por **identidade (Entra ID)**: a **System-Assigned Managed Identity**
do Function App tem o papel `Azure Event Hubs Data Sender` no namespace — **sem SAS
keys e sem segredos** em configuração ou no código.

---

## 🏗 Arquitetura

- **Generators**: cria eventos sintéticos (`ura`, `calls`, `surveys`)
- **Services**: cliente de envio para o Event Hubs
- **Auth**: credencial da Managed Identity (`DefaultAzureCredential`)
- **Config**: centraliza variáveis de ambiente
- **Exceptions**: exceções de domínio
- **Utils**: utilitários de logging

## 📂 Estrutura de pastas

```
function_app/
├── function_app.py            # Entry point (TimerTrigger)
├── requirements.txt
├── host.json
├── auth/
│   └── credentials.py         # get_credential() → DefaultAzureCredential (MI)
├── config/
│   └── settings.py
├── exceptions/
│   └── domain_exceptions.py
├── generators/
│   ├── ura.py
│   ├── calls.py
│   └── surveys.py
├── services/
│   └── eventhub_client.py
└── utils/
    └── logging_utils.py
```

## ⚙️ Configuração (App Settings)

Provisionadas pelo Bicep ([`functionapp.bicep`](../infrastructure/bicep/modules/functionapp.bicep)):

| Variável                     | Exemplo                                  | Descrição |
|------------------------------|------------------------------------------|-----------|
| `EVENTHUB_NAMESPACE_FQDN`    | `evhnscjtecprd001.servicebus.windows.net`| FQDN do namespace EH |
| `EH_NAME_URA`                | `evh_cj_tec_ura`                         | Nome do Event Hub |
| `EH_NAME_CALLS`              | `evh_cj_tec_calls`                       | Nome do Event Hub |
| `EH_NAME_SURVEYS`            | `evh_cj_tec_surveys`                     | Nome do Event Hub |

Não há segredos nem URI de Key Vault: a autenticação usa a Managed Identity.

## 🔒 RBAC / Permissões

- **Function App → Identity**: **System-Assigned Managed Identity** habilitada (Bicep).
- **Event Hubs**: a MI recebe **`Azure Event Hubs Data Sender`** no namespace
  ([`roles.bicep`](../infrastructure/bicep/modules/roles.bicep)). O namespace tem
  `disableLocalAuth: true` — SAS keys não são aceitas.

## ▶️ Execução local

Com `az login` feito, o `DefaultAzureCredential` usa as credenciais do desenvolvedor
(que precisam de `Data Sender` no namespace para testar o envio real):

```bash
func start
```

## 🚀 Deploy

No CI (recomendado), pelo workflow [`deploy-function.yml`](../.github/workflows/deploy-function.yml)
(`workflow_dispatch`, `environment: prd`), que publica com **build remoto Oryx** das
dependências. Localmente:

```bash
func azure functionapp publish funccjtecprd001
```

## ✅ Fluxo resumido

1. TimerTrigger dispara a cada 2 minutos.
2. Gera eventos URA, Calls e Surveys (mesmo `id_chamada` entre eles).
3. Obtém a credencial da **Managed Identity** (`get_credential()`).
4. Autentica no Event Hubs por OAuth e envia aos 3 hubs em lote (`EventDataBatch`).

## 📊 Observabilidade

- Logs estruturados via `logging_utils` (contagens por hub).
- Application Insights habilitado para monitorar execuções.
- Exceções de domínio (`EventBuildError`, `EventSendError`) facilitam o troubleshooting.
