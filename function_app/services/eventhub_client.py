from __future__ import annotations

import json
from collections.abc import Iterable, Sequence

from azure.eventhub import EventData, EventHubProducerClient
from azure.eventhub.exceptions import EventHubError
from config.settings import settings
from exceptions.domain_exceptions import EventBuildError, EventSendError


def _producer(eventhub_name: str, credential) -> EventHubProducerClient:
    if not settings.event_hub_fqdn:
        raise ValueError("EVENTHUB_NAMESPACE_FQDN não configurado.")
    return EventHubProducerClient(
        fully_qualified_namespace=settings.event_hub_fqdn,
        eventhub_name=eventhub_name,
        credential=credential,
    )

def _to_event_data(items: Iterable[object]) -> list[EventData]:
    try:
        return [EventData(json.dumps(item, default=lambda o: o.__dict__)) for item in items]
    except Exception as exc: # noqa: BLE001
        raise EventBuildError(f"Falha ao serializar eventos: {exc}") from exc

def send_events(eventhub_name: str, credential, items: Sequence[object]) -> int:
    if not items:
        return 0

    events = _to_event_data(items)
    total_sent = 0

    try:
        producer = _producer(eventhub_name, credential)
        try:
            batch = producer.create_batch()
            for ev in events:
                try:
                    batch.add(ev)
                except ValueError as exc:
                    # ValueError com o batch VAZIO significa que o próprio evento não
                    # cabe no tamanho máximo — não adianta enviar/recriar; falha claro.
                    if len(batch) == 0:
                        raise EventSendError(
                            "Evento individual excede o tamanho máximo do batch do Event Hubs."
                        ) from exc
                    # batch cheio: envia o acumulado e recomeça com o evento atual.
                    producer.send_batch(batch)
                    total_sent += len(batch)
                    batch = producer.create_batch()
                    try:
                        batch.add(ev)
                    except ValueError as exc:
                        raise EventSendError(
                            "Evento individual excede o tamanho máximo do batch do Event Hubs."
                        ) from exc
            if len(batch) > 0:
                producer.send_batch(batch)
                total_sent += len(batch)
        finally:
            producer.close()

        return total_sent

    except EventHubError as exc:
        raise EventSendError(f"Erro do Event Hubs: {exc}") from exc
    except Exception as exc:
        raise EventSendError(str(exc)) from exc
