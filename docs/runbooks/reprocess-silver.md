# Runbook — Reprocessar uma fonte (Silver)

**Quando usar**: a Silver de uma fonte ficou inconsistente e é preciso reprocessar
desde o início da Bronze.

> A Silver consome a Bronze como **stream Delta + checkpoint** (sem tabela de controle).
> O progresso vive no **checkpoint** da fonte; reprocessar = resetar esse checkpoint.
> O MERGE é idempotente, então reprocessar **não duplica**.

## Diagnóstico
```sql
DESCRIBE HISTORY prd.b_dm_callcenter.ura_once;          -- versões disponíveis na Bronze
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
4. **Reexecutar** o job — sem checkpoint, o stream Delta processa todo o snapshot da
   Bronze (backfill) e o novo checkpoint assume a partir daí:
   ```bash
   dm run silver-job -l layer_silver
   ```
5. **Validar** com DQ e contagens; conferir `__dq_results`. Após confirmar, remover o
   backup do checkpoint.

> O MERGE por chave torna o backfill seguro mesmo que a Silver não tenha sido truncada:
> registros existentes são atualizados, não duplicados.
