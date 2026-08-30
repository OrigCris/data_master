# ADR-0005 — Mascaramento de PII no catálogo (Unity Catalog)

- **Status**: Aceito
- **Contexto**: a `dim_clientes` contém PII (CPF, e-mail, nome, data de nascimento).
  É preciso proteger o dado sensível em todas as camadas e para todos os consumidores.

## Decisão
Impor o mascaramento via **column mask do Unity Catalog**, liberando o valor em
claro apenas a `is_account_group_member('dm_pii_readers')`. O controle vive **no
catálogo**, não no pipeline.

## Alternativas
- **Mascarar no ETL** — depende de cada job lembrar de mascarar; um consumidor que
  leia a tabela direto veria o dado cru.
- **Vistas dinâmicas** — funcionam, mas duplicam objetos; *column mask* é mais limpo.
- **Serviço externo de detecção (ex.: Presidio)** — útil para descoberta automática;
  complementar, no [Roadmap](../roadmap.md) via Purview.

## Consequências
- (+) Proteção uniforme e auditável, independente do consumidor.
- (+) Funções puras de mascaramento reutilizáveis e **testadas**.
- (−) Requer grupos do Entra ID sincronizados no workspace.

Relacionado: [Governança](../governance.md), [`lib/security`](../../Databricks/lib/security).
