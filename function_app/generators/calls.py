from __future__ import annotations
import uuid
import random
from datetime import datetime, timedelta
from typing import Iterable
from faker import Faker

fake = Faker("pt_BR")
AREAS = ["Cartões", "Financiamento", "Cobrança", "Relacionamento"]

def gerar_fato_chamada_humana(eventos_ura: Iterable[dict]) -> list[dict]:
    eventos_humanos: list[dict] = []

    for evento in eventos_ura:
        if not evento.get("derivado_atendimento"):
            continue

        num_atendimentos = random.randint(1, 7)
        assistentes_ids = random.sample(range(1, 21), k=num_atendimentos)
        data_hora_inicio = evento["data_hora_fim"]

        if isinstance(data_hora_inicio, str):
            data_hora_inicio_dt = datetime.fromisoformat(data_hora_inicio)
        else:
            data_hora_inicio_dt = data_hora_inicio

        for i in range(num_atendimentos):
            inicio = data_hora_inicio_dt if i == 0 else datetime.fromisoformat(eventos_humanos[-1]["data_hora_fim"])
            fim = fake.date_time_between(start_date=inicio, end_date=inicio + timedelta(minutes=5))

            eventos_humanos.append(
                {
                "id_chamada": evento["id_chamada"],
                "id_atendimento": str(uuid.uuid4()),
                "id_cliente": evento["id_cliente"],
                "id_assistente": assistentes_ids[i],
                "data_hora_inicio": inicio.isoformat(),
                "data_hora_fim": fim.isoformat(),
                "area_atendimento": random.choice(AREAS),
                }
            )

    return eventos_humanos