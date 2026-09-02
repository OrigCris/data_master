# 08. Instalação da CLI `dm`

A CLI `dm` unifica provisionamento, deploy e operação. É opcional (tudo pode ser
feito direto com `az`/`databricks`), mas recomendada.

## Instalação
```bash
git clone <repo> && cd data_master
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e cli/
dm --help
```

## Comandos
| Comando | Descrição |
|---|---|
| `dm provision -g <rg>` | Provisiona a infraestrutura (Bicep). `--what-if` pré-visualiza. |
| `dm deploy [all\|layer_*]` | Publica os Asset Bundles na ordem das camadas. |
| `dm run <job> -l <layer>` | Dispara um job de um bundle. |
| `dm validate` | Valida todos os bundles (essential/bronze/silver/gold/orchestration). |
| `dm info` | Mostra a configuração resolvida. |

> `--dry-run` imprime os comandos sem executá-los — útil para revisar antes de
> aplicar. Documentação completa em [`cli/README.md`](../cli/README.md).

---

[← Anterior: Pré-Requisitos](pre-requirements.md) | [Voltar ao índice](../README.md#documentação) | [Próximo: Como Usar →](how-to-use.md)
