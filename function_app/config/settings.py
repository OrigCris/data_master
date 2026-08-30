from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Carrega configurações via variáveis de ambiente."""

    # Event Hubs (autenticação por Managed Identity — sem segredos em configuração)
    event_hub_fqdn: str = os.environ.get("EVENTHUB_NAMESPACE_FQDN", "").strip()
    eh_name_ura: str = os.environ.get("EH_NAME_URA", "evh_cj_tec_ura").strip()
    eh_name_calls: str = os.environ.get("EH_NAME_CALLS", "evh_cj_tec_calls").strip()
    eh_name_surveys: str = os.environ.get("EH_NAME_SURVEYS", "evh_cj_tec_surveys").strip()

settings = Settings()
