"""Testes dos construtores de comando da CLI `dm` (sem az/databricks/typer)."""
import pytest
from dm.builders import (
    LAYERS,
    bicep_deploy_cmd,
    build_pipeline_plan,
    bundle_deploy_cmd,
    bundle_run_cmd,
    layer_dir,
    resolve_layers,
)


def test_resolve_layers_all():
    assert resolve_layers("all") == list(LAYERS)


def test_resolve_layers_single():
    assert resolve_layers("layer_silver") == ["layer_silver"]


def test_resolve_layers_invalid():
    with pytest.raises(ValueError):
        resolve_layers("ouro")


def test_bundle_deploy_cmd():
    assert bundle_deploy_cmd("prd") == ["databricks", "bundle", "deploy", "-t", "prd"]


def test_bundle_run_cmd():
    assert bundle_run_cmd("bronze-streaming", "prd") == [
        "databricks", "bundle", "run", "bronze-streaming", "-t", "prd",
    ]


def test_bicep_deploy_cmd():
    cmd = bicep_deploy_cmd("rg1", "main.bicep", "prd.bicepparam")
    assert cmd[:5] == ["az", "deployment", "group", "create", "-g"]
    assert "main.bicep" in cmd and "prd.bicepparam" in cmd


def test_pipeline_plan_ordena_camadas():
    plan = build_pipeline_plan(resolve_layers("all"), "prd")
    dirs = [d for d, _ in plan]
    assert dirs == [layer_dir(layer) for layer in LAYERS]
    assert dirs[0].endswith("layer_bronze")
    assert dirs[-1].endswith("layer_gold")
