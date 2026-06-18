# 04. Visão Geral da Arquitetura

A arquitetura é **orientada a eventos**, **serverless** onde possível, e
**modular** — cada componente é provisionado por um módulo Bicep isolado (ver
[Componentização](stacks.md)) e cada camada de processamento é um Databricks Asset
Bundle independente.

<p align="center">
  <img src="../Imagens/arquitetura_tecnica.png" alt="Arquitetura técnica" width="900px"/>
</p>

## Fluxo end-to-end

```mermaid
flowchart LR
    subgraph Ingestao
      FN[Azure Functions<br/>Timer + SPN] -->|eventos JSON| EH[(Event Hubs<br/>ura / calls / surveys)]
    end
    subgraph Bronze
      EH -->|readStream AvailableNow| B[(Delta Bronze<br/>+ CDF)]
      DIM[Faker dims] --> B
    end
    subgraph Silver
      B -->|Change Data Feed stream| S[(Delta Silver<br/>foreachBatch MERGE)]
      CKPT[(checkpoint)] <-->|progresso| S
    end
    subgraph Gold
      S -->|agregação D-1| G[(Delta Gold<br/>visões)]
    end
    G --> BI[Dashboards / BI]
    B & S & G -.->|métricas| MON[Azure Monitor]
    KV[Key Vault] -.->|secrets| FN
    UC[Unity Catalog<br/>governança/PII] --- B & S & G
```

## 1. Ingestão (produção de eventos)

Uma **Azure Function** com **TimerTrigger** gera eventos sintéticos coerentes —
URA, derivações e pesquisas mantêm o mesmo `id_chamada` — e os envia para três
**Event Hubs** distintos. A autenticação usa uma **Service Principal (SPN)** cujos
segredos ficam no **Key Vault**, lidos via **Managed Identity** (a Function nunca
guarda segredo em configuração). Detalhes em [Ingestão](ingestion.md).

## 2. Bronze (landing)

Um job Databricks (**`Trigger.AvailableNow`**) consome cada Event Hub e grava na Bronze em
**Delta com CDF habilitado**. As dimensões são geradas em paralelo. A Bronze é
**imutável**: nenhuma transformação de negócio acontece aqui.

## 3. Silver (Bronze → Silver)

Job diário que consome o **CDF** da Bronze por **streaming `AvailableNow` +
checkpoint**, faz o parse do JSON cru, normaliza nomes e tipos, deriva colunas de
data e aplica **MERGE idempotente** via `foreachBatch`. Ver [Processamento](processing.md).

## 4. Gold (Silver → Gold)

Job diário que cruza as tabelas Silver com as dimensões e materializa as **visões
analíticas D-1** (`visao_ura_calls`, `visao_assistentes`), com `replaceWhere` por
data de referência. Ver [Geração de Dados Analíticos](analytics.md).

## Orquestração

O pipeline diário é orquestrado **por dependência** (não por horário): o bundle
`orchestration` define o job `dm-pipeline`, que encadeia as camadas com `depends_on`
disparando os jobs de cada camada via `run_job_task`.

```mermaid
flowchart LR
    dims[ingest_dims<br/>bronze-dim] --> gold[build_gold<br/>gold-job]
    silver[process_silver<br/>silver-job] --> gold
```

| Job | Trigger |
|---|---|
| `dm-pipeline` (orquestrador) | agendado diariamente (único schedule do batch) |
| `bronze-dim`, `silver-job`, `gold-job` | sem schedule próprio — disparados pela cadeia |
| `bronze-streaming` | schedule próprio (a cada 30 min) — ingestão contínua |

> `gold` só inicia quando **dims** e **silver** concluem. A ingestão de streaming
> roda de forma independente, alimentando a Bronze ao longo do dia.

## Pilares transversais

- **Governança/Segurança** — Unity Catalog + column masking de PII + RBAC ([Governança](governance.md)).
- **Observabilidade** — Azure Monitor + alertas + dashboard ([Observabilidade](observability.md)).
- **FinOps** — Azure Cost Management ([FinOps](finops.md)).

---

[← Anterior: Camadas](layers.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Componentização →](stacks.md)
