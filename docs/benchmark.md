# 16. Benchmark e Performance

Metodologia e resultados esperados para validar performance e escala do pipeline.
Os números abaixo são **referências de ordem de grandeza** para o ambiente de demo
(`Standard_D4ps_v6`, 1 worker, `AvailableNow`); reexecute em seu ambiente para medir.

## Metodologia
1. Gerar carga controlada ajustando os parâmetros do bundle Bronze
   (`QTD_CLIENTES`, `QTD_ASSIST`) e a frequência do TimerTrigger.
2. Medir por camada usando a telemetria nativa:
   - Bronze: `numInputRows` / `batchDuration` do `lastProgress`.
   - Silver/Gold: duração do job + linhas afetadas pelo MERGE/overwrite.
3. Repetir 3× e tomar a mediana; registrar custo via [FinOps](finops.md).

## Eixos avaliados

| Eixo | O que medir | Expectativa |
|---|---|---|
| **Latência de ingestão** | Event Hubs → Bronze (`AvailableNow`) | dominada pelo *cold start* do cluster (~1–3 min) |
| **Throughput Silver** | linhas/s no MERGE incremental | escala linear com o tamanho do delta (CDF) |
| **Custo por execução** | DBU × tempo | minimizado por autotermination + cluster pequeno |
| **Eficiência de leitura** | arquivos varridos na Gold | reduzida por liquid clustering + `replaceWhere` |

## Boas práticas que sustentam a performance
- **Processar só o delta** (CDF) em vez de full scan.
- **Liquid clustering** por período → *data skipping*.
- **`OPTIMIZE`** nas dimensões após overwrite.
- **Clusters job-scoped** dimensionados ao trabalho.

## Escala futura
Para volumes muito maiores: aumentar workers/autoscaling, particionar Event Hubs
(mais partições), e avaliar **Databricks SQL Serverless** para o consumo analítico
(ver [Roadmap](roadmap.md)).

---

[← Anterior: FinOps](finops.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Roadmap →](roadmap.md)
