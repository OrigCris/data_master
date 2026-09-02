# Runbook — Ingestão parada (sem eventos na Bronze)

**Disparo**: alerta `oper-evh-sem-ingestao` (`IncomingMessages = 0` na janela esperada)
ou Bronze sem novas linhas.

## Triagem (do produtor ao consumidor)
1. **Function App** está rodando?
   - App Insights → telemetria de **exceções** das execuções (métrica `exceptions/count`;
     a Function é TimerTrigger, então falha = exceção, não HTTP 5xx).
   ```bash
   az functionapp show -g rsgcjtecprd001 -n funccjtecprd001 --query state
   ```
2. **Managed Identity** da Function habilitada?
   ```bash
   az functionapp identity show -g rsgcjtecprd001 -n funccjtecprd001 --query principalId
   ```
3. **Permissão de envio** ao Event Hubs?
   - A **MI da Function** precisa de `Azure Event Hubs Data Sender` no namespace
     (o envio é por OAuth; falha de token → sem produção). Confira o role assignment
     no namespace `evhnscjtecprd001`.
4. **Event Hubs** saudável?
   ```bash
   az eventhubs eventhub show -g rsgcjtecprd001 --namespace-name evhnscjtecprd001 -n evh_cj_tec_ura
   ```
5. **Permissão de leitura** do consumidor no Event Hubs?
   - O SPN consumidor (`spn_dtb_consumer`) precisa de `Azure Event Hubs Data Receiver`
     no namespace; a leitura é por OAuth/Entra ID (falha de token → sem consumo).
6. **Consumo Bronze** (`AvailableNow`) executou? Verifique o run do job
   `bronze-streaming` e o `lastProgress`.

## Resolução
- Corrigir o elo quebrado (segredo, RBAC ou estado da Function) e reexecutar:
  ```bash
  dm run bronze-streaming -l layer_bronze
  ```
- Conferir se a interrupção não excedeu a **retenção** configurada do Event Hubs
  (dimensionada por ambiente); reprocessar a partir do que ainda estiver retido.
