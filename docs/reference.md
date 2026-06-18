# 18. Referência Técnica

## Convenção de nomenclatura de recursos Azure
Padrão `<tipo><app><amb><seq>`, ex.: `stacjtecprd001` (storage), `evhnscjtecprd001`
(Event Hubs namespace), `akvcjtecprd001` (Key Vault), `dbwcjtecprd001` (Databricks).

| Abreviação | Recurso |
|---|---|
| `rsg` | Resource Group |
| `sta` | Storage Account |
| `evhns` / `evh` | Event Hubs namespace / hub |
| `akv` | Key Vault |
| `func` / `asp` | Function App / App Service Plan |
| `dbw` | Databricks Workspace |
| `log` / `appi` / `ag` | Log Analytics / App Insights / Action Group |

## Schemas do Unity Catalog
| Camada | Schema | Prefixo |
|---|---|---|
| Bronze | `b_dm_callcenter` | `b_` |
| Silver | `s_dm_callcenter` | `s_` |
| Gold | `g_dm_callcenter` | `g_` |

## Prefixos de coluna (Silver/Gold)
`ID_` identificador · `DH_` timestamp · `DT_` data · `CD_` código · `QT_`/`NR_`
quantidade/número · `IN_` indicador · `VL_`/`PC_` valor/percentual · `DS_` descrição
· `NM_` nome.

## Estrutura do repositório
```
├── cli/                  # CLI `dm` (Typer)
├── database/             # DDL (migrations) + MER
├── Databricks/
│   ├── essential/        # criação de schemas + governança de PII
│   ├── layer_bronze|silver|gold/   # Asset Bundles + notebooks
│   ├── orchestration/    # job dm-pipeline (encadeia as camadas por dependência)
│   └── lib/              # transforms, quality, security (compartilhado/testado)
├── docs/                 # esta documentação (+ adrs, runbooks)
├── function_app/         # produtor de eventos (Azure Functions)
├── infrastructure/       # Bicep modular + bootstrap
├── monitoring/           # dashboard + alertas
└── tests/                # pytest (unit)
```

## Tabelas auxiliares e progresso
- **Progresso da Silver**: controlado pelo **checkpoint** do streaming por fonte, em
  `/Volumes/.../checkpoints/silver/<tabela>`.
- `s_dm_callcenter.__dq_results` — histórico de Data Quality.

---

[← Anterior: Roadmap](roadmap.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Considerações →](considerations.md)
