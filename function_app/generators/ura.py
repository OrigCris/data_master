from __future__ import annotations
import uuid
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("pt_BR")

OpcoesURA = [
    "EMP", "CRT", "FIN", "COB", "INF", "SEG", "BO2", "CAD", "LIM", "BLO", "TRS", "SEN", "INV", "PIX"
]

def gerar_eventos_ura(min_chamadas: int = 8, max_chamadas: int = 30) -> list[dict]:
    eventos: list[dict] = []
    now = datetime.now()
    num_chamadas = random.randint(min_chamadas, max_chamadas)

    for _ in range(num_chamadas):
        inicio = now + timedelta(seconds=random.randint(1, 5))
        fim = inicio + timedelta(minutes=random.randint(2, 5))
        codigo_opcao = random.choice(OpcoesURA)
        derivado = random.choices([True, False], weights=[30, 70])[0]

        eventos.append(
            {
                "id_chamada": str(uuid.uuid4()),
                "id_cliente": random.randint(1, 1000),
                "data_hora_inicio": inicio.isoformat(),
                "data_hora_fim": fim.isoformat(),
                "autenticado": random.choices([True, False], weights=[85, 15])[0],
                "opcoes_navegadas": random.randint(1, 10),
                "codigo_opcao": codigo_opcao,
                "derivado_atendimento": derivado,
                "id_fila": f"URA_{codigo_opcao}",
            }
        )

    return eventos