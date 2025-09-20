from __future__ import annotations
from azure.identity import ClientSecretCredential
from services.keyvault import get_secret
from config.settings import settings
from exceptions.domain_exceptions import KeyVaultSecretError

def get_spn_credential() -> ClientSecretCredential:
    """Monta sempre a credencial do SPN a partir do Key Vault (MI para ler o KV)."""
    client_id = get_secret(settings.kv_secret_spn_client_id)
    tenant_id = get_secret(settings.kv_secret_spn_tenant_id)
    client_secret = get_secret(settings.kv_secret_spn_client_secret)

    if not all([client_id, tenant_id, client_secret]):
        raise KeyVaultSecretError("Segredos do SPN ausentes ou vazios no Key Vault.")

    return ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)