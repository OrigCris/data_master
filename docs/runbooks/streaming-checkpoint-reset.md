# Runbook — Reset de checkpoint do streaming (Bronze)

**Quando usar**: o job `bronze-streaming` falha consistentemente por checkpoint
corrompido/incompatível (ex.: mudança de schema do stream) ou é preciso recomeçar a
leitura do Event Hubs.

> ⚠️ Resetar o checkpoint faz o job **reler** a partir da `startingPosition`
> configurada. Combine com a deduplicação da Bronze (chaves do Event Hubs) para não
> duplicar — ou aceite que o MERGE da Silver é idempotente.

## Localizar o checkpoint
O caminho é `{CHECKPOINT_BASE}/{eventhub_name}/{table_name}`, ex.:
`/Volumes/prd/b_dm_callcenter/checkpoints/bronze/evh_cj_tec_ura/ura_once`.

## Ação
1. **Parar** o job/stream em execução.
2. **Mover** (não apagar de imediato) o checkpoint para um caminho de backup:
   ```python
   dbutils.fs.mv(checkpoint_path, checkpoint_path + "_bak", recurse=True)
   ```
3. **Reexecutar**:
   ```bash
   dm run bronze-streaming -l layer_bronze
   ```
4. **Validar** ingestão (telemetria `numInputRows`) e contagens Bronze.
5. Após confirmar, **remover** o backup.

## Prevenção
- Versionar mudanças de schema do stream.
- Manter `CHECKPOINT_BASE` em Volume gerenciado (UC), com retenção.
