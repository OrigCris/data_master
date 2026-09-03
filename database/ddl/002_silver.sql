-- =============================================================================
-- Camada SILVER — schema s_dm_callcenter
-- Dados limpos/normalizados, consumidos da Bronze (append-only) por streaming Delta
-- e aplicados via MERGE idempotente. Nomenclatura padronizada (ver reference.md).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS prd.s_dm_callcenter;

-- Obs.: o progresso do consumo incremental Bronze→Silver é controlado pelo
-- CHECKPOINT do Structured Streaming (Trigger.AvailableNow + foreachBatch MERGE).
-- Ver docs/processing.md e ADR-0002.

-- URA analítica (1 linha por chamada).
CREATE TABLE IF NOT EXISTS prd.s_dm_callcenter.tabe_ura_anlt (
  ID_CHAM        STRING,   -- id da chamada (chave de negócio)
  ID_CLIE        STRING,   -- id do cliente
  ID_FILA        STRING,   -- fila/serviço da URA
  DH_INIC        TIMESTAMP,
  DH_FIM         TIMESTAMP,
  QT_OPCA_NAVG   INT,      -- qtd de opções navegadas
  CD_ULTI_OPCA   STRING,   -- código da última opção
  IN_AUTN        BOOLEAN,  -- autenticado
  IN_DERV_ATEN   BOOLEAN,  -- derivado a atendimento humano
  CD_PERI        INT,      -- período yyyyMM
  DT_INIC        DATE,
  DT_FIM         DATE,
  DH_REFE_CRGA   TIMESTAMP
) USING DELTA CLUSTER BY (CD_PERI, DT_INIC, ID_CHAM);

-- Atendimentos humanos (N linhas por chamada — uma por etapa de atendimento).
CREATE TABLE IF NOT EXISTS prd.s_dm_callcenter.tabe_calls (
  ID_CHAM        STRING,
  ID_ATEN        STRING,   -- id do atendimento (parte da chave junto de ID_CHAM)
  ID_CLIE        STRING,
  ID_ASST        INT,      -- id do assistente
  DH_INIC        TIMESTAMP,
  DH_FIM         TIMESTAMP,
  DS_AREA_ATEN   STRING,
  CD_PERI        INT,
  DT_INIC        DATE,
  DT_FIM         DATE,
  DH_REFE_CRGA   TIMESTAMP,
  IN_TRAF        INT,      -- houve transferência para próximo atendimento
  IN_TRAF_INDV   INT       -- transferência indevida (mesma área)
) USING DELTA CLUSTER BY (CD_PERI, DT_INIC, ID_CHAM);

-- Pesquisa de satisfação (1 linha por pesquisa).
CREATE TABLE IF NOT EXISTS prd.s_dm_callcenter.tabe_pesq_ura (
  ID_CHAM        STRING,
  ID_PESQ        STRING,
  DT_ENVI        DATE,
  VL_NOTA        INT,      -- nota 0..10 (escala NPS clássica)
  CD_PERI        INT,
  DH_REFE_CRGA   TIMESTAMP
) USING DELTA CLUSTER BY (ID_PESQ);

-- Tabela de auditoria de Data Quality (alimentada por QualityReport.to_table).
CREATE TABLE IF NOT EXISTS prd.s_dm_callcenter.__dq_results (
  dataset      STRING,
  expectation  STRING,
  column       STRING,
  severity     STRING,
  failed_rows  BIGINT,
  passed       BOOLEAN,
  checked_at   TIMESTAMP
) USING DELTA
COMMENT 'Resultados das checagens de Data Quality por execução.';

-- Dead-letter queue (DLQ): eventos com coluna do contrato ausente/inválida não são
-- descartados, e sim isolados aqui com o payload original e o motivo, para triagem/
-- reprocessamento. Escrita idempotente por event_id (MERGE WHEN NOT MATCHED).
CREATE TABLE IF NOT EXISTS prd.s_dm_callcenter.__quarantine (
  event_id       STRING,   -- sha256 da identidade do evento (source|partition|offset)
  payload        STRING,   -- payload original recebido na Bronze
  error_reason   STRING,   -- missing_or_invalid: <campos>
  schema_version STRING,   -- versão do contrato aplicado
  ingestion_ts   TIMESTAMP,
  source         STRING    -- tabela/fonte de origem do evento
) USING DELTA
COMMENT 'Eventos em quarentena por violação do contrato (colunas do schema).';

-- Histórico de métricas de dataset (volume, freshness) para observabilidade:
-- alimenta a comparação de volume contra a média móvel das execuções anteriores.
CREATE TABLE IF NOT EXISTS prd.s_dm_callcenter.__dataset_metrics (
  dataset       STRING,
  metric        STRING,   -- row_count | freshness_minutes
  metric_value  DOUBLE,
  observed_date DATE,     -- data de referência observada (date_col)
  observed_at   TIMESTAMP
) USING DELTA
COMMENT 'Métricas de dataset por execução (base da observabilidade de volume/freshness).';
