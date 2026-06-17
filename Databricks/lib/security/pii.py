"""Mascaramento e governança de PII para o data lake do call center.

A dimensão de clientes (`dim_clientes`) carrega dados pessoais (CPF, e-mail, nome,
data de nascimento). Este módulo provê:

* funções puras de mascaramento (testáveis sem Spark);
* `mask_dataframe` para aplicar mascaramento em batch num DataFrame Spark;
* geradores de SQL para **column masks** e **dynamic views** do Unity Catalog,
  que impõem o mascaramento *no catálogo* (não só no pipeline), liberando o dado
  em claro apenas para grupos privilegiados.

A estratégia adotada é **Unity Catalog column-level masking** + grupos do Entra ID.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

try:  # pragma: no cover - runtime Spark
    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F
except Exception:  # pragma: no cover
    DataFrame = object  # type: ignore
    F = None  # type: ignore


# Catálogo de colunas sensíveis por tabela (classificação de dados).
PII_COLUMNS: dict[str, dict[str, str]] = {
    "dim_clientes": {
        "cpf": "cpf",
        "email": "email",
        "nome": "name",
        "data_nascimento": "date",
    },
    "dim_assistentes": {
        "email": "email",
        "nomeAssistente": "name",
    },
}


# ----------------------------- funções puras ------------------------------ #
def mask_cpf(value: str | None) -> str | None:
    """Mascara um CPF preservando os 3 primeiros e os 2 últimos dígitos.

    >>> mask_cpf("123.456.789-09")
    '123.***.***-09'
    """
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11:
        return "***"
    return f"{digits[:3]}.***.***-{digits[-2:]}"


def mask_email(value: str | None) -> str | None:
    """Mascara o usuário do e-mail, preservando domínio.

    >>> mask_email("cristiano.alves@empresa.com")
    'c***@empresa.com'
    """
    if value is None or "@" not in value:
        return None if value is None else "***"
    user, _, domain = value.partition("@")
    head = user[0] if user else "*"
    return f"{head}***@{domain}"


def mask_name(value: str | None) -> str | None:
    """Mantém o primeiro nome e mascara os sobrenomes.

    >>> mask_name("Cristiano Alves de Souza")
    'Cristiano A. S.'
    """
    if value is None:
        return None
    parts = [p for p in value.split() if p]
    if not parts:
        return "***"
    return " ".join([parts[0]] + [f"{p[0]}." for p in parts[1:]])


def redact(value: str | None, keep: int = 0) -> str | None:
    """Redação genérica: mantém `keep` caracteres iniciais."""
    if value is None:
        return None
    return value[:keep] + "***"


# --------------------------- aplicação em Spark --------------------------- #
def mask_dataframe(df: DataFrame, columns: Mapping[str, str]) -> DataFrame:
    """Aplica mascaramento em batch. `columns` mapeia coluna→tipo
    ('cpf'|'email'|'name'|'date'|'redact')."""
    masker = {
        "cpf": F.udf(mask_cpf),
        "email": F.udf(mask_email),
        "name": F.udf(mask_name),
        "redact": F.udf(lambda v: redact(v)),
    }
    out = df
    for col, kind in columns.items():
        if col not in out.columns:
            continue
        if kind == "date":
            # Generaliza a data de nascimento para o ano (reduz risco de reidentificação).
            out = out.withColumn(col, F.year(F.col(col)).cast("string"))
        else:
            out = out.withColumn(col, masker.get(kind, masker["redact"])(F.col(col)))
    return out


# ----------------------- geração de SQL (Unity Catalog) ------------------- #
def column_mask_functions_sql(catalog: str, schema: str, privileged_group: str = "dm_pii_readers") -> str:
    """SQL que cria funções de mascaramento reutilizáveis no Unity Catalog.

    As funções liberam o valor em claro apenas para membros de `privileged_group`
    (grupo do Entra ID sincronizado no workspace) via `is_account_group_member`.
    """
    fqn = f"{catalog}.{schema}"
    return f"""
-- Funções de column mask (Unity Catalog) — {fqn}
CREATE OR REPLACE FUNCTION {fqn}.mask_cpf(v STRING)
RETURN CASE WHEN is_account_group_member('{privileged_group}') THEN v
            ELSE regexp_replace(v, '(\\\\d{{3}})\\\\.?\\\\d{{3}}\\\\.?\\\\d{{3}}-?(\\\\d{{2}})', '$1.***.***-$2') END;

CREATE OR REPLACE FUNCTION {fqn}.mask_email(v STRING)
RETURN CASE WHEN is_account_group_member('{privileged_group}') THEN v
            ELSE concat(substr(v, 1, 1), '***@', split(v, '@')[1]) END;

CREATE OR REPLACE FUNCTION {fqn}.mask_name(v STRING)
RETURN CASE WHEN is_account_group_member('{privileged_group}') THEN v
            ELSE concat(split(v, ' ')[0], ' ***') END;
""".strip()


def apply_column_masks_sql(catalog: str, schema: str, table: str, columns: Iterable[str]) -> str:
    """SQL que aplica as funções de mask às colunas sensíveis de uma tabela."""
    fqn = f"{catalog}.{schema}.{table}"
    func_map = {"cpf": "mask_cpf", "email": "mask_email", "nome": "mask_name", "nomeAssistente": "mask_name"}
    stmts = []
    for col in columns:
        fn = func_map.get(col)
        if fn:
            stmts.append(f"ALTER TABLE {fqn} ALTER COLUMN {col} SET MASK {catalog}.{schema}.{fn};")
    return "\n".join(stmts)
