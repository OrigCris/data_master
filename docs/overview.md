# 01. Apresentação do Case

## Contexto

Este projeto implementa uma plataforma de dados **end-to-end** para um domínio de
**call center / URA** (Unidade de Resposta Audível), construída sobre a nuvem
**Microsoft Azure** com arquitetura **Medallion** (bronze → silver → gold) e
processamento em **Azure Databricks**.

O objetivo é demonstrar, com um domínio realista, uma solução de engenharia de
dados que cobre todo o ciclo: **ingestão em tempo real**, **processamento
incremental**, **modelagem analítica**, **governança/segurança de PII**,
**observabilidade**, **FinOps** e **automação de deploy**.

## Domínio de negócio

Um cliente liga para a central. A jornada passa por:

1. **URA (autoatendimento)** — o cliente navega por opções; pode resolver sozinho
   ou ser **derivado** para um atendente humano.
2. **Atendimento humano** — um ou mais **assistentes** atendem a chamada derivada;
   há transferências entre áreas.
3. **Pesquisa de satisfação** — parte das chamadas atendidas responde a uma
   pesquisa (nota 1–10), base para o cálculo de **NPS**.

As entidades de apoio são as dimensões **clientes** e **assistentes** (com
hierarquia organizacional). O modelo completo está em [Modelo de Dados](mer.md).

## Perguntas de negócio respondidas

- Qual a taxa de **autoatendimento × derivação** por fila da URA?
- Qual o **tempo médio de atendimento** e o volume de **transferências indevidas**?
- Quem são os assistentes com melhor **NPS** e menor **rechamada**?
- Como evolui o custo da plataforma por serviço (**FinOps**)?

## Componentes principais

| Capacidade | Serviço Azure |
|---|---|
| Geração/produção de eventos | Azure Functions (Timer) + SPN |
| Ingestão em tempo real | Azure Event Hubs |
| Processamento (medallion) | Azure Databricks + Delta + Unity Catalog |
| Armazenamento | ADLS Gen2 |
| Segredos / identidade | Key Vault + Managed Identity + Entra ID |
| Observabilidade | Azure Monitor / Log Analytics / App Insights |
| Custo | Azure Cost Management |
| Automação | Databricks Asset Bundles + Bicep + CLI `dm` |

---

[Voltar ao índice](../README.md#documentação) | [Próximo: Modelo de Dados →](mer.md)
