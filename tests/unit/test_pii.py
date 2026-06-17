"""Testes das funções puras de mascaramento de PII."""
import pytest
from security.pii import apply_column_masks_sql, mask_cpf, mask_email, mask_name, redact


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("123.456.789-09", "123.***.***-09"),
        ("12345678909", "123.***.***-09"),
        ("123", "***"),
        (None, None),
    ],
)
def test_mask_cpf(raw, expected):
    assert mask_cpf(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("cristiano.alves@empresa.com", "c***@empresa.com"),
        ("a@b.com", "a***@b.com"),
        ("sem-arroba", "***"),
        (None, None),
    ],
)
def test_mask_email(raw, expected):
    assert mask_email(raw) == expected


def test_mask_name():
    assert mask_name("Cristiano Alves de Souza") == "Cristiano A. d. S."
    assert mask_name("Madonna") == "Madonna"
    assert mask_name(None) is None
    assert mask_name("   ") == "***"


def test_redact():
    assert redact("segredo", keep=2) == "se***"
    assert redact(None) is None


def test_apply_column_masks_sql_gera_alter_para_colunas_conhecidas():
    sql = apply_column_masks_sql("prd", "b_dm_callcenter", "dim_clientes", ["cpf", "email", "nome", "segmento"])
    assert "ALTER TABLE prd.b_dm_callcenter.dim_clientes ALTER COLUMN cpf SET MASK" in sql
    assert "email" in sql and "nome" in sql
    # 'segmento' não é PII → não deve receber máscara
    assert "segmento" not in sql
