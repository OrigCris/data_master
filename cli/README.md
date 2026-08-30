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
| `dm deploy [all\|layer_bronze\|layer_silver\|layer_gold]` | Publica os Databricks Asset Bundles na ordem das camadas. |
| `dm run <job> -l <layer>` | Dispara um job de um bundle (ex.: `dm run bronze-streaming -l layer_bronze`). |
| `dm validate` | Valida todos os bundles — bronze/silver/gold/orchestration (`databricks bundle validate`). |
| `dm info` | Mostra a configuração resolvida. |

Use `--dry-run` em qualquer comando para imprimir os comandos sem executá-los.

## Design

A lógica de montagem de comandos vive em [`dm/builders.py`](dm/builders.py) (funções
puras, sem dependências), separada da camada Typer em [`dm/main.py`](dm/main.py).
Isso mantém a CLI testável no CI — ver [`tests/unit/test_cli.py`](../tests/unit/test_cli.py) —
sem precisar de `az`, `databricks` ou um cluster.
