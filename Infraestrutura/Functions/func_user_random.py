import logging, json, os, requests
import azure.functions as func
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.eventhub import EventHubProducerClient, EventData

app = func.FunctionApp()

@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False)
def func_negocios(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    # URL do seu Key Vault
    KEY_VAULT_URL = "https://akvcjprd001.vault.azure.net"

    # Criar a credencial com o managed identity do functionapp
    credential = DefaultAzureCredential()

    # Criar cliente para o Key Vault com as credenciais
    client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)

    # Recuperar segredos do Key Vault (Client ID, Client Secret e Tenant ID)
    try:
        client_id = client.get_secret("ServicePrincipalAppId").value
        client_secret = client.get_secret("ServicePrincipalSecret").value
        tenant_id = client.get_secret("ServicePrincipalTenantId").value
    except Exception as e:
        logging.error(f"Erro ao recuperar segredos do Key Vault: {e}")
        return
    
    # Usar as credenciais para criar uma credencial do SPN
    spn_credential = ClientSecretCredential(tenant_id, client_id, client_secret)

    # Obter valores do Event Hub das variáveis de ambiente configuradas
    eventhub_namespace = os.getenv('EVENTHUB_NAMESPACE_FULLY')
    eventhub_name = os.getenv('EVENTHUB_NAME')
    logging.info(eventhub_namespace)

    if not eventhub_namespace or not eventhub_name:
        logging.error('Event Hub Namespace ou Event Hub Name não configurados nas variáveis de ambiente.')
        return

    # Usar a credencial do SPN para autenticar no Event Hub
    producer_client = EventHubProducerClient(
        fully_qualified_namespace=eventhub_namespace,
        eventhub_name=eventhub_name,
        credential=spn_credential
    )

    # API de usuários fictícios
    api_users = 'https://random-data-api.com/api/v2/users'
    response = requests.get(url=api_users)

    if response.status_code != 200:
        logging.error(f"Erro ao buscar dados da API: {response.status_code}")
        return

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        logging.error("Erro ao decodificar JSON da API")
        return

    # Criar um evento e enviar para o Event Hub
    event_data_batch = producer_client.create_batch()
    event_data_batch.add(EventData(str(data)))

    # Enviar os dados
    producer_client.send_batch(event_data_batch)
    logging.info("Mensagem enviada para o Event Hub!")

    # Fechar a conexão do produtor
    producer_client.close()