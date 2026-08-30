# 14. Governança e Segurança de Dados

A governança combina **controle de acesso**, **mascaramento de PII** e **identidade
sem segredos**, usando recursos nativos do Azure e do Unity Catalog.

## Identidade e segredos (sem credenciais no código)
- **Produtor**: a **Managed Identity** da Function App tem *Azure Event Hubs Data
  Sender* no namespace — envia por OAuth, sem SAS keys e sem ler segredo algum.
- **Consumidor**: a SPN `spn_dtb_consumer` tem **apenas** *Azure Event Hubs Data
  Receiver* (no namespace) — **least privilege de verdade**: sem `Contributor`, sem
  acesso ao storage. Seus segredos ficam no **Key Vault**, lidos pelo secret scope do
  Databricks.
- O **Access Connector** do Databricks acessa o ADLS via MI (*Storage Blob Data
  Contributor*) para as MANAGED LOCATIONs do Unity Catalog — por isso o consumidor não
  precisa de papel no storage.
- O namespace do Event Hubs tem **`disableLocalAuth: true`**: SAS keys ficam
  desabilitadas, tudo é RBAC/Entra ID.

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
As funções e os `ALTER ... SET MASK` são gerados e aplicados pelo notebook
[`apply_pii_masks`](../Databricks/essential/apply_pii_masks.ipynb), que usa a lib
[`Databricks/lib/security`](../Databricks/lib/security):

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
