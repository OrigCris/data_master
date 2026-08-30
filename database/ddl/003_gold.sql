-- =============================================================================
-- Camada GOLD — schema g_dm_callcenter
-- Visões analíticas diárias (D-1), materializadas com replaceWhere por DT_REFE.
-- Prontas para consumo em BI/dashboards.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS prd.g_dm_callcenter;

-- Visão diária por fila da URA × derivações (autoatendimento vs. atendimento humano).
CREATE TABLE IF NOT EXISTS prd.g_dm_callcenter.visao_ura_calls (
  CD_PERI                INT,
  DT_REFE                DATE,
  ID_FILA                STRING,
  NR_MED_OPCA_NAVG       DOUBLE,   -- média de opções navegadas
  NR_MED_OPCA_AUTO_SERV  DOUBLE,   -- média de opções (autoatendimento)
  NR_MED_OPCA_DERV       DOUBLE,   -- média de opções (derivadas)
  QT_AUTN                BIGINT,   -- chamadas autenticadas
  QT_DERV_ATEN           BIGINT,   -- chamadas derivadas
  QT_CHAM_ATEN_HUMN      BIGINT,   -- atendimentos humanos
  QT_TRAF                BIGINT,   -- transferências
  QT_TRAF_INDV           BIGINT,   -- transferências indevidas
  NR_MEDI_TEMP_CHAM      DOUBLE    -- tempo médio de chamada (s)
) USING DELTA CLUSTER BY (CD_PERI, DT_REFE, ID_FILA);

-- Visão diária por assistente (produtividade + NPS).
CREATE TABLE IF NOT EXISTS prd.g_dm_callcenter.visao_assistentes (
  CD_PERI            INT,
  DT_REFE            DATE,
  DS_AREA            STRING,
  ID_ASST            INT,
  NM_ASST            STRING,
  NM_SVSP            STRING,
  NM_CORD            STRING,
  NM_GERN            STRING,
  NM_SUPT            STRING,
  QT_CHAM_ATEN       BIGINT,
  QT_TRAF            BIGINT,
  PC_TRAF            DOUBLE,
  QT_TRAF_INDV       BIGINT,
  PC_TRAF_INDV       DOUBLE,
  QT_RECH            BIGINT,    -- rechamadas (≤24h)
  PC_RECH            DOUBLE,
  VL_TEMP_MEDI_OPER  DOUBLE,    -- tempo médio de atendimento (s)
  QT_PRMT            BIGINT,    -- promotores (nota 9-10)
  QT_NTRO            BIGINT,    -- passivos/neutros (nota 7-8)
  QT_DETR            BIGINT,    -- detratores (nota 0-6)
  VL_NPS             DOUBLE     -- (PRMT - DETR) / total * 100
) USING DELTA CLUSTER BY (CD_PERI, DT_REFE, ID_ASST);
