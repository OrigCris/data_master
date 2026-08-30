# 12. Geração de Dados Analíticos (Gold)

A Gold materializa **visões diárias (D-1)** prontas para consumo, com
`replaceWhere` por `DT_REFE` (reescreve só a partição do dia, preserva histórico).

## `visao_ura_calls` — dia × fila

Cruza `tabe_ura_anlt` (URA) com `tabe_calls` (atendimentos) e agrega por fila:

| Métrica | Significado |
|---|---|
| `NR_MED_OPCA_NAVG` | média de opções navegadas |
| `NR_MED_OPCA_AUTO_SERV` / `NR_MED_OPCA_DERV` | média de opções em autoatendimento × derivadas |
| `QT_AUTN`, `QT_DERV_ATEN` | autenticadas / derivadas |
| `QT_TRAF`, `QT_TRAF_INDV` | transferências / transferências indevidas |
| `NR_MEDI_TEMP_CHAM` | tempo médio de chamada (s) |

## `visao_assistentes` — dia × assistente

Cruza `tabe_calls` + `tabe_pesq_ura` + `dim_assistentes` (hierarquia), com:

| Métrica | Significado |
|---|---|
| `QT_CHAM_ATEN`, `VL_TEMP_MEDI_OPER` | volume e TMA |
| `PC_TRAF`, `PC_TRAF_INDV`, `PC_RECH` | percentuais de transferência/rechamada |
| `QT_PRMT`/`QT_NTRO`/`QT_DETR` | promotores/passivos/detratores |
| `VL_NPS` | `(promotores − detratores) / total × 100` |

### Regra de NPS
Faixas do **NPS clássico**, na escala **0–10**: **promotor 9–10**, **passivo 7–8**,
**detrator 0–6**. O `VL_NPS` é `(promotores − detratores) / total × 100`.

## Padrão de materialização
```python
if not spark.catalog.tableExists(nm_tabe_final):
    # cria vazia com o schema do resultado + CLUSTER BY (CD_PERI, DT_REFE, <chave>)
result.write.mode("overwrite") \
      .option("replaceWhere", f"DT_REFE = '{odate}'") \
      .saveAsTable(nm_tabe_final)
```

> O clustering por `(CD_PERI, DT_REFE, <chave>)` garante *data skipping* nos
> dashboards que filtram por período.

---

[← Anterior: Processamento](processing.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Observabilidade →](observability.md)
