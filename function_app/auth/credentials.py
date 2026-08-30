from __future__ import annotations

from azure.identity import DefaultAzureCredential


def get_credential() -> DefaultAzureCredential:
    """Credencial de identidade do Function App para enviar ao Event Hubs.

    Em produção resolve para a **System-Assigned Managed Identity** do Function App
    (que recebe o papel `Azure Event Hubs Data Sender` no namespace); em
    desenvolvimento, para as credenciais do `az login`. Não há segredos no código
    nem no Key Vault — a autenticação é por identidade (Entra ID/OAuth).
    """
    return DefaultAzureCredential()
