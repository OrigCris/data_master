-- =============================================================================
-- Governança de dados — Unity Catalog column masking (PII)
-- Mascaramento aplicado NO CATÁLOGO: o dado em claro é liberado apenas para o
-- grupo 'dm_pii_readers' (Entra ID), usando recursos nativos do Unity Catalog.
-- Responsabilidades no pipeline: (1) as FUNÇÕES são criadas uma vez pelo notebook
-- essential/setup_pii_functions; (2) cada dimensão APLICA suas máscaras às próprias
-- colunas, após persistir a tabela. Os geradores de SQL estão em security/pii.py;
-- este arquivo é a referência declarativa equivalente.
-- =============================================================================

-- 1) Funções reutilizáveis (criadas por essential/setup_pii_functions)
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

-- 2) Aplicação por tabela (cada notebook de dimensão aplica após persistir)
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
