# 16. Benchmark e Performance

Experimento reprodutível para medir performance e escala do caminho arquitetural
central (streaming Delta + `foreachBatch` MERGE). O harness gera carga controlada, mede a execução
**real** e registra os números — a tabela de resultados abaixo é preenchida rodando os
cenários, não estimada.

## Harness
O notebook [`Databricks/essential/benchmark.ipynb`](../Databricks/essential/benchmark.ipynb)
recebe `scenario`, `volume`, `num_workers` e `node_type`, gera a carga sintética na
Bronze (append-only), executa a Silver medindo `duration_s`/`throughput_rows_s` e faz
*append* em `__benchmark_results`. Cada cenário é uma linha acumulada nessa tabela.

## Metodologia
1. Definir o cluster no bundle (`num_workers`, `node_type`) e rodar o harness com o
   `volume` do cenário.
2. As métricas saem da execução real: duração cronometrada, linhas de saída e
   throughput; o custo vem do DBU × tempo (ver [FinOps](finops.md)).
3. Repetir 3× por cenário e tomar a mediana.

## Cenários (matriz de execução)
Três cenários isolam o efeito do **volume** (A→B) e do **paralelismo** (B→C):

| Cenário | Volume | Cluster | duração (s) | throughput (rows/s) | custo (DBU×t) |
|---|---|---|---|---|---|
| A | 1M | `D4ps_v6` × 1 | _(preencher)_ | _(preencher)_ | _(preencher)_ |
| B | 10M | `D4ps_v6` × 1 | _(preencher)_ | _(preencher)_ | _(preencher)_ |
| C | 10M | `D4ps_v6` × 2 | _(preencher)_ | _(preencher)_ | _(preencher)_ |

> Os campos ficam em branco de propósito: preencha com a saída de `__benchmark_results`
> após rodar cada cenário. A leitura interessante é a **eficiência de scaling** (B→C):
> dobrar workers raramente reduz o tempo pela metade — quando o gargalo deixa de ser
> CPU e passa a ser I/O/shuffle, o ganho satura. Use o Spark UI (stages, *shuffle
> read/write*, *spill*) para atribuir o gargalo.

## Eixos avaliados

| Eixo | O que medir | Onde ler |
|---|---|---|
| **Latência de ingestão** | Event Hubs → Bronze (`AvailableNow`) | `numInputRows`/`batchDuration` do `lastProgress` |
| **Throughput Silver** | linhas/s no MERGE incremental | `__benchmark_results.throughput_rows_s` |
| **Custo por execução** | DBU × tempo | [FinOps](finops.md) |
| **Eficiência de leitura** | arquivos varridos na Gold | *data skipping* (liquid clustering + `replaceWhere`) |

## Boas práticas que sustentam a performance
- **Processar só o que chegou** (stream incremental) em vez de full scan.
- **Liquid clustering** por período → *data skipping*.
- **`OPTIMIZE`** nas dimensões após overwrite.
- **Clusters job-scoped** dimensionados ao trabalho.

## Escala futura
Para volumes muito maiores: aumentar workers/autoscaling, particionar Event Hubs
(mais partições), e avaliar **Databricks SQL Serverless** para o consumo analítico
(ver [Roadmap](roadmap.md)).

---

[← Anterior: FinOps](finops.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Roadmap →](roadmap.md)
