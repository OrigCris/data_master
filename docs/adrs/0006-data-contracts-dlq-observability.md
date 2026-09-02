# ADR-0006 — Data contracts, quarentena (DLQ) e observabilidade de dados

- **Status**: Aceito
- **Contexto**: a Bronze parseia o evento contra um contrato versionado e a Silver
  consome os campos já estruturados. Sem uma estratégia definida, um evento incompatível
  (campo obrigatório ausente ou com tipo errado, inclusive vindo de JSON malformado) some
  do processamento silenciosamente, e uma queda/pico anômalo de volume passa despercebido
  pelas regras de linha (`not_null`, `between`).

## Decisão
1. **Contrato + quarentena (DLQ)**: o contrato versionado (`transforms.contracts`) é
   aplicado na Bronze (parse estrutural, preservando o payload original) e reforçado na
   Silver, onde cada micro-batch valida os **campos obrigatórios**. Eventos inválidos são
   roteados para `__quarantine` (payload original + motivo), não descartados — a escrita é
   **idempotente por `event_id`** (`merge_quarantine`), então um retry do micro-batch
   at-least-once não duplica. Só os válidos seguem para a Silver.
2. **Observabilidade de dataset**: a cada execução, registra-se **volume** e
   **freshness** em `__dataset_metrics` e compara-se o volume com a **média móvel** das
   execuções anteriores (anomalia fora de `[0.7, 1.3] × média`).

Ambos vivem na lib compartilhada (`transforms.validate_contract`/`merge_quarantine`,
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
  camada confiável; a DLQ é idempotente por `event_id` (retries não duplicam).
- (+) Data Quality evolui para **Data Reliability**: sinais de volume e freshness, não
  só validação de linha.
- (−) Uma tabela de quarentena e uma de métricas a operar/observar; a comparação de
  volume só ganha sentido depois de acumular histórico.

Relacionado: [Processamento](../processing.md), [Observabilidade](../observability.md),
[ADR-0002](0002-incremental-streaming.md).
