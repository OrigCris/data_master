from __future__ import annotations

import random
import uuid
from collections.abc import Iterable
from datetime import date


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
                    # data (não timestamp): a Silver faz parse como DateType.
                    # Enviar um timestamp ISO completo resultaria em DT_ENVI nulo
                    # e a pesquisa sumiria do cálculo de NPS no Gold.
                    "data_envio": date.today().isoformat(),
                    # Escala NPS clássica: 0–10.
                    "nota": random.randint(0, 10),
                }
            )
    return eventos
