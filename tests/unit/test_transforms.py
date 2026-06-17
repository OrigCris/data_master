"""Testes das funções puras da lib de transforms (sem Spark)."""
import pytest
from transforms.cdf_merge import assert_fqn, build_merge_on


def test_build_merge_on_uma_chave():
    assert build_merge_on(["ID_CHAM"]) == "S.ID_CHAM = C.ID_CHAM"


def test_build_merge_on_multiplas_chaves():
    sql = build_merge_on(["ID_CHAM", "ID_ATEN"])
    assert sql == "S.ID_CHAM = C.ID_CHAM AND S.ID_ATEN = C.ID_ATEN"


def test_build_merge_on_aliases_customizados():
    assert build_merge_on(["K"], target_alias="T", source_alias="U") == "T.K = U.K"


def test_build_merge_on_sem_chaves_falha():
    with pytest.raises(ValueError):
        build_merge_on([])


@pytest.mark.parametrize("fqn", ["prd.s_dm_callcenter.tabe_ura_anlt"])
def test_assert_fqn_valido(fqn):
    assert assert_fqn(fqn) == ("prd", "s_dm_callcenter", "tabe_ura_anlt")


@pytest.mark.parametrize("fqn", ["schema.table", "soltable", "a..c", "a.b.c.d"])
def test_assert_fqn_invalido(fqn):
    with pytest.raises(ValueError):
        assert_fqn(fqn)
