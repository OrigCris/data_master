# Infraestrutura como Código — Bicep modular

Provisionamento declarativo e idempotente do ambiente Azure do Data Master,
organizado em **módulos por domínio**. O bootstrap de identidade/segredos
(Entra ID) fica em [`bootstrap.sh`](../bootstrap.sh), executado após o Bicep.

## Mapa de módulos

| Módulo | Recurso Azure | Responsabilidade |
|---|---|---|
| `modules/storage.bicep` | ADLS Gen2 (HNS) + container | Data lake (bronze/silver/gold) |
| `modules/eventhub.bicep` | Event Hubs Namespace + hubs | Ingestão em tempo real |
| `modules/keyvault.bicep` | Key Vault (access policy) | Segredos da SPN consumidora (Databricks) |
| `modules/functionapp.bicep` | Function App + Plan + MI | Produção de eventos |
| `modules/databricks.bicep` | Workspace + Access Connector | Processamento + Unity Catalog |
| `modules/monitoring.bicep` | Log Analytics + App Insights + Action Group | Observabilidade |
| `modules/roles.bicep` | Role assignments (least privilege) | RBAC |

## Deploy

```bash
az group create -n rsgcjtecprd001 -l eastus2

# Pré-visualização (what-if)
az deployment group what-if -g rsgcjtecprd001 \
  -f infrastructure/bicep/main.bicep \
  -p infrastructure/bicep/params/prd.bicepparam

# Aplicar
az deployment group create -g rsgcjtecprd001 \
  -f infrastructure/bicep/main.bicep \
  -p infrastructure/bicep/params/prd.bicepparam
```

## Fronteira declarativa × imperativa

A criação da **Service Principal consumidora** (Databricks) e o **seed de segredos**
no Key Vault exigem Microsoft Graph e geram credenciais rotativas — fora do escopo
do ARM/Bicep. Essa etapa fica no bootstrap [`bootstrap.sh`](../bootstrap.sh). O produtor
não tem SPN: usa a Managed Identity do Function App (papel *Data Sender* dado pelo Bicep).
O Bicep cuida de todos os recursos de plataforma, do RBAC e das app settings; o
bootstrap cuida da SPN consumidora e dos segredos.
