# Dar acesso de leitura ao AKV para o FunctionAPP
az role assignment create \
    --assignee d2af57a8-fe3f-4052-beae-96ff94e4ee78 \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show --name akvcjprd001 --query id -o tsv)

# Dar acesso de envio para a SPN (precisa do Application ID)
az role assignment create \
  --assignee 5e21175e-8f42-45c1-9994-3a7f79ec54e6 \
  --role "Azure Event Hubs Data Sender" \
  --scope "/subscriptions/aa6ae7e7-9ce6-4420-b25e-08f234e5d25e/resourceGroups/rsgcjprd001/providers/Microsoft.EventHub/namespaces/evhnscjprd001"