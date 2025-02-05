import os
import requests
import json
import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.eventhub import EventHubProducerClient, EventData
from azure.schemaregistry import SchemaRegistryClient
from azure.schemaregistry.serializer.avroserializer import AvroSerializer

app = func.FunctionApp()

@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def func_negocios(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    # URL do seu Key Vault
    KEY_VAULT_URL = "https://akvcjprd001.vault.azure.net"

    # Criar a credencial com o managed identity do Function App
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

    # Criar credencial do SPN
    spn_credential = ClientSecretCredential(tenant_id, client_id, client_secret)

    # Obter valores das variáveis de ambiente
    eventhub_namespace = os.getenv('EVENTHUB_NAMESPACE_FULLY')
    eventhub_name = os.getenv('EVENTHUB_NAME')
    schemaregistry_fqdn = os.getenv('SCHEMAREGISTRY_FQDN')
    schema_group = os.getenv('SCHEMA_GROUP')
    schema_name = os.getenv('SCHEMA_NAME')
    
    if not eventhub_namespace or not eventhub_name or not schemaregistry_fqdn or not schema_group or not schema_name:
        logging.error('Variáveis de ambiente do Event Hub ou Schema Registry não configuradas corretamente.')
        return

    # Criar clientes do Event Hub e Schema Registry
    producer_client = EventHubProducerClient(
        fully_qualified_namespace=eventhub_namespace,
        eventhub_name=eventhub_name,
        credential=spn_credential
    )

    schema_registry_client = SchemaRegistryClient(
        fully_qualified_namespace=schemaregistry_fqdn,
        credential=spn_credential
    )

    avro_serializer = AvroSerializer(
        client=schema_registry_client,
        group_name=schema_group
    )

    # Obter o esquema Avro registrado no Schema Registry
    try:
        schema_definition = schema_registry_client.get_schema(schema_id='d9c48705ca474bdba3a64ea34e0b5113').definition
        logging.info(schema_definition)
    except Exception as e:
        logging.error(f"Erro ao recuperar o esquema Avro do Schema Registry: {e}")
        return

    # API de usuários fictícios
    api_users = 'https://random-data-api.com/api/v2/users'
    response = requests.get(url=api_users)

    if response.status_code != 200:
        logging.error(f"Erro ao buscar dados da API: {response.status_code}")
        return

    try:
        data = json.loads(response.content)
        if not isinstance(data, list):
            data = [data]  # Garante que os dados sejam uma lista
    except json.JSONDecodeError:
        logging.error("Erro ao decodificar JSON da API")
        return

    # Criar um batch de eventos
    event_data_batch = producer_client.create_batch()

    for record in data:
        try:
            serialized_data = avro_serializer.serialize(record, schema=schema_definition)
            event_data_batch.add(EventData(serialized_data))
        except Exception as e:
            logging.error(f"Erro ao serializar os dados: {e}")
            continue  # Pula este registro e tenta o próximo

    # Enviar os dados para o Event Hub
    try:
        producer_client.send_batch(event_data_batch)
        logging.info("Mensagem enviada para o Event Hub com Avro Schema!")
    except Exception as e:
        logging.error(f"Erro ao enviar dados para o Event Hub: {e}")
    
    # Fechar conexões
    producer_client.close()
    schema_registry_client.close()
