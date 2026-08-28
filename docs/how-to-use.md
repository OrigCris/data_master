# 09. Utilização — do zero ao dashboard

Passo a passo para colocar a plataforma em pé e rodar o pipeline ponta a ponta.

## 1. Provisionar a infraestrutura
```bash
az group create -n rsgcjtecprd001 -l brazilsouth
dm provision -g rsgcjtecprd001 --what-if    # revisar
dm provision -g rsgcjtecprd001              # aplicar
```
O Bicep cria Storage, Event Hubs, Key Vault, Function App, Databricks, observabilidade,
RBAC e as app settings da Function. Em seguida rode o **bootstrap** de identidade/segredos
(o que o Bicep não faz — SPNs + secrets):
```bash
bash infrastructure/bootstrap.sh            # cria SPNs e popula o Key Vault
```

## 2. Preparar o Unity Catalog
Configure o profile do Databricks CLI (uma vez) com a URL do workspace provisionado —
os bundles usam `profile: prd`, então o host **não** fica no repo:
```bash
databricks configure --profile prd --host https://adb-<seu_id>.azuredatabricks.net
# (informe o token quando pedido)
```
Provisione o Unity Catalog (secret scope + storage credential + external location +
catalog), sem operação manual no workspace:
```bash
bash Databricks/essential/setup_unity_catalog.sh
```
> Requer o **metastore** do Unity Catalog já atribuído ao workspace — etapa de
> *account admin*, no nível da conta (a única fora dos scripts).

Crie os schemas por camada:
- `Databricks/essential/create_databases.ipynb`

> A Silver controla o progresso pelo **checkpoint** do streaming, em
> `/Volumes/.../checkpoints/silver` (criado automaticamente na primeira execução).

E aplique a governança de PII (após criar as dimensões na Bronze), por um dos
caminhos:
- notebook `Databricks/essential/apply_pii_masks.ipynb` (usa a lib `security`), ou
- SQL estático em `database/ddl/004_governance.sql`.

## 3. Deploy dos jobs
Com o profile `prd` já configurado (passo 2), publique:
```bash
dm deploy all          # bronze → silver → gold → orchestration
```
A orquestração entra por último (resolve os job ids das camadas por nome).

## 4. Produzir e ingerir dados
- Faça o deploy da **Function App** (`function_app/`) — o TimerTrigger passa a
  enviar eventos aos Event Hubs.
- Rode a ingestão Bronze (ou aguarde o agendamento):
```bash
dm run bronze-streaming -l layer_bronze
dm run bronze-dim       -l layer_bronze
```

## 5. Processar
O pipeline diário roda pelo orquestrador (`dm-pipeline`), que encadeia
dims/silver/gold por dependência. Disparo manual:
```bash
dm run dm-pipeline -l orchestration
```
Ou execute uma camada isolada (ad-hoc): `dm run silver-job -l layer_silver`.

## 6. Visualizar
As tabelas `g_dm_callcenter.visao_*` estão prontas para BI. A observabilidade
operacional está no dashboard do Azure Monitor ([Observabilidade](observability.md)).

## Operação contínua
Após o primeiro ciclo, os **agendamentos** assumem (ver tabela em
[Arquitetura](architecture.md)). Para incidentes, consulte os
[Runbooks](runbooks).

---

[← Anterior: Instalação](installation.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Ingestão →](ingestion.md)
