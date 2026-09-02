"""Testes dos geradores de SQL de governança de PII (column masks do Unity Catalog)."""
from security.pii import apply_column_masks_sql, column_mask_functions_sql


def test_column_mask_functions_sql_cria_as_quatro_funcoes():
    funcs = column_mask_functions_sql("prd", "b_dm_callcenter")
    for fn in ("mask_cpf", "mask_email", "mask_name", "mask_data_nascimento"):
        assert f"prd.b_dm_callcenter.{fn}" in funcs
    # data de nascimento generalizada para o ano, mantendo o tipo DATE
    assert "trunc(v, 'YEAR')" in funcs
    # libera em claro apenas para o grupo privilegiado
    assert "is_account_group_member('dm_pii_readers')" in funcs


def test_apply_column_masks_sql_usa_o_par_coluna_funcao():
    sql = apply_column_masks_sql(
        "prd", "b_dm_callcenter", "dim_clientes",
        {"cpf": "mask_cpf", "email": "mask_email", "nome": "mask_name",
         "data_nascimento": "mask_data_nascimento"},
    )
    assert "ALTER TABLE prd.b_dm_callcenter.dim_clientes ALTER COLUMN cpf SET MASK prd.b_dm_callcenter.mask_cpf;" in sql
    assert "ALTER COLUMN data_nascimento SET MASK prd.b_dm_callcenter.mask_data_nascimento;" in sql
    assert len(sql.strip().splitlines()) == 4


def test_apply_column_masks_sql_vazio_quando_sem_mascaras():
    assert apply_column_masks_sql("prd", "b", "t", {}) == ""
