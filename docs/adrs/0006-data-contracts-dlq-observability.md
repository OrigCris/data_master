# ADR-0006 — Data contracts, quarentena (DLQ) e observabilidade de dados

- **Status**: Aceito
- **Contexto**: a Silver parseia o JSON da Bronze contra um schema explícito. Sem uma
  estratégia definida, um evento incompatível (JSON malformado, campo obrigatório
  ausente ou com tipo errado) some do processamento silenciosamente, e uma queda/pico
  anômalo de volume passa despercebido pelas regras de linha (`not_null`, `between`).

## Decisão
1. **Data contract + quarentena (DLQ)**: cada micro-batch valida os eventos contra o
   schema e uma lista de **campos obrigatórios**. Eventos inválidos são roteados para
   `__quarantine` (payload cru + motivo), não descartados. Só os válidos seguem para a
   Silver.
2. **Observabilidade de dataset**: a cada execução, registra-se **volume** e
   **freshness** em `__dataset_metrics` e compara-se o volume com a **média móvel** das
   execuções anteriores (anomalia fora de `[0.7, 1.3] × média`).

Ambos vivem na lib compartilhada (`transforms.validate_contract`,
`quality.run_observability`), com a lógica de decisão em funções puras testadas no CI.

## Alternativas
- **Descartar eventos inválidos** (`filter(isNotNull)`) — simples, mas perde dado e
  esconde problemas de contrato do produtor.
- **Só regras de linha** — não capturam anomalias de comportamento do dataset (volume,
  freshness).
- **Ferramenta externa de observabilidade** — poder maior, porém custo e acoplamento
  desnecessários para o escopo atual.

## Consequências
- (+) Dado inválido é isolado e auditável (triagem/reprocessamento), sem contaminar a
  camada confiável.
- (+) Data Quality evolui para **Data Reliability**: sinais de volume e freshness, não
  só validação de linha.
- (−) Uma tabela de quarentena e uma de métricas a operar/observar; a comparação de
  volume só ganha sentido depois de acumular histórico.

Relacionado: [Processamento](../processing.md), [Observabilidade](../observability.md),
[ADR-0002](0002-incremental-streaming.md).
