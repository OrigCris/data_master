# 09. Utilização — do zero ao dashboard

Passo a passo para colocar a plataforma em pé e rodar o pipeline ponta a ponta.

## 1. Provisionar a infraestrutura
```bash
dm provision -g rsgcjtecprd001 --what-if    # revisar
dm provision -g rsgcjtecprd001              # aplicar
```
O `provision` **cria o Resource Group** (idempotente, na região do `.bicepparam`) e
aplica o Bicep — não precisa de `az group create` à parte.
O Bicep cria Storage, Event Hubs, Key Vault, Function App, Databricks, observabilidade,
RBAC (incl. a MI da Function → *Data Sender*) e as app settings. Em seguida rode a
etapa de identidade/segredos (o que o Bicep não faz — a SPN consumidora):
```bash
dm setup-spn -g rsgcjtecprd001              # cria a SPN consumidora e popula o Key Vault
```

## 2. Preparar o Unity Catalog
Configure o profile do Databricks CLI (uma vez) — resolve o host do workspace no Azure
e grava o `~/.databrickscfg` (os bundles usam `profile: prd`, então o host **não** fica
no repo):
```bash
dm setup-databricks -g rsgcjtecprd001
```
> Grava `auth_type = azure-cli`: a autenticação reaproveita o `az login` (sem browser à
> parte) e fornece o token do Entra ID que o **secret scope AKV-backed** (passo seguinte)
> exige — um PAT não satisfaz. Após um rebuild do RG, rode de novo para atualizar o host.

Provisione o Unity Catalog (secret scope + storage credential + external location +
catalog).
```bash
dm setup-catalog -g rsgcjtecprd001
```
> Reconciliador: após um rebuild do RG, rodar de novo reaponta a storage credential
> para o Access Connector recriado (sem tocar em external location, catalog ou schemas).
> Requer o **metastore** do Unity Catalog já atribuído ao workspace — etapa de
> *account admin*, no nível da conta (a única fora do CLI).

Crie os schemas e os **Volumes de checkpoint** publicando o bundle `essential` e
rodando o job (não agendado) — sem import manual pela UI:
```bash
dm deploy essential
dm run setup-databases -l essential
```
> Cria os schemas `b_/s_/g_dm_callcenter` e os **Volumes gerenciados** `checkpoints`
> (Bronze e Silver). A Silver controla o progresso pelo **checkpoint** do streaming, em
> `/Volumes/prd/s_dm_callcenter/checkpoints/silver` (o subdiretório é criado na primeira
> execução; o Volume, aqui).

Crie as **funções de máscara de PII** — **antes** das dimensões, pois cada dimensão
aplica as máscaras às próprias colunas ao ser criada:
```bash
dm run setup-pii-functions -l essential
```
> Alternativa declarativa equivalente: o SQL estático em `database/ddl/004_governance.sql`.

## 3. Deploy dos jobs
Com o profile `prd` já configurado (passo 2), publique:
```bash
dm deploy all          # essential → bronze → silver → gold → orchestration
```
A orquestração entra por último (resolve os job ids das camadas por nome). O `essential`
já foi publicado no passo 2, mas `all` o inclui de novo (idempotente).

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
