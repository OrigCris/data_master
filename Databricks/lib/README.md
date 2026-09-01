# `Databricks/lib` — Bibliotecas compartilhadas

Código reutilizável pelos notebooks das camadas, mantido fora dos notebooks para
ser **versionável, testável e livre de duplicação**. Cada pacote é importável
tanto pelos jobs no Databricks quanto pela suíte de testes local (`tests/`).

| Pacote | Responsabilidade | Principais APIs |
|---|---|---|
| [`transforms/`](transforms) | Padrão incremental Bronze→Silver (streaming Delta + checkpoint + MERGE) e helpers de parsing/contrato. | `SilverStream`, `merge_upsert`, `parse_body`, `validate_contract`, `rename_columns`, `add_period_and_dates` |
| [`quality/`](quality) | Framework de Data Quality declarativo com relatório e gate de criticidade. | `Expectation`, `run_expectations`, `QualityReport` |
| [`security/`](security) | Mascaramento de PII (funções puras + Spark) e geração de *column masks* do Unity Catalog. | `mask_cpf`, `mask_email`, `mask_dataframe`, `column_mask_functions_sql` |

## Empacotamento e consumo

A lib é distribuída como **wheel** (`pyproject.toml` aqui). O bundle
[`layer_silver`](../layer_silver/databricks.yml) constrói o wheel (`artifacts`) e o
anexa aos jobs (`libraries`), então os notebooks dos jobs importam `from transforms
...` sem depender de Repos. Em execução **interativa** (dev), os notebooks também
funcionam via `sys.path.append("/Workspace/Repos/.../Databricks/lib")`.

Build local do wheel:

```bash
cd Databricks/lib && python -m build --wheel   # gera dist/dm_callcenter_lib-*.whl
```

Exemplo dentro de um notebook Silver:

```python
import sys; sys.path.append("/Workspace/Repos/<repo>/Databricks/lib")
from transforms import SilverStream
from quality import Expectation

stream = SilverStream(spark)
stream.run(
    source_table_fqn="prd.b_dm_callcenter.ura_once",
    target_table_fqn="prd.s_dm_callcenter.tabe_ura_anlt",
    transform=transform,                       # callable: micro_df -> staged_df
    keys=["ID_CHAM"],
    checkpoint_location="/Volumes/.../checkpoints/silver/tabe_ura_anlt",
    cluster_by=["CD_PERI", "DT_INIC", "ID_CHAM"],
    expectations=[Expectation.not_null("ID_CHAM")],   # gate de DQ por micro-batch
    dq_results_table="prd.s_dm_callcenter.__dq_results",
)
```

> As funções puras (`build_merge_on`, `mask_cpf`, expectations) têm cobertura de
> testes em [`tests/unit`](../../tests/unit) e rodam no CI sem cluster Spark.
