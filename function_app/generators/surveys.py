from __future__ import annotations
import uuid
import random
from datetime import datetime
from typing import Iterable

def gerar_fato_pesquisa_satisfacao(eventos_ura: Iterable[dict]) -> list[dict]:
    eventos: list[dict] = []

    for e in eventos_ura:
        if not e.get("derivado_atendimento"):
            continue
        if random.random() < 0.7:
            eventos.append(
                {
                    "id_chamada": e["id_chamada"],
                    "id_pesquisa": str(uuid.uuid4()),
                    "data_envio": datetime.now().isoformat(),
                    "nota": random.randint(1, 10),
                }
            )
    return eventos