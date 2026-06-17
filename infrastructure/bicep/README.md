# Infraestrutura como Código — Bicep modular

Provisionamento declarativo e idempotente do ambiente Azure do Data Master.
Substitui o script imperativo [`create_resouce.sh`](../create_resouce.sh) (mantido
apenas como *bootstrap* para a parte de Entra ID/segredos) por **módulos por
domínio**, espelhando a ideia de "componentização por stacks" do case de referência.

## Mapa de módulos (≈ "stacks")

| Módulo | Recurso Azure | Equivalente AWS (case de referência) |
|---|---|---|
| `modules/storage.bicep` | ADLS Gen2 (HNS) + container | `storage.yml` (S3) |
| `modules/eventhub.bicep` | Event Hubs Namespace + hubs | `streaming.yml` (Kinesis) |
| `modules/keyvault.bicep` | Key Vault (RBAC) | `security.yml` (Secrets/KMS) |
| `modules/functionapp.bicep` | Function App + Plan + MI | `functions.yml` (Lambda) |
| `modules/databricks.bicep` | Workspace + Access Connector | `processing.yml` (EMR/Glue) |
| `modules/monitoring.bicep` | Log Analytics + App Insights + Action Group | `observability.yml` |
| `modules/roles.bicep` | Role assignments (least privilege) | `roles.yml` |

## Deploy

```bash
az group create -n rsgcjtecprd001 -l brazilsouth

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

A criação dos **Service Principals** (produtor/consumidor) e o **seed de segredos**
no Key Vault exigem Microsoft Graph e geram credenciais rotativas — fora do escopo
do ARM/Bicep. Essa etapa permanece no bootstrap [`scripts`](../create_resouce.sh)
ou na CLI do projeto (`dm provision --seed-secrets`). O Bicep cuida de todos os
recursos de plataforma e do RBAC; o bootstrap cuida da identidade e dos segredos.
