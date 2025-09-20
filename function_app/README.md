# Azure Functions – Event Hubs com SPN via Key Vault

Este projeto implementa uma **Azure Function (TimerTrigger)** que gera dados sintéticos de chamadas de URA, atendimentos humanos e pesquisas de satisfação.  
Os dados são enviados para **Azure Event Hubs** com **autenticação via AAD (SPN)**, sendo os segredos do Service Principal armazenados em **Azure Key Vault** e acessados com **Managed Identity**.

---

## 🏗 Arquitetura

- **Generators**: cria eventos sintéticos (`ura`, `calls`, `surveys`)
- **Services**: cliente para Event Hubs e Key Vault
- **Auth**: monta credenciais do SPN a partir do KV
- **Config**: centraliza variáveis de ambiente
- **Exceptions**: exceções de domínio
- **Utils**: utilitários de logging

---

## 📂 Estrutura de pastas

```
azurefn-eventhub/
├── function_app.py                 # Entry point (TimerTrigger)
├── requirements.txt
├── host.json
├── local.settings.json             # (não versionar)
├── auth/
│   └── credentials.py
├── config/
│   └── settings.py
├── exceptions/
│   └── domain_exceptions.py
├── generators/
│   ├── ura.py
│   ├── calls.py
│   └── surveys.py
├── models/
│   └── schemas.py
├── services/
│   ├── eventhub_client.py
│   └── keyvault.py
└── utils/
    └── logging_utils.py
```

---

## ⚙️ Pré-requisitos

- **Python 3.10+**
- Azure CLI (`az`)
- Extensão Functions Core Tools
- Acesso a:
  - Azure Event Hubs
  - Azure Key Vault
  - Azure Function App

---

## 📦 Instalação

1. Clone este repositório:

```bash
git clone <url>
cd azurefn-eventhub
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate   # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## 🔑 Configuração (App Settings)

Configure as variáveis no **Function App → Configuration**:

| Variável                     | Exemplo                                      | Descrição |
|-------------------------------|----------------------------------------------|-----------|
| `KV_URI`                      | `https://akvcjtecprd001.vault.azure.net/`    | URI do Key Vault |
| `KV_SECRET_SPN_CLIENT_ID`     | `ServicePrincipalAppId`                      | Nome do segredo no KV |
| `KV_SECRET_SPN_TENANT_ID`     | `ServicePrincipalTenantId`                   | Nome do segredo no KV |
| `KV_SECRET_SPN_CLIENT_SECRET` | `ServicePrincipalSecret`                     | Nome do segredo no KV |
| `EVENTHUB_NAMESPACE_FQDN`     | `meu-namespace.servicebus.windows.net`       | FQDN do namespace EH |
| `EH_NAME_URA`                 | `evh_cj_tec_ura`                             | Nome do Event Hub |
| `EH_NAME_CALLS`               | `evh_cj_tec_calls`                           | Nome do Event Hub |
| `EH_NAME_SURVEYS`             | `evh_cj_tec_surveys`                         | Nome do Event Hub |

---

## 🔒 RBAC / Permissões

1. **Function App → Identity**
   - Habilite **System Assigned Managed Identity**

2. **Key Vault**
   - Atribua à MI a role **Key Vault Secrets User**  
   (ou Access Policy com permissão *Get* em Secrets)

3. **Event Hubs**
   - Atribua ao **App Registration (SPN)** a role **Azure Event Hubs Data Sender**

---

## ▶️ Execução local

```bash
func start
```

---

## 🚀 Deploy para Azure

```bash
func azure functionapp publish <NOME_DO_FUNCTION_APP>
```

---

## 📊 Observabilidade

- Logs estruturados via `logging_utils`
- Application Insights pode ser habilitado para monitorar execuções
- Exceptions personalizadas (`EventSendError`, `KeyVaultSecretError`) facilitam troubleshooting

---

## ✅ Fluxo resumido

1. TimerTrigger dispara a cada 2 minutos
2. Gera eventos URA, Calls e Surveys
3. Lê credenciais do SPN no Key Vault (via MI)
4. Cria `ClientSecretCredential` e autentica no Event Hubs
5. Envia eventos para 3 Event Hubs distintos

---
