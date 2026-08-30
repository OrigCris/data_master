-- =============================================================================
-- Camada BRONZE — schema b_dm_callcenter
-- Dados crus: dimensões sintéticas + landing de streaming (Event Hubs).
-- As tabelas são MANAGED no Unity Catalog. Este DDL documenta o contrato de
-- schema; em runtime os notebooks criam/atualizam as tabelas (saveAsTable).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS prd.b_dm_callcenter;

-- Dimensão de clientes (contém PII — ver 004_governance.sql)
CREATE TABLE IF NOT EXISTS prd.b_dm_callcenter.dim_clientes (
  id_cliente        INT,
  nome              STRING,
  cpf               STRING,
  email             STRING,
  data_nascimento   DATE,
  sexo              STRING,
  estado            STRING,
  cidade            STRING,
  segmento          STRING,
  dt_cadastro       TIMESTAMP,
  dat_ref_carga     DATE,
  ingestion_ts      TIMESTAMP
) USING DELTA
COMMENT 'Dimensão de clientes do call center (dados sintéticos Faker pt_BR).';

-- Dimensão de assistentes (hierarquia organizacional)
CREATE TABLE IF NOT EXISTS prd.b_dm_callcenter.dim_assistentes (
  identificadorAssistente        INT,
  nomeAssistente                 STRING,
  email                          STRING,
  matricula                      STRING,
  area                           STRING,
  identificadorSupervisor        STRING,
  nomeSupervisor                 STRING,
  identificadorCoordenador       STRING,
  nomeCoordenador                STRING,
  identificadorGerente           STRING,
  nomeGerente                    STRING,
  identificadorSuperintendente   STRING,
  nomeSuperintendente            STRING,
  status                         STRING,
  dt_cadastro                    TIMESTAMP,
  dat_ref_carga                  DATE,
  ingestion_ts                   TIMESTAMP
) USING DELTA
COMMENT 'Dimensão de assistentes com hierarquia (supervisor→gerente→superintendente).';

-- Landing de streaming (Event Hubs → Bronze). Mesmo contrato para ura/calls/surveys.
-- Append-only: serve como fonte de streaming Delta direto para a Silver. Liquid
-- clustering por data.
CREATE TABLE IF NOT EXISTS prd.b_dm_callcenter.ura_once (
  body             STRING,
  partition        INT,
  offset           STRING,
  enqueuedTime     TIMESTAMP,
  partitionKey     STRING,
  ingestion_ts     TIMESTAMP,
  ingestion_date   DATE
) USING DELTA
CLUSTER BY (ingestion_date)
COMMENT 'Landing cru de eventos de URA vindos do Event Hubs (AvailableNow).';

CREATE TABLE IF NOT EXISTS prd.b_dm_callcenter.calls_once (
  body STRING, partition INT, offset STRING,
  enqueuedTime TIMESTAMP, partitionKey STRING, ingestion_ts TIMESTAMP, ingestion_date DATE
) USING DELTA CLUSTER BY (ingestion_date)
COMMENT 'Landing cru de atendimentos humanos (derivações da URA).';

CREATE TABLE IF NOT EXISTS prd.b_dm_callcenter.surveys_once (
  body STRING, partition INT, offset STRING,
  enqueuedTime TIMESTAMP, partitionKey STRING, ingestion_ts TIMESTAMP, ingestion_date DATE
) USING DELTA CLUSTER BY (ingestion_date)
COMMENT 'Landing cru de pesquisas de satisfação.';
