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
   **Delta append-only**; dimensões geradas com Faker.
3. **Silver** — consumo **incremental** da Bronze por **streaming Delta + checkpoint**
   (`foreachBatch` MERGE), com **MERGE idempotente** por chave de negócio.
4. **Gold** — visões diárias (**D-1**) materializadas com `replaceWhere`.

Todos os recursos são provisionados por **Bicep modular** (um módulo por domínio) e
cada camada de processamento é um **Databricks Asset Bundle** independente. A
documentação detalhada está em [`docs/architecture.md`](../docs/architecture.md).

## 4. Decisões de arquitetura e trade-offs

| Decisão | Motivação | ADR |
|---|---|---|
| Medallion com Delta + Unity Catalog | ACID, time-travel e governança nativos | [0001](../docs/adrs/0001-medallion-delta-uc.md) |
| Silver incremental via streaming Delta + checkpoint | Incremental; at-least-once no `foreachBatch` com idempotência pelo MERGE por chave | [0002](../docs/adrs/0002-incremental-streaming.md) |
| Processamento agendado (AvailableNow) | Custo muito menor que streaming 24/7 | [0003](../docs/adrs/0003-scheduled-availablenow.md) |
| Event Hubs | High-throughput + integração Spark | [0004](../docs/adrs/0004-eventhubs-vs-servicebus.md) |
| PII mascarada no catálogo | Proteção uniforme p/ qualquer consumidor | [0005](../docs/adrs/0005-pii-masking-unity-catalog.md) |
| Data contracts + DLQ + observabilidade | Não perder dado inválido nem anomalia de volume | [0006](../docs/adrs/0006-data-contracts-dlq-observability.md) |

Trade-offs e limitações conhecidas estão registrados com transparência em
[`docs/trade-offs.md`](../docs/trade-offs.md).

## 5. Governança e segurança

- **Identidade sem segredos**: produtor pela **Managed Identity** da Function (*Data
  Sender*); consumidor por uma SPN com **apenas** *Data Receiver* — **least privilege**,
  sem SAS keys (namespace com `disableLocalAuth`).
- **PII**: a `dim_clientes` (CPF, e-mail, nome, nascimento) é mascarada por **column
  mask do Unity Catalog**, liberando o valor em claro apenas a um grupo do Entra ID.
- **Acesso por camada**: consumidores de BI só enxergam a Gold.

## 6. Qualidade de engenharia

- **Testes** unitários (pytest) cobrindo geradores, helpers de transformação,
  mascaramento de PII e a CLI (sem cluster Spark), mais **integração** (streaming/checkpoint/MERGE).
- **CI** (GitHub Actions): lint (ruff), testes unit+integração, **security scan**
  (bandit/pip-audit) e validação de bundles e de Bicep.
- **Deploy** (manual, `environment: prd`): bundles do Databricks e **código da Function**
  (build remoto no Flex Consumption). A infraestrutura é IaC (Bicep); o deploy do código da Function é
  etapa própria, também no pipeline.
- **Código compartilhado** (`Databricks/lib`): o padrão streaming/MERGE é centralizado
  em `transforms.SilverStream` e exercitado por testes no CI.
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
- **Regra de rechamada (`IN_RECH`)** e as **faixas do NPS clássico** (0–10:
  promotor 9–10, passivo 7–8, detrator 0–6) são decisões de negócio explícitas,
  registradas em [trade-offs](../docs/trade-offs.md) e
  [roadmap](../docs/roadmap.md).
- **Indicadores de transferência (`IN_TRAF`)** são recomputados sobre a **chamada
  inteira**: a cada batch, os atendimentos novos são unidos ao histórico da Silver e a
  janela é recalculada — corretos mesmo com atendimentos chegando em batches diferentes
  (sem depender de co-ocorrência no micro-batch). A leitura do histórico é limitada às
  chamadas tocadas e a um **lookback de 1 dia**, que é o limite explícito da
  reconciliação (ver [trade-offs](../docs/trade-offs.md)).

## 9. Roadmap

Curto prazo (dívidas técnicas), médio prazo (orquestração por dependência) e longo
prazo (Purview, SQL Serverless, tempo real). Detalhes em
[`docs/roadmap.md`](../docs/roadmap.md).

## 10. Conclusão

A entrega é uma base **modular, governada e testada**, sobre serviços gerenciados e
elásticos, pronta para evoluir de forma incremental sem reescrever a fundação —
combinando idempotência, custo controlado e automação, com as decisões e limitações
documentadas de forma transparente.

---

> Índice completo da documentação: [README](../README.md#documentação).
