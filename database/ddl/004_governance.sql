-- =============================================================================
-- Governança de dados — Unity Catalog column masking (PII)
-- Mascaramento aplicado NO CATÁLOGO: o dado em claro é liberado apenas para o
-- grupo 'dm_pii_readers' (Entra ID), usando recursos nativos do Unity Catalog.
-- Geração programática equivalente em Databricks/lib/security/pii.py.
-- =============================================================================

-- 1) Funções de mascaramento reutilizáveis (Bronze)
CREATE OR REPLACE FUNCTION prd.b_dm_callcenter.mask_cpf(v STRING)
RETURN CASE WHEN is_account_group_member('dm_pii_readers') THEN v
            ELSE regexp_replace(v, '(\\d{3})\\.?\\d{3}\\.?\\d{3}-?(\\d{2})', '$1.***.***-$2') END;

CREATE OR REPLACE FUNCTION prd.b_dm_callcenter.mask_email(v STRING)
RETURN CASE WHEN is_account_group_member('dm_pii_readers') THEN v
            ELSE concat(substr(v, 1, 1), '***@', split(v, '@')[1]) END;

CREATE OR REPLACE FUNCTION prd.b_dm_callcenter.mask_name(v STRING)
RETURN CASE WHEN is_account_group_member('dm_pii_readers') THEN v
            ELSE concat(split(v, ' ')[0], ' ***') END;

-- Data de nascimento generalizada para o ano (mantém o tipo DATE via trunc).
CREATE OR REPLACE FUNCTION prd.b_dm_callcenter.mask_data_nascimento(v DATE)
RETURN CASE WHEN is_account_group_member('dm_pii_readers') THEN v
            ELSE trunc(v, 'YEAR') END;

-- 2) Aplicação das máscaras às colunas sensíveis
ALTER TABLE prd.b_dm_callcenter.dim_clientes ALTER COLUMN cpf             SET MASK prd.b_dm_callcenter.mask_cpf;
ALTER TABLE prd.b_dm_callcenter.dim_clientes ALTER COLUMN email           SET MASK prd.b_dm_callcenter.mask_email;
ALTER TABLE prd.b_dm_callcenter.dim_clientes ALTER COLUMN nome            SET MASK prd.b_dm_callcenter.mask_name;
ALTER TABLE prd.b_dm_callcenter.dim_clientes ALTER COLUMN data_nascimento SET MASK prd.b_dm_callcenter.mask_data_nascimento;
ALTER TABLE prd.b_dm_callcenter.dim_assistentes ALTER COLUMN email          SET MASK prd.b_dm_callcenter.mask_email;
ALTER TABLE prd.b_dm_callcenter.dim_assistentes ALTER COLUMN nomeAssistente SET MASK prd.b_dm_callcenter.mask_name;

-- 3) Exemplo de GRANT por camada (least privilege)
--    Consumidores de BI só enxergam a Gold; PII fica restrita à Bronze.
-- GRANT USE SCHEMA, SELECT ON SCHEMA prd.g_dm_callcenter TO `dm_bi_consumers`;
-- GRANT SELECT ON TABLE prd.b_dm_callcenter.dim_clientes TO `dm_pii_readers`;
