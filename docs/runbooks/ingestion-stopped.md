# Runbook — Ingestão parada (sem eventos na Bronze)

**Disparo**: alerta `evh-sem-ingestao` (`IncomingMessages = 0` por 30 min) ou
Bronze sem novas linhas.

## Triagem (do produtor ao consumidor)
1. **Function App** está rodando?
   - App Insights → falhas/exceções; métrica `Http5xx`.
   - Causa comum: SPN sem segredo válido no Key Vault.
   ```bash
   az functionapp show -g rsgcjtecprd001 -n funccjtecprd001 --query state
   ```
2. **Segredos do SPN** existem e estão corretos?
   ```bash
   az keyvault secret show --vault-name akvcjtecprd001 -n ServicePrincipalAppId --query value
   ```
   - A MI da Function tem `Key Vault Secrets User`? (RBAC)
3. **Permissão de envio** ao Event Hubs?
   - O SPN produtor precisa de `Azure Event Hubs Data Sender` no namespace.
4. **Event Hubs** saudável?
   ```bash
   az eventhubs eventhub show -g rsgcjtecprd001 --namespace-name evhnscjtecprd001 -n evh_cj_tec_ura
   ```
5. **Consumo Bronze** (trigger-once) executou? Verifique o run do job
   `bronze-streaming` e o `lastProgress`.

## Resolução
- Corrigir o elo quebrado (segredo, RBAC ou estado da Function) e reexecutar:
  ```bash
  dm run bronze-streaming -l layer_bronze
  ```
- Se houve janela > 1h sem consumo, parte dos eventos pode ter expirado (retenção).
  Avaliar buffer de resiliência ([Roadmap](../roadmap.md)).
