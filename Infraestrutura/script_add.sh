# Dar acesso de leitura ao AKV para o FunctionAPP
az role assignment create \
    --assignee 38c023a2-13b1-4aec-af9d-6b0a76c7e340 \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show --name akvcjprd001 --query id -o tsv)

# Dar acesso de envio para a SPN (precisa do Application ID)
az role assignment create \
  --assignee 5f8e191a-c13b-44c5-b271-a5b81cacd409 \
  --role "Azure Event Hubs Data Sender" \
  --scope "/subscriptions/aa6ae7e7-9ce6-4420-b25e-08f234e5d25e/resourceGroups/rsgcjprd001/providers/Microsoft.EventHub/namespaces/evhnscjprd001"