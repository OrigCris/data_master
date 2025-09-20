class KeyVaultSecretError(Exception):
    """Falha ao recuperar segredos do Key Vault."""

class EventBuildError(Exception):
    """Falha ao serializar/empacotar eventos para envio."""

class EventSendError(Exception):
    """Falha ao enviar eventos ao Event Hubs."""