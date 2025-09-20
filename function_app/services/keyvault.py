from __future__ import annotations
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from config.settings import settings
from exceptions.domain_exceptions import KeyVaultSecretError

_client: SecretClient | None = None

def _get_client() -> SecretClient:
    """
    Retorna um SecretClient reutilizável (cacheado em _client).
    Usa Managed Identity via DefaultAzureCredential.
    Lança KeyVaultSecretError se KV_URL não estiver configurado.
    """
    global _client  # declara que vamos modificar a variável global _client

    # Se ainda não existe um cliente cacheado, criamos um novo
    if _client is None:
        # Verifica se a URI do Key Vault foi configurada
        if not settings.kv_url:
            # Interrompe com uma exceção clara se a configuração estiver ausente
            raise KeyVaultSecretError("KV_URL não configurado.")
        
        # Cria uma credencial que prioriza a Managed Identity do Function App.
        cred = DefaultAzureCredential()

        # Instancia o SecretClient apontando para o seu Key Vault, autenticado com a Managed Identity.
        _client = SecretClient(vault_url=settings.kv_url, credential=cred)

    # Retorna o cliente
    return _client

def get_secret(name: str) -> Optional[str]:
    """
    Lê o valor de uma secret do Key Vault pelo nome.
    Retorna o valor (string) se encontrar; caso qualquer erro ocorra, retorna None.
    """

    # Obtém o cliente (cria se ainda não existir)
    client = _get_client()
    try:
        # Chama a API do Key Vault para buscar o segredo e retorna apenas o .value
        return client.get_secret(name).value
    except Exception as exc:
        # Captura qualquer exceção (por exemplo: segredo não existe, acesso negado, rede, etc.)
        # Retorna None para o chamador lidar com fallback/erro de forma controlada.
        return None