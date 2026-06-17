# 09. Utilização — do zero ao dashboard

Passo a passo para colocar a plataforma em pé e rodar o pipeline ponta a ponta.

## 1. Provisionar a infraestrutura
```bash
az group create -n rsgcjtecprd001 -l brazilsouth
dm provision -g rsgcjtecprd001 --what-if    # revisar
dm provision -g rsgcjtecprd001              # aplicar
```
Isso cria Storage, Event Hubs, Key Vault, Function App, Databricks, observabilidade
e o RBAC. Em seguida rode o **bootstrap** de identidade/segredos (SPNs + secrets):
```bash
bash infrastructure/create_resouce.sh       # cria SPNs e popula o Key Vault
```

## 2. Preparar o Unity Catalog
No Databricks, execute o notebook essencial (uma vez):
- `Databricks/essential/create_databases.ipynb` — cria os schemas por camada.

> A Silver controla o progresso pelo **checkpoint** do streaming, em
> `/Volumes/.../checkpoints/silver` (criado automaticamente na primeira execução).

E aplique a governança de PII:
```sql
-- database/ddl/004_governance.sql (column masks do Unity Catalog)
```

## 3. Deploy dos jobs
```bash
dm deploy all          # bronze → silver → gold
```

## 4. Produzir e ingerir dados
- Faça o deploy da **Function App** (`function_app/`) — o TimerTrigger passa a
  enviar eventos aos Event Hubs.
- Rode a ingestão Bronze (ou aguarde o agendamento):
```bash
dm run bronze-streaming -l layer_bronze
dm run bronze-dim       -l layer_bronze
```

## 5. Processar
```bash
dm run silver-job -l layer_silver
dm run gold-job   -l layer_gold
```

## 6. Visualizar
As tabelas `g_dm_callcenter.visao_*` estão prontas para BI. A observabilidade
operacional está no dashboard do Azure Monitor ([Observabilidade](observability.md)).

## Operação contínua
Após o primeiro ciclo, os **agendamentos** assumem (ver tabela em
[Arquitetura](architecture.md)). Para incidentes, consulte os
[Runbooks](runbooks).

---

[← Anterior: Instalação](installation.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Ingestão →](ingestion.md)
