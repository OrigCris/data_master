# 05. Componentização da Arquitetura

A infraestrutura é dividida em **módulos Bicep** por domínio, em
[`infrastructure/bicep/modules`](../infrastructure/bicep/modules). Cada módulo é
revisável e aplicável com `what-if` isoladamente.

## Mapa de componentes

| Módulo Bicep | Recurso Azure | Responsabilidade |
|---|---|---|
| `storage.bicep` | ADLS Gen2 (HNS) | Data lake (bronze/silver/gold) |
| `eventhub.bicep` | Event Hubs Namespace + 3 hubs | Ingestão em tempo real |
| `keyvault.bicep` | Key Vault (RBAC) | Segredos do SPN e do Event Hubs |
| `functionapp.bicep` | Function App + Plan + MI | Produção de eventos |
| `databricks.bicep` | Workspace + Access Connector | Processamento + Unity Catalog |
| `monitoring.bicep` | Log Analytics + App Insights + Action Group | Observabilidade |
| `roles.bicep` | Role assignments | RBAC *least privilege* |

O orquestrador [`main.bicep`](../infrastructure/bicep/main.bicep) compõe os módulos
e propaga *outputs* (FQDN do Event Hubs, URI do Key Vault, principalIds) entre eles
— sem hardcode de nomes.

## Camadas de processamento (Asset Bundles)

Cada camada Databricks é um bundle independente, versionado com seus jobs e
clusters:

| Bundle | Diretório | Jobs |
|---|---|---|
| `bronze-callcenter` | `Databricks/layer_bronze` | `bronze-dim`, `bronze-streaming` |
| `silver-callcenter` | `Databricks/layer_silver` | `silver-job` |
| `gold-callcenter` | `Databricks/layer_gold` | `gold-job` |
| `orchestration-callcenter` | `Databricks/orchestration` | `dm-pipeline` (encadeia as camadas por `depends_on`) |

O bundle `orchestration` é publicado **por último**: ele resolve os job ids das
camadas por nome (variável `lookup`), então elas precisam já existir no workspace.

## Fronteira declarativa × imperativa

O Bicep cuida de **todos os recursos de plataforma + RBAC**. A criação dos
**Service Principals** (Entra ID) e o **seed de segredos** dependem do Microsoft
Graph e de credenciais rotativas — ficam no bootstrap
[`bootstrap.sh`](../infrastructure/bootstrap.sh), executado após o Bicep.

---

[← Anterior: Arquitetura](architecture.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Trade-offs →](trade-offs.md)
