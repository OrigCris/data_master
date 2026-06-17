"""Construtores de comandos da CLI `dm` (lógica pura, sem dependências externas).

Cada função devolve a lista de argumentos a ser executada via subprocess. Manter
isso separado da camada Typer permite testá-los no CI sem `az`/`databricks` nem
o pacote `typer` instalados.
"""
from __future__ import annotations

from collections.abc import Sequence

LAYERS = ("layer_bronze", "layer_silver", "layer_gold")


def resolve_layers(layer: str) -> list[str]:
    """Expande 'all' para todas as camadas; valida nomes."""
    if layer == "all":
        return list(LAYERS)
    if layer in LAYERS:
        return [layer]
    raise ValueError(f"Camada inválida: {layer!r}. Use uma de {('all', *LAYERS)}.")


def bicep_whatif_cmd(resource_group: str, template: str, params: str) -> list[str]:
    return [
        "az", "deployment", "group", "what-if",
        "-g", resource_group, "-f", template, "-p", params,
    ]


def bicep_deploy_cmd(resource_group: str, template: str, params: str) -> list[str]:
    return [
        "az", "deployment", "group", "create",
        "-g", resource_group, "-f", template, "-p", params,
    ]


def bundle_validate_cmd() -> list[str]:
    return ["databricks", "bundle", "validate"]


def bundle_deploy_cmd(target: str) -> list[str]:
    return ["databricks", "bundle", "deploy", "-t", target]


def bundle_run_cmd(job: str, target: str) -> list[str]:
    return ["databricks", "bundle", "run", job, "-t", target]


def layer_dir(layer: str, base: str = "Databricks") -> str:
    return f"{base}/{layer}"


def build_pipeline_plan(layers: Sequence[str], target: str) -> list[tuple[str, list[str]]]:
    """Plano (dir, comando) de deploy por camada — usado por `dm deploy`."""
    return [(layer_dir(layer), bundle_deploy_cmd(target)) for layer in layers]
