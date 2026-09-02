"""Governança de PII via **column masks** do Unity Catalog.

A política de mascaramento é imposta no catálogo (não no pipeline): funções de mask
reutilizáveis liberam o valor em claro apenas para um grupo privilegiado do Entra ID
(`is_account_group_member`), e cada tabela aplica as máscaras às suas colunas sensíveis.

Este módulo só gera SQL (sem Spark): a criação das funções fica no setup do Unity
Catalog; a aplicação por coluna fica no notebook que cria cada dimensão, que declara
explicitamente o par coluna → função.
"""
from __future__ import annotations

from collections.abc import Mapping


def column_mask_functions_sql(catalog: str, schema: str, privileged_group: str = "dm_pii_readers") -> str:
    """SQL que cria as funções de column mask reutilizáveis no Unity Catalog.

    As funções liberam o valor em claro apenas para membros de `privileged_group`
    (grupo do Entra ID sincronizado no workspace) via `is_account_group_member`.
    """
    fqn = f"{catalog}.{schema}"
    return f"""
CREATE OR REPLACE FUNCTION {fqn}.mask_cpf(v STRING)
RETURN CASE WHEN is_account_group_member('{privileged_group}') THEN v
            ELSE regexp_replace(v, '(\\\\d{{3}})\\\\.?\\\\d{{3}}\\\\.?\\\\d{{3}}-?(\\\\d{{2}})', '$1.***.***-$2') END;

CREATE OR REPLACE FUNCTION {fqn}.mask_email(v STRING)
RETURN CASE WHEN is_account_group_member('{privileged_group}') THEN v
            ELSE concat(substr(v, 1, 1), '***@', split(v, '@')[1]) END;

CREATE OR REPLACE FUNCTION {fqn}.mask_name(v STRING)
RETURN CASE WHEN is_account_group_member('{privileged_group}') THEN v
            ELSE concat(split(v, ' ')[0], ' ***') END;

-- Data de nascimento generalizada para o ano (trunc → 1º de janeiro), preservando o
-- tipo DATE exigido pelo column mask e reduzindo o risco de reidentificação.
CREATE OR REPLACE FUNCTION {fqn}.mask_data_nascimento(v DATE)
RETURN CASE WHEN is_account_group_member('{privileged_group}') THEN v
            ELSE trunc(v, 'YEAR') END;
""".strip()


def apply_column_masks_sql(catalog: str, schema: str, table: str, masks: Mapping[str, str]) -> str:
    """SQL que aplica as máscaras às colunas de `table`.

    `masks` mapeia **coluna → função** de mask (ex.: `{"cpf": "mask_cpf"}`) — a tabela
    é dona da própria política, informando explicitamente o que mascarar.
    """
    fqn = f"{catalog}.{schema}.{table}"
    return "\n".join(
        f"ALTER TABLE {fqn} ALTER COLUMN {col} SET MASK {catalog}.{schema}.{fn};"
        for col, fn in masks.items()
    )
