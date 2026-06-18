# 17. Roadmap Técnico e Melhorias Futuras

Evoluções priorizadas.

## Curto prazo (dívidas técnicas)
- [ ] Garantir, na ingestão, que os atendimentos de uma mesma chamada cheguem no
  mesmo micro-batch (a janela de `IN_TRAF` na Silver assume isso).

## Médio prazo
- [ ] **File arrival trigger** no orquestrador (disparar por chegada de dado, além
  do schedule diário).
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
