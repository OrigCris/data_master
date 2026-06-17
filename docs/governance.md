# 14. Governança e Segurança de Dados

A governança combina **controle de acesso**, **mascaramento de PII** e **identidade
sem segredos**, usando recursos nativos do Azure e do Unity Catalog.

## Identidade e segredos (sem credenciais no código)
- **Managed Identity** da Function App lê o **Key Vault** (RBAC `Key Vault Secrets
  User`); nenhuma credencial fica em configuração.
- **Service Principals** distintas para produzir (`spn_func_send`, *Event Hubs Data
  Sender*) e consumir (`spn_dtb_consumer`, *Storage Blob Data Contributor*) —
  **least privilege**.
- O **Access Connector** do Databricks acessa o ADLS via MI para as MANAGED LOCATIONs
  do Unity Catalog.

## Controle de acesso (Unity Catalog)
- Catálogo `prd` com schemas por camada (`b_/s_/g_`).
- **GRANT por camada**: consumidores de BI recebem `SELECT` apenas na **Gold**; a
  PII fica restrita à Bronze para grupos autorizados (ver [`004_governance.sql`](../database/ddl/004_governance.sql)).

## Mascaramento de PII (no catálogo)

A `dim_clientes` contém **CPF, e-mail, nome e data de nascimento**. O mascaramento
é imposto por **column mask** do Unity Catalog — vale para **qualquer** consumidor,
não depende do ETL:

```sql
ALTER TABLE prd.b_dm_callcenter.dim_clientes
  ALTER COLUMN cpf SET MASK prd.b_dm_callcenter.mask_cpf;
```

A função libera o valor em claro apenas para `is_account_group_member('dm_pii_readers')`.
Estratégias e geração programática em [`Databricks/lib/security`](../Databricks/lib/security):

| Função | Comportamento |
|---|---|
| `mask_cpf` | `123.***.***-09` |
| `mask_email` | `c***@dominio.com` |
| `mask_name` | primeiro nome + iniciais |
| data de nascimento | generalizada para o ano |

> As funções puras de mascaramento têm testes em
> [`tests/unit/test_pii.py`](../tests/unit/test_pii.py).

## Auditoria e lineage
- O **lineage** do Unity Catalog rastreia o fluxo bronze→silver→gold automaticamente.
- A tabela `__dq_results` registra o histórico de qualidade.
- Evolução: integração com **Microsoft Purview** para catálogo corporativo e
  classificação automática ([Roadmap](roadmap.md)).

---

[← Anterior: Observabilidade](observability.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: FinOps →](finops.md)
