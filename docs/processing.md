# 11. Processamento de Dados (Silver)

A camada Silver transforma o dado **estruturado** da Bronze em tabelas limpas e
normalizadas, de forma **incremental** e **idempotente** — sem refazer `from_json`.

## Padrão incremental (streaming Delta + checkpoint + MERGE)

O consumo Bronze→Silver é feito por **Structured Streaming** lendo a Bronze como
**fonte de streaming Delta** (`readStream.format("delta")`), com **`Trigger.AvailableNow`**
(processa todo o backlog em micro-batches e encerra) e **`foreachBatch`** aplicando
**MERGE** idempotente. Como a Bronze é **append-only**, o stream já entrega só as linhas
novas (ver [ADR-0002](adrs/0002-incremental-streaming.md)).
O **checkpoint** controla o progresso por fonte. Como uso `foreachBatch`, a escrita é
**at-least-once**; a ausência de duplicidade vem do **MERGE por chave de negócio**,
projetado para ser idempotente em reexecuções.

O ciclo, encapsulado em [`Databricks/lib/transforms`](../Databricks/lib/transforms):

```python
from transforms import SilverStream

stream = SilverStream(spark)
stream.run(
    source_table_fqn="prd.b_dm_callcenter.ura_once",
    target_table_fqn="prd.s_dm_callcenter.tabe_ura_anlt",
    transform=transform,                       # normalização (callable; a Bronze já estruturou)
    keys=["ID_CHAM"],
    checkpoint_location="/Volumes/.../checkpoints/silver/tabe_ura_anlt",
    cluster_by=["CD_PERI", "DT_INIC", "ID_CHAM"],
)
```

1. **Stream Delta** — `readStream.format("delta")` com `skipChangeCommits=true` e
   `Trigger.AvailableNow` (ignora reescritas de `OPTIMIZE`; a Bronze só cresce por append).
2. **foreachBatch** — para cada micro-batch: aplica o `transform` e faz `MERGE` por
   chave de negócio.
3. **Transform** — projeção/renomeação dos campos já estruturados para o padrão do
   projeto e derivação de `CD_PERI`/datas/auditoria (sem `from_json` — a Bronze já parseou).
4. **Checkpoint** — controla o offset/versão processado (progresso do stream);
   reexecuções de micro-batch são absorvidas pelo MERGE idempotente. Reprocessar do
   zero é resetar o checkpoint (ver runbook [streaming-checkpoint-reset](runbooks/streaming-checkpoint-reset.md)).

> O padrão de streaming/MERGE é centralizado em `transforms.SilverStream` e exercitado por
> testes em [`tests/unit/test_transforms.py`](../tests/unit/test_transforms.py), de
> modo que a regra de idempotência roda no CI sem cluster Spark.

## Transformações por tabela

| Tabela Silver | Chave MERGE | Derivações específicas |
|---|---|---|
| `tabe_ura_anlt` | `ID_CHAM` | flags `IN_AUTN`, `IN_DERV_ATEN` |
| `tabe_calls` | `ID_CHAM`, `ID_ATEN` | `IN_TRAF`, `IN_TRAF_INDV` (recomputados sobre a chamada inteira — ver abaixo) |
| `tabe_pesq_ura` | `ID_CHAM` | `VL_NOTA`, `DT_ENVI` |

### Recomputação por chave (eventos entre micro-batches)

Os indicadores de transferência de `tabe_calls` (`IN_TRAF`/`IN_TRAF_INDV`) dependem de
**todos os atendimentos de uma chamada** — uma janela `lead` por `ID_CHAM`. Num stream,
não se pode assumir que os atendimentos correlatos cheguem no mesmo micro-batch.

Por isso o `SilverStream` suporta uma etapa de **recomputação por chave**: para cada
`ID_CHAM` presente no batch, ele junta os atendimentos novos ao **histórico já gravado
na Silver** e recalcula os indicadores sobre a chamada inteira, antes do MERGE.

```python
SilverStream(spark).run(
    ...,
    recompute=recompute,          # aplica a janela sobre o conjunto completo da chave
    recompute_keys=["ID_CHAM"],   # escopo recarregado do alvo (leitura limitada às chaves tocadas)
)
```

Como a Silver é a fonte da verdade, um atendimento que chega atrasado reconcilia a
chamada corretamente — **sem `watermark` e sem perder dado** (ver
[Trade-offs](trade-offs.md)).

## Data Quality (gate)

Cada notebook Silver passa um conjunto de **expectativas** para o `SilverStream`. A
cada micro-batch, antes do MERGE, o gate valida o *staged*, registra o resultado em
`__dq_results` e **interrompe** o batch em caso de falha crítica:

```python
from quality import Expectation

checks = [
    Expectation.not_null("ID_CHAM"),
    Expectation.unique("ID_PESQ"),
    Expectation.between("VL_NOTA", 0, 10),
]

SilverStream(spark).run(
    source_table_fqn="prd.b_dm_callcenter.surveys_once",
    target_table_fqn="prd.s_dm_callcenter.tabe_pesq_ura",
    transform=transform,
    keys=["ID_CHAM"],
    checkpoint_location="/Volumes/.../checkpoints/silver/tabe_pesq_ura",
    expectations=checks,
    dq_results_table="prd.s_dm_callcenter.__dq_results",
)
```

Severidade `critical` falha o job; `warn` apenas registra. O histórico fica em
[`__dq_results`](../database/ddl/002_silver.sql).

## Data Contract e Quarentena (DLQ)

O **parse estrutural** contra o contrato versionado acontece na Bronze
([`transforms.contracts`](../Databricks/lib/transforms/contracts.py)). Na Silver, antes
do gate de linha, cada micro-batch reforça o contrato validando os **campos
obrigatórios** sobre as colunas já estruturadas (sem refazer `from_json`). Um evento com
campo obrigatório ausente/incompatível — inclusive vindo de payload malformado, cujo
parse na Bronze produziu nulos — não é descartado em silêncio: é isolado na **quarentena**
(`__quarantine`) com o **payload original** e o motivo (`missing_or_invalid: <campos>`).

```python
SilverStream(spark).run(
    ...,
    contract_required=["id_chamada", ...],# campos que não podem faltar
    quarantine_table="prd.s_dm_callcenter.__quarantine",
)
```

A escrita da quarentena é **idempotente por `event_id`** (`merge_quarantine`): como o
`foreachBatch` é at-least-once, um retry do mesmo micro-batch não gera duplicidade na
DLQ. Assim, dado inválido **não some** e também **não contamina** a camada confiável;
a quarentena fica disponível para triagem e reprocessamento (ver [Roadmap](roadmap.md)).

## Observabilidade de dataset

As *expectations* olham a **linha**; a observabilidade olha o **dataset ao longo do
tempo**. Após cada execução, [`run_observability`](../Databricks/lib/quality/observability.py)
registra métricas em `__dataset_metrics` e as compara com a janela anterior:

- **Volume**: as linhas da data mais recente contra a **média móvel** das execuções
  passadas — fora de `[0.7, 1.3] × média` é anomalia. Um dia com 40 mil eventos onde
  normalmente entram milhões não viola `not_null` nem `between`, mas é sinalizado aqui.
- **Freshness**: minutos desde o evento mais recente, contra um limite configurável.

As checagens são `warn` por padrão (sinalizam sem interromper), com a lógica de decisão
em funções puras testadas no CI ([`test_observability.py`](../tests/unit/test_observability.py)).

---

[← Anterior: Ingestão](ingestion.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Analytics →](analytics.md)
