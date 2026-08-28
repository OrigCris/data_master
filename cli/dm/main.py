"""CLI `dm` — orquestra o ciclo de vida do Data Master (Azure).

Comandos:
    dm provision      Provisiona a infraestrutura (Bicep) e, opcionalmente, o bootstrap.
    dm deploy LAYER   Publica os Databricks Asset Bundles (bronze/silver/gold/all).
    dm run JOB        Dispara um job de um bundle.
    dm validate       Valida os bundles (bundle validate) das três camadas.
    dm info           Mostra a configuração resolvida.

Uso:
    pip install -e cli/        # instala o entrypoint `dm`
    dm provision --resource-group rsgcjtecprd001
    dm deploy all
    dm run bronze-streaming --layer layer_bronze
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

try:
    import typer
except ImportError:  # pragma: no cover
    print("Pacote 'typer' não instalado. Rode: pip install -e cli/", file=sys.stderr)
    raise

from dm.builders import (
    bicep_deploy_cmd,
    bicep_whatif_cmd,
    build_pipeline_plan,
    bundle_run_cmd,
    bundle_validate_cmd,
    layer_dir,
    resolve_layers,
)

app = typer.Typer(help="Data Master CLI — provisiona, publica e opera o pipeline de call center.")

REPO_ROOT = Path(__file__).resolve().parents[2]
BICEP_TEMPLATE = "infrastructure/bicep/main.bicep"
BICEP_PARAMS = "infrastructure/bicep/params/prd.bicepparam"
BOOTSTRAP = "infrastructure/bootstrap.sh"


def _run(cmd: list[str], cwd: Path | None = None, dry_run: bool = False) -> int:
    where = f" (cwd={cwd})" if cwd else ""
    typer.secho(f"$ {' '.join(cmd)}{where}", fg=typer.colors.BRIGHT_BLACK)
    if dry_run:
        return 0
    # No Windows, `az`/`databricks` são .cmd — o subprocess não resolve a extensão
    # sozinho. shutil.which encontra o caminho completo (usa o PATHEXT).
    exe = shutil.which(cmd[0]) or cmd[0]
    return subprocess.run([exe, *cmd[1:]], cwd=cwd).returncode


@app.command()
def provision(
    resource_group: str = typer.Option(..., "--resource-group", "-g"),
    what_if: bool = typer.Option(False, help="Apenas pré-visualiza (az what-if)."),
    dry_run: bool = typer.Option(False, help="Imprime os comandos sem executar."),
):
    """Provisiona a infraestrutura via Bicep modular."""
    cmd = (bicep_whatif_cmd if what_if else bicep_deploy_cmd)(
        resource_group, BICEP_TEMPLATE, BICEP_PARAMS
    )
    code = _run(cmd, cwd=REPO_ROOT, dry_run=dry_run)
    raise typer.Exit(code)


@app.command()
def deploy(
    layer: str = typer.Argument("all", help="layer_bronze | layer_silver | layer_gold | all"),
    target: str = typer.Option("prd", "--target", "-t"),
    dry_run: bool = typer.Option(False),
):
    """Publica os Databricks Asset Bundles por camada (em ordem bronze→silver→gold)."""
    layers = resolve_layers(layer)
    for rel_dir, cmd in build_pipeline_plan(layers, target):
        code = _run(cmd, cwd=REPO_ROOT / rel_dir, dry_run=dry_run)
        if code != 0:
            raise typer.Exit(code)
    typer.secho("✓ Deploy concluído", fg=typer.colors.GREEN)


@app.command()
def run(
    job: str = typer.Argument(..., help="Nome do recurso de job no bundle (ex.: bronze-streaming)."),
    layer: str = typer.Option(..., "--layer", "-l"),
    target: str = typer.Option("prd", "--target", "-t"),
    dry_run: bool = typer.Option(False),
):
    """Dispara a execução de um job de um bundle."""
    [resolved] = resolve_layers(layer)
    code = _run(bundle_run_cmd(job, target), cwd=REPO_ROOT / layer_dir(resolved), dry_run=dry_run)
    raise typer.Exit(code)


@app.command()
def validate(dry_run: bool = typer.Option(False)):
    """Valida os três bundles (CI-friendly)."""
    for layer in resolve_layers("all"):
        code = _run(bundle_validate_cmd(), cwd=REPO_ROOT / layer_dir(layer), dry_run=dry_run)
        if code != 0:
            raise typer.Exit(code)
    typer.secho("✓ Bundles válidos", fg=typer.colors.GREEN)


@app.command()
def info():
    """Mostra a configuração resolvida da CLI."""
    typer.echo(f"repo_root : {REPO_ROOT}")
    typer.echo(f"bicep     : {BICEP_TEMPLATE}")
    typer.echo(f"params    : {BICEP_PARAMS}")
    typer.echo(f"bootstrap : {BOOTSTRAP}")
    typer.echo("layers    : layer_bronze, layer_silver, layer_gold")


if __name__ == "__main__":  # pragma: no cover
    app()
