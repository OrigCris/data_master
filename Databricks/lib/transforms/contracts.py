"""
    Contratos de dados versionados por tabela Bronze.
"""
from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import types as T


@dataclass(frozen=True)
class Contract:
    """Schema versionado de uma tabela Bronze.

    O schema é a fonte única da verdade: **toda** coluna declarada é obrigatória. Um
    evento cujo parse deixe qualquer uma delas nula viola o contrato e vai para a
    quarentena (ver `validate_contract`).
    """

    schema: T.StructType
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
    ),
    "surveys_once": Contract(
        schema=T.StructType([
            T.StructField("id_chamada", T.StringType()),
            T.StructField("id_pesquisa", T.StringType()),
            T.StructField("data_envio", T.DateType()),
            T.StructField("nota", T.IntegerType()),
        ]),
    ),
}


def contract_for(table_name: str) -> Contract:
    """Contrato (schema + versão) da tabela Bronze `table_name`."""
    try:
        return _CONTRACTS[table_name]
    except KeyError:
        raise ValueError(
            f"Sem contrato para a tabela Bronze {table_name!r}. Conhecidas: {sorted(_CONTRACTS)}"
        ) from None
