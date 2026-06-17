# Relatório Técnico — Data Master

**Plataforma de Dados de Call Center na Microsoft Azure**

---

## 1. Resumo executivo

Este projeto entrega uma plataforma de engenharia de dados **end-to-end** sobre a
Microsoft Azure, partindo de um domínio realista de **call center / URA** e cobrindo
ingestão em tempo real, processamento incremental em arquitetura Medallion,
modelagem analítica, governança de dados sensíveis, observabilidade, gestão de
custos e automação completa de provisionamento e deploy.

A solução foi desenhada com três objetivos não-funcionais guiando cada decisão:
**custo controlado**, **confiabilidade/idempotência** e **manutenibilidade**.

## 2. Domínio e problema

A central recebe ligações que entram pela **URA** (autoatendimento). Parte é
**derivada** a atendentes humanos; parte das chamadas atendidas responde a uma
**pesquisa de satisfação** (base do NPS). As entidades de apoio são as dimensões de
**clientes** (com PII) e **assistentes** (com hierarquia organizacional).

A plataforma responde a perguntas como: taxa de autoatendimento × derivação por
fila, tempo médio de atendimento, transferências indevidas, NPS e rechamada por
assistente, e o custo da operação por serviço.

## 3. Arquitetura

Arquitetura **orientada a eventos** e **modular**:

1. **Ingestão** — Azure Functions (TimerTrigger) gera eventos coerentes
   (mesmo `id_chamada` entre URA, atendimento e pesquisa) e os envia a três **Event
   Hubs**, autenticando via **Service Principal** cujos segredos vêm do **Key Vault**
   (lido por **Managed Identity** — sem segredos no código).
2. **Bronze** — job Databricks com **`Trigger.AvailableNow`** grava o dado cru em
   **Delta com Change Data Feed**; dimensões geradas com Faker.
3. **Silver** — consumo **incremental** do CDF por **streaming + checkpoint**
   (`foreachBatch` MERGE), com **MERGE idempotente** por chave de negócio.
4. **Gold** — visões diárias (**D-1**) materializadas com `replaceWhere`.

Todos os recursos são provisionados por **Bicep modular** (um módulo por domínio) e
cada camada de processamento é um **Databricks Asset Bundle** independente. A
documentação detalhada está em [`docs/architecture.md`](../docs/architecture.md).

## 4. Decisões de arquitetura e trade-offs

| Decisão | Motivação | ADR |
|---|---|---|
| Medallion com Delta + Unity Catalog | ACID, time-travel, CDF e governança nativos | [0001](../docs/adrs/0001-medallion-delta-uc.md) |
| Silver incremental via streaming CDF + checkpoint | Incremental, idempotente, exactly-once | [0002](../docs/adrs/0002-incremental-streaming-cdf.md) |
| Processamento agendado (AvailableNow) | Custo muito menor que streaming 24/7 | [0003](../docs/adrs/0003-scheduled-availablenow.md) |
| Event Hubs | High-throughput + integração Spark | [0004](../docs/adrs/0004-eventhubs-vs-servicebus.md) |
| PII mascarada no catálogo | Proteção uniforme p/ qualquer consumidor | [0005](../docs/adrs/0005-pii-masking-unity-catalog.md) |

Trade-offs e limitações conhecidas estão registrados com transparência em
[`docs/trade-offs.md`](../docs/trade-offs.md).

## 5. Governança e segurança

- **Identidade sem segredos**: Managed Identity + Key Vault; SPNs separadas para
  produzir e consumir, com **least privilege**.
- **PII**: a `dim_clientes` (CPF, e-mail, nome, nascimento) é mascarada por **column
  mask do Unity Catalog**, liberando o valor em claro apenas a um grupo do Entra ID.
- **Acesso por camada**: consumidores de BI só enxergam a Gold.

## 6. Qualidade de engenharia

- **Testes** unitários (pytest) cobrindo geradores, helpers de transformação,
  mascaramento de PII e a CLI — executáveis no CI **sem cluster Spark**.
- **CI/CD** (GitHub Actions): lint (ruff), testes, validação de bundles e de Bicep.
- **Código compartilhado** (`Databricks/lib`): o padrão CDF/MERGE é centralizado em
  `transforms.SilverStream` e exercitado por testes no CI.
- **Data Quality** como gate: expectativas críticas falham o job; resultados
  auditados em `__dq_results`.

## 7. Observabilidade e FinOps

- **Azure Monitor** + Application Insights + dashboard, com **alertas como código**
  (ingestão parada, falhas da Function).
- **FinOps** via Azure Cost Management, com tags de *cost allocation* e decisões que
  reduzem custo (processamento agendado `AvailableNow`, incremental, `replaceWhere`,
  autotermination).

## 8. Contratos e limitações conhecidas

- **Contrato de dados da pesquisa**: `data_envio` é uma **data** (não timestamp),
  compatível com o `DateType` da Silver — garantindo que a pesquisa entre no cálculo
  de NPS. Coberto por teste de regressão.
- **Regra de rechamada (`IN_RECH`)** e **faixa de NPS** adotada são decisões de
  negócio explícitas, registradas em [trade-offs](../docs/trade-offs.md) e
  [roadmap](../docs/roadmap.md).
- **Indicadores de transferência (`IN_TRAF`)** assumem que os atendimentos de uma
  mesma chamada chegam no mesmo micro-batch — verdadeiro no fluxo de ingestão atual.

## 9. Roadmap

Curto prazo (dívidas técnicas), médio prazo (resiliência/orquestração por
dependência) e longo prazo (Purview, SQL Serverless, tempo real). Detalhes em
[`docs/roadmap.md`](../docs/roadmap.md).

## 10. Conclusão

A entrega é uma base **serverless, modular, governada e testada**, pronta para
evoluir de forma incremental sem reescrever a fundação. A combinação de
idempotência, custo controlado e automação cobre os pilares avaliados em um programa
de certificação de nível avançado/expert, com as decisões e limitações documentadas
de forma transparente.

---

> Índice completo da documentação: [README](../README.md#documentação).
