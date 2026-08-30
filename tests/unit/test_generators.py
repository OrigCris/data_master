"""Testes dos geradores de eventos sintéticos da Function App."""
import random
from datetime import date

import pytest
from faker import Faker
from generators.calls import AREAS, area_do_assistente, gerar_fato_chamada_humana
from generators.surveys import gerar_fato_pesquisa_satisfacao
from generators.ura import OpcoesURA, gerar_eventos_ura


@pytest.fixture(autouse=True)
def _seed():
    """Torna a geração determinística por teste."""
    random.seed(42)
    Faker.seed(42)


def test_ura_respeita_limites_de_quantidade():
    eventos = gerar_eventos_ura(min_chamadas=5, max_chamadas=5)
    assert len(eventos) == 5


def test_ura_campos_obrigatorios_e_dominio():
    eventos = gerar_eventos_ura()
    assert eventos, "deveria gerar ao menos uma chamada"
    for e in eventos:
        assert set(e) >= {
            "id_chamada", "id_cliente", "data_hora_inicio", "data_hora_fim",
            "autenticado", "opcoes_navegadas", "codigo_opcao",
            "derivado_atendimento", "id_fila",
        }
        assert e["codigo_opcao"] in OpcoesURA
        assert e["id_fila"] == f"URA_{e['codigo_opcao']}"
        assert 1 <= e["opcoes_navegadas"] <= 10
        assert e["data_hora_fim"] > e["data_hora_inicio"]


def test_calls_apenas_para_chamadas_derivadas():
    ura = gerar_eventos_ura()
    calls = gerar_fato_chamada_humana(ura)
    ids_derivados = {e["id_chamada"] for e in ura if e["derivado_atendimento"]}
    ids_em_calls = {c["id_chamada"] for c in calls}
    assert ids_em_calls <= ids_derivados


def test_calls_herdam_cliente_da_ura():
    ura = gerar_eventos_ura()
    cliente_por_chamada = {e["id_chamada"]: e["id_cliente"] for e in ura}
    for c in gerar_fato_chamada_humana(ura):
        assert c["id_cliente"] == cliente_por_chamada[c["id_chamada"]]


def test_surveys_data_envio_eh_date_iso():
    ura = gerar_eventos_ura()
    surveys = gerar_fato_pesquisa_satisfacao(ura)
    for s in surveys:
        # Regressão do bug de tipo: deve ser uma data ISO (YYYY-MM-DD), não timestamp.
        parsed = date.fromisoformat(s["data_envio"])
        assert isinstance(parsed, date)
        assert "T" not in s["data_envio"]
        assert 0 <= s["nota"] <= 10


def test_surveys_apenas_para_derivadas():
    ura = gerar_eventos_ura()
    surveys = gerar_fato_pesquisa_satisfacao(ura)
    ids_derivados = {e["id_chamada"] for e in ura if e["derivado_atendimento"]}
    assert {s["id_chamada"] for s in surveys} <= ids_derivados


def test_area_deterministica_por_assistente():
    # a mesma regra da dim_assistentes: id → área (determinística, ciclando as áreas)
    assert area_do_assistente(1) == AREAS[0]
    assert area_do_assistente(len(AREAS) + 1) == AREAS[0]
    assert all(area_do_assistente(i) in AREAS for i in range(1, 25))


def test_calls_area_coerente_com_assistente():
    # em qualquer evento de atendimento, a área bate com a do assistente (coerência
    # com a dimensão): um assistente nunca aparece com áreas diferentes.
    ura = gerar_eventos_ura()
    calls = gerar_fato_chamada_humana(ura)
    for c in calls:
        assert c["area_atendimento"] == area_do_assistente(c["id_assistente"])
