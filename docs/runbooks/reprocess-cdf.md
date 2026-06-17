# Runbook — Reprocessar uma fonte (Silver)

**Quando usar**: a Silver de uma fonte ficou inconsistente e é preciso reprocessar
desde o início (ou de uma versão específica) da Bronze.

> A Silver consome o CDF da Bronze por **streaming + checkpoint** (sem tabela de
> controle). O progresso vive no **checkpoint** da fonte; reprocessar = resetar esse
> checkpoint. O MERGE é idempotente, então reprocessar **não duplica**.

## Diagnóstico
```sql
DESCRIBE HISTORY prd.b_dm_callcenter.ura_once;          -- versões disponíveis no CDF
SELECT count(*) FROM prd.s_dm_callcenter.tabe_ura_anlt; -- conferir consistência
SELECT * FROM prd.s_dm_callcenter.__dq_results
 WHERE dataset = 'silver.tabe_ura_anlt' ORDER BY checked_at DESC;
```

## Ação
1. **Localizar o checkpoint** da fonte:
   `/Volumes/prd/s_dm_callcenter/checkpoints/silver/<silver_table>`.
2. **Mover** o checkpoint para um backup (não apagar de imediato):
   ```python
   ckpt = "/Volumes/prd/s_dm_callcenter/checkpoints/silver/tabe_ura_anlt"
   dbutils.fs.mv(ckpt, ckpt + "_bak", recurse=True)
   ```
3. (Opcional) **Truncar a Silver** se quiser reconstruir do zero:
   ```sql
   TRUNCATE TABLE prd.s_dm_callcenter.tabe_ura_anlt;
   ```
4. **Reexecutar** o job — `SilverStream(starting_version=0)` faz o backfill de todo o
   histórico do CDF e o novo checkpoint assume a partir daí:
   ```bash
   dm run silver-job -l layer_silver
   ```
5. **Validar** com DQ e contagens; conferir `__dq_results`. Após confirmar, remover o
   backup do checkpoint.

> Para reprocessar a partir de uma versão intermediária (não do zero), ajuste
> `starting_version` no widget/parâmetro do notebook antes de recriar o checkpoint.
