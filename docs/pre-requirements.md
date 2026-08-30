# 07. Pré-Requisitos

## Conta e permissões Azure
- Assinatura Azure ativa com permissão para criar Resource Groups e recursos.
- Função **Owner** ou **Contributor + User Access Administrator** no escopo do RG
  (necessário para criar *role assignments* via Bicep).
- Permissão para criar **Service Principals** no Entra ID (bootstrap de segredos).
- **Unity Catalog** habilitado no workspace Databricks (catálogo `prd`).

## Ferramentas locais
| Ferramenta | Versão | Uso |
|---|---|---|
| Azure CLI (`az`) | ≥ 2.60 | Provisionamento / bootstrap |
| Bicep | ≥ 0.27 | IaC (`az bicep`) |
| Databricks CLI | ≥ 0.220 | Asset Bundles |
| Python | 3.11 | Function App, libs, CLI, testes |
| Git | — | Versionamento |

## Quotas e SKUs (ambiente de demo)
- ADLS Gen2 `Standard_LRS`; Event Hubs `Standard`; Function App plano `B1`;
  Databricks `Premium`. Ajuste conforme o ambiente — ver [FinOps](finops.md).

## Verificação rápida
```bash
az version && az bicep version
databricks version
python --version
pip install -r tests/requirements-dev.txt && pytest -q
```

---

[← Anterior: Trade-offs](trade-offs.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Instalação →](installation.md)
