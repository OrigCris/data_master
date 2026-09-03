# `dm` — Data Master CLI

CLI em Python (Typer) que unifica o ciclo de vida do projeto — provisionamento,
publicação e operação — numa única ferramenta aderente ao stack Azure/Python.

## Instalação

```bash
pip install -e cli/
dm --help
```

## Comandos

| Comando | O que faz |
|---|---|
| `dm provision -g <rg>` | Provisiona a infraestrutura via Bicep modular (`--what-if` para pré-visualizar). |
| `dm setup-spn -g <rg>` | Cria/rotaciona a SPN consumidora (Databricks → Event Hubs) e popula o Key Vault — Entra ID/Graph, o que o Bicep não faz. Idempotente. |
| `dm setup-databricks -g <rg>` | Configura o profile `prd` do Databricks CLI (host do workspace + `auth_type = azure-cli`) no `~/.databrickscfg`. Reconciliador. |
| `dm setup-catalog -g <rg>` | Provisiona/reconcilia o Unity Catalog: secret scope AKV, storage credential, external location e catalog `prd`. Reconciliador. |
| `dm create-cluster` | Cria/reutiliza um cluster all-purpose, imprime o `cluster_id` e o aponta nos `databricks.yml` dos bundles (`--no-set-in-bundles` para só imprimir). |
| `dm deploy [all\|essential\|layer_bronze\|layer_silver\|layer_gold\|orchestration]` | Publica os Databricks Asset Bundles (ordem do `all`: essential → camadas → orquestração). |
| `dm run <job> -l <bundle>` | Dispara um job de um bundle (ex.: `dm run setup-databases -l essential`, `dm run bronze-streaming -l layer_bronze`). |
| `dm validate` | Valida todos os bundles — essential/bronze/silver/gold/orchestration (`databricks bundle validate`). |
| `dm info` | Mostra a configuração resolvida. |

Use `--dry-run` nos comandos de Bicep/bundles (`provision`/`deploy`/`run`/`validate`)
para imprimir os comandos sem executá-los.

## Design

A lógica de montagem de comandos vive em [`dm/builders.py`](dm/builders.py) (funções
puras, sem dependências), separada da camada Typer em [`dm/main.py`](dm/main.py).
Isso mantém a CLI testável no CI — ver [`tests/unit/test_cli.py`](../tests/unit/test_cli.py) —
sem precisar de `az`, `databricks` ou um cluster.
