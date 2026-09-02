"""Contratos de dados versionados por tabela Bronze.

O parsing estrutural do evento ocorre na Bronze contra estes contratos (schema +
campos obrigatórios + versão); a Silver consome os campos já estruturados, sem refazer
`from_json`. O contrato é resolvido pelo `table_name` da Bronze — o notebook Bronze é
genérico e atende URA/CALLS/PESQUISA pela tabela de destino. Vive no código (versionado),
sem Schema Registry.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pyspark.sql import types as T


@dataclass(frozen=True)
class Contract:
    schema: T.StructType
    required: Sequence[str]
    version: str = "1.0"


_CONTRACTS: dict[str, Contract] = {
    "ura_once": Contract(
        schema=T.StructType([
            T.StructField("id_chamada", T.StringType()),
            T.StructField("id_cliente", T.StringType()),
            T.StructField("id_fila", T.StringType()),
            T.StructField("data_hora_inicio", T.TimestampType()),
            T.StructField("data_hora_fim", T.TimestampType()),
            T.StructField("autenticado", T.BooleanType()),
            T.StructField("opcoes_navegadas", T.IntegerType()),
            T.StructField("codigo_opcao", T.StringType()),
            T.StructField("derivado_atendimento", T.BooleanType()),
        ]),
        required=["id_chamada", "id_cliente", "data_hora_inicio"],
    ),
    "calls_once": Contract(
        schema=T.StructType([
            T.StructField("id_chamada", T.StringType()),
            T.StructField("id_atendimento", T.StringType()),
            T.StructField("id_cliente", T.StringType()),
            T.StructField("id_assistente", T.IntegerType()),
            T.StructField("data_hora_inicio", T.TimestampType()),
            T.StructField("data_hora_fim", T.TimestampType()),
            T.StructField("area_atendimento", T.StringType()),
        ]),
        required=["id_chamada", "id_atendimento", "id_assistente", "data_hora_inicio"],
    ),
    "surveys_once": Contract(
        schema=T.StructType([
            T.StructField("id_chamada", T.StringType()),
            T.StructField("id_pesquisa", T.StringType()),
            T.StructField("data_envio", T.DateType()),
            T.StructField("nota", T.IntegerType()),
        ]),
        required=["id_chamada", "id_pesquisa", "nota"],
    ),
}


def contract_for(table_name: str) -> Contract:
    """Contrato (schema + obrigatórios + versão) da tabela Bronze `table_name`."""
    try:
        return _CONTRACTS[table_name]
    except KeyError:
        raise ValueError(
            f"Sem contrato para a tabela Bronze {table_name!r}. Conhecidas: {sorted(_CONTRACTS)}"
        ) from None
