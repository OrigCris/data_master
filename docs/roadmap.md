# 17. Roadmap Técnico e Melhorias Futuras

Evoluções priorizadas.

## Médio prazo
- [ ] **File arrival trigger** no orquestrador (disparar por chegada de dado, além
  do schedule diário).
- [ ] **Reprocessamento automático** da quarentena (a DLQ já isola os eventos
  malformados; falta o *replay* orquestrado após correção do contrato).
- [ ] **Budgets do Cost Management** com alerta de custo.

## Longo prazo (plataforma)
- [ ] **Microsoft Purview** para catálogo corporativo e classificação automática de PII.
- [ ] **Databricks SQL Serverless** + dashboards versionados para o consumo analítico.
- [ ] **Tempo real** de fato (streaming contínuo) para casos que exijam latência baixa.
- [ ] Ampliar os **testes de integração** com Spark (a base — streaming Delta +
  checkpoint + MERGE idempotente — já roda no CI; evoluir para cobrir DQ gate e quarentena).

---

[← Anterior: Benchmark](benchmark.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Referência →](reference.md)
