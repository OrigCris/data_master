# ADR-0001 — Medallion com Delta Lake + Unity Catalog

- **Status**: Aceito
- **Data**: 2025
- **Contexto**: precisamos de um formato de tabela transacional e de um catálogo
  governado para o data lake no Azure, equivalente ao Iceberg + Glue do case de
  referência (AWS).

## Decisão
Adotar **arquitetura Medallion** (bronze/silver/gold) com **Delta Lake** como
formato e **Unity Catalog** como catálogo/governança, no Azure Databricks.

## Alternativas consideradas
- **Apache Iceberg + catálogo externo** — ótimo, mas menos integrado ao Databricks
  no Azure; CDF/time-travel exigiriam mais peças.
- **Parquet puro + Hive Metastore** — sem ACID, sem CDF nativo, sem governança
  centralizada.

## Consequências
- (+) ACID, time-travel e **Change Data Feed** nativos (base do incremental).
- (+) Catálogo, **lineage** e **column masking** centralizados no Unity Catalog.
- (−) Acoplamento ao ecossistema Databricks.

Relacionado: [ADR-0002](0002-incremental-streaming-cdf.md), [Layers](../layers.md).
