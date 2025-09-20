from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    """Carrega configurações via variáveis de ambiente."""

    # Key Vault
    kv_url: str = os.environ.get("KV_URL", "").strip()
    kv_secret_spn_client_id: str = os.environ.get("KV_SECRET_SPN_CLIENT_ID", "ServicePrincipalAppId").strip()
    kv_secret_spn_tenant_id: str = os.environ.get("KV_SECRET_SPN_TENANT_ID", "ServicePrincipalTenantId").strip()
    kv_secret_spn_client_secret: str = os.environ.get("KV_SECRET_SPN_CLIENT_SECRET", "ServicePrincipalSecret").strip()

    # Event Hubs
    event_hub_fqdn: str = os.environ.get("EVENTHUB_NAMESPACE_FQDN", "").strip()
    eh_name_ura: str = os.environ.get("EH_NAME_URA", "evh_cj_tec_ura").strip()
    eh_name_calls: str = os.environ.get("EH_NAME_CALLS", "evh_cj_tec_calls").strip()
    eh_name_surveys: str = os.environ.get("EH_NAME_SURVEYS", "evh_cj_tec_surveys").strip()

settings = Settings()