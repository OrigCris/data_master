# 17. Roadmap Técnico e Melhorias Futuras

Evoluções priorizadas.

## Curto prazo (dívidas técnicas)
- [ ] **Rechamada cross-dia**: a janela de `IN_RECH` considera apenas as chamadas do
  próprio dia (`odate`); para capturar retornos que cruzam a meia-noite (ex.: 23h →
  01h), incluir as chamadas de D-1 na base da janela.
- [ ] Garantir, na ingestão, que os atendimentos de uma mesma chamada cheguem no
  mesmo micro-batch (a janela de `IN_TRAF` na Silver assume isso).

## Médio prazo (resiliência e orquestração)
- [ ] **Fila de resiliência** (Service Bus) entre Function App e Event Hubs como
  buffer contra intermitências (evita perda na retenção de 1h).
- [ ] **Orquestração por dependência** (job tasks com `depends_on` ou
  *file arrival trigger*) em vez de cascata por horário.
- [ ] **DLQ** e reprocessamento automático de eventos malformados.
- [ ] **Budgets do Cost Management** com alerta de custo.

## Longo prazo (plataforma)
- [ ] **Microsoft Purview** para catálogo corporativo e classificação automática de PII.
- [ ] **Databricks SQL Serverless** + dashboards versionados para o consumo analítico.
- [ ] **Tempo real** de fato (streaming contínuo) para casos que exijam latência baixa.
- [ ] **DABs com wheel** empacotando `Databricks/lib` (em vez de `sys.path`).
- [ ] **Testes de integração** com Spark local (`pyspark` no CI) cobrindo MERGE/CDF.

---

[← Anterior: Benchmark](benchmark.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Referência →](reference.md)
