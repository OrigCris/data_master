# 11. Processamento de Dados (Silver)

A camada Silver transforma o dado cru da Bronze em tabelas limpas e normalizadas,
de forma **incremental** e **idempotente**.

## Padrão incremental (streaming CDF + checkpoint + MERGE)

O consumo Bronze→Silver é feito por **Structured Streaming** lendo o **Change Data
Feed** da Bronze como fonte, com **`Trigger.AvailableNow`** (processa todo o backlog
em micro-batches e encerra) e **`foreachBatch`** aplicando **MERGE** idempotente. O
**checkpoint** do stream controla o progresso por fonte, com garantia de
*exactly-once* (ver [ADR-0002](adrs/0002-incremental-streaming-cdf.md)).

O ciclo, encapsulado em [`Databricks/lib/transforms`](../Databricks/lib/transforms):

```python
from transforms import SilverStream

stream = SilverStream(spark)
stream.run(
    source_fqn="prd.b_dm_callcenter.ura_once",
    target_fqn="prd.s_dm_callcenter.tabe_ura_anlt",
    transform=transform,                       # parse + normalização (callable)
    keys=["ID_CHAM"],
    checkpoint_location="/Volumes/.../checkpoints/silver/tabe_ura_anlt",
    cluster_by=["CD_PERI", "DT_INIC", "ID_CHAM"],
)
```

1. **Stream do CDF** — `readStream` com `readChangeFeed=true` e `Trigger.AvailableNow`.
2. **foreachBatch** — para cada micro-batch: filtra `_change_type = insert`, aplica o
   `transform` e faz `MERGE` por chave de negócio.
3. **Transform** — `from_json` do `body` com `StructType`, renomeação para o padrão
   do projeto e derivação de `CD_PERI`/datas/auditoria.
4. **Checkpoint** — controla o offset/versão processado (exactly-once); reprocessar é
   resetar o checkpoint (ver runbook [streaming-checkpoint-reset](runbooks/streaming-checkpoint-reset.md)).

> O padrão de CDF/MERGE é centralizado em `transforms.SilverStream` e exercitado por
> testes em [`tests/unit/test_transforms.py`](../tests/unit/test_transforms.py), de
> modo que a regra de idempotência roda no CI sem cluster Spark.

## Transformações por tabela

| Tabela Silver | Chave MERGE | Derivações específicas |
|---|---|---|
| `tabe_ura_anlt` | `ID_CHAM` | flags `IN_AUTN`, `IN_DERV_ATEN` |
| `tabe_calls` | `ID_CHAM`, `ID_ATEN` | `IN_TRAF`, `IN_TRAF_INDV` (via `lead` por chamada) |
| `tabe_pesq_ura` | `ID_CHAM` | `VL_NOTA`, `DT_ENVI` |

## Data Quality (gate)

Cada execução pode validar o *staged* com o framework de expectativas:

```python
from quality import Expectation, run_expectations

report = run_expectations(staged, [
    Expectation.not_null("ID_CHAM"),
    Expectation.between("VL_NOTA", 1, 10),
], dataset="silver.tabe_pesq_ura")
report.raise_if_critical_failed()                 # falha o job em violação crítica
report.to_table(spark, "prd.s_dm_callcenter.__dq_results")
```

---

[← Anterior: Ingestão](ingestion.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Analytics →](analytics.md)
