# 02. Modelo de Dados

O modelo de dados segue a arquitetura Medallion: dados crus na **Bronze**,
normalizados na **Silver** e modelados para consumo na **Gold**.

> Os diagramas ER (Mermaid) e o DDL físico completo estão versionados em
> [`database/mer/model.md`](../database/mer/model.md) e
> [`database/ddl/`](../database/ddl). Esta página resume as decisões de modelagem.

## Convenções de nomenclatura

A camada Silver/Gold adota um padrão de nomes compacto e consistente (estilo
*data warehouse* bancário), detalhado em [Referência Técnica](reference.md):

| Prefixo | Significado | Exemplo |
|---|---|---|
| `ID_` | identificador | `ID_CHAM`, `ID_ASST` |
| `DH_` | data/hora (timestamp) | `DH_INIC`, `DH_FIM` |
| `DT_` | data | `DT_INIC`, `DT_REFE` |
| `CD_` | código | `CD_PERI`, `CD_ULTI_OPCA` |
| `QT_` / `NR_` | quantidade / número | `QT_TRAF`, `NR_MEDI_TEMP_CHAM` |
| `IN_` | indicador (flag) | `IN_AUTN`, `IN_DERV_ATEN` |
| `VL_` / `PC_` | valor / percentual | `VL_NPS`, `PC_RECH` |

## Entidades

### Dimensões (Bronze)
- **`dim_clientes`** — cadastro de clientes. **Contém PII** (CPF, e-mail, nome,
  data de nascimento) → mascarada no Unity Catalog (ver [Governança](governance.md)).
- **`dim_assistentes`** — assistentes com hierarquia
  (supervisor → coordenador → gerente → superintendente).

### Fatos (Silver)
- **`tabe_ura_anlt`** — 1 linha por chamada de URA.
- **`tabe_calls`** — N linhas por chamada (etapas de atendimento humano). Chave
  composta `ID_CHAM` + `ID_ATEN`.
- **`tabe_pesq_ura`** — 1 linha por pesquisa de satisfação.

### Visões (Gold)
- **`visao_ura_calls`** — grão dia × fila.
- **`visao_assistentes`** — grão dia × assistente (com NPS).

## Decisões de modelagem

- **Chaves de negócio** (não surrogate) para o MERGE incremental — `ID_CHAM`
  identifica a chamada de ponta a ponta entre as fontes.
- **Período `CD_PERI` (yyyyMM)** como dimensão temporal de baixa cardinalidade,
  usada em todos os *cluster keys* para *data skipping*.
- **Metadados de CDF** (`_cv`, `_ct`) preservados na Silver para auditoria e
  reprocesso seguro.

---

[← Anterior: Apresentação](overview.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Camadas →](layers.md)
