"""CLI `dm` — orquestra o ciclo de vida do Data Master (Azure).

Comandos:
    dm provision      Cria o Resource Group e provisiona a infraestrutura (Bicep).
    dm setup-spn      Cria/rotaciona a SPN consumidora (Databricks → Event Hubs) e
                      popula o Key Vault (Entra ID/Graph — o que o Bicep não faz).
    dm setup-databricks  Configura o profile `prd` do Databricks CLI (host do workspace
                      + auth via Azure CLI) no ~/.databrickscfg.
    dm setup-catalog  Provisiona/reconcilia o Unity Catalog (secret scope, storage
                      credential, external location e catalog).
    dm create-cluster Cria/reutiliza um cluster all-purpose e imprime o cluster_id.
    dm deploy LAYER   Publica os Databricks Asset Bundles
                      (essential/bronze/silver/gold/orchestration/all).
    dm run JOB        Dispara um job de um bundle.
    dm validate       Valida todos os bundles (bundle validate).
    dm info           Mostra a configuração resolvida.

Uso:
    pip install -e cli/        # instala o entrypoint `dm`
    dm provision --resource-group rsgcjtecprd001
    dm setup-spn --resource-group rsgcjtecprd001
    dm deploy all
    dm run bronze-streaming --layer layer_bronze
"""
from __future__ import annotations

import configparser
import json
import re
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


def _run(cmd: list[str], cwd: Path | None = None, dry_run: bool = False) -> int:
    where = f" (cwd={cwd})" if cwd else ""
    typer.secho(f"$ {' '.join(cmd)}{where}", fg=typer.colors.BRIGHT_BLACK)
    if dry_run:
        return 0
    # No Windows, `az`/`databricks` são .cmd — o subprocess não resolve a extensão
    # sozinho. shutil.which encontra o caminho completo (usa o PATHEXT).
    exe = shutil.which(cmd[0]) or cmd[0]
    return subprocess.run([exe, *cmd[1:]], cwd=cwd).returncode


def _az(args: list[str], *, capture: bool = False, check: bool = True) -> str:
    """Executa `az` (resolvendo o .cmd no Windows). Com `capture`, devolve o stdout
    sem ecoá-lo — usado para segredos/ids. Falha aborta a CLI, como `set -e`."""
    exe = shutil.which("az") or "az"
    if capture:
        r = subprocess.run([exe, *args], capture_output=True, text=True)
        if check and r.returncode != 0:
            typer.secho(r.stderr.strip(), fg=typer.colors.RED)
            raise typer.Exit(r.returncode)
        return r.stdout.strip()
    rc = subprocess.run([exe, *args]).returncode
    if check and rc != 0:
        raise typer.Exit(rc)
    return ""


def _dbx(args: list[str], *, profile: str = "prd", check: bool = True) -> subprocess.CompletedProcess:
    """Executa a Databricks CLI (capturando stdout/stderr) e devolve o CompletedProcess.
    Com `check`, falha aborta a CLI; sem, o chamador inspeciona `returncode`/`stdout`
    (usado nos `get` que retornam ≠0 quando o objeto ainda não existe)."""
    exe = shutil.which("databricks") or "databricks"
    r = subprocess.run([exe, "--profile", profile, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        typer.secho(r.stderr.strip() or r.stdout.strip(), fg=typer.colors.RED)
        raise typer.Exit(r.returncode)
    return r


def _json_body(text: str, default):
    """Parseia JSON tolerando prefixo não-JSON no stdout (a Databricks CLI pode escrever
    um aviso antes do corpo). Devolve `default` se não houver JSON válido."""
    text = (text or "").strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
        if starts:
            try:
                return json.loads(text[min(starts):])
            except json.JSONDecodeError:
                pass
    return default


def _bicep_location(default: str = "westus") -> str:
    """Lê a região do `.bicepparam` (fonte única) para criar o Resource Group."""
    try:
        text = (REPO_ROOT / BICEP_PARAMS).read_text(encoding="utf-8")
        m = re.search(r"param\s+location\s*=\s*'([^']+)'", text)
        return m.group(1) if m else default
    except OSError:
        return default


@app.command()
def provision(
    resource_group: str = typer.Option(..., "--resource-group", "-g"),
    what_if: bool = typer.Option(False, help="Apenas pré-visualiza (az what-if)."),
    dry_run: bool = typer.Option(False, help="Imprime os comandos sem executar."),
):
    """Cria o Resource Group (idempotente) e provisiona a infraestrutura via Bicep."""
    location = _bicep_location()
    # O deployment é escopo de RG (what-if inclusive), então o grupo precisa existir.
    # `az group create` é idempotente — no-op se já existe com a mesma região.
    code = _run(["az", "group", "create", "-n", resource_group, "-l", location], cwd=REPO_ROOT, dry_run=dry_run)
    if code != 0:
        raise typer.Exit(code)
    cmd = (bicep_whatif_cmd if what_if else bicep_deploy_cmd)(
        resource_group, BICEP_TEMPLATE, BICEP_PARAMS
    )
    raise typer.Exit(_run(cmd, cwd=REPO_ROOT, dry_run=dry_run))


@app.command(name="setup-spn")
def setup_spn(
    resource_group: str = typer.Option("rsgcjtecprd001", "--resource-group", "-g"),
    namespace: str = typer.Option("evhnscjtecprd001", help="Event Hubs Namespace."),
    key_vault: str = typer.Option("akvcjtecprd001", help="Key Vault."),
    spn_name: str = typer.Option("spn_dtb_consumer", help="Nome da SPN consumidora."),
):
    """Cria/rotaciona a SPN consumidora (Databricks → Event Hubs) e popula o Key Vault.

    Faz o que o Bicep não faz (Microsoft Graph + segredos rotativos): SPN com o papel
    mínimo 'Azure Event Hubs Data Receiver' no namespace, os segredos no Key Vault e as
    access policies do vault (operador → Set; app first-party 'AzureDatabricks' →
    Get/List, exigidas pelo AKV-backed secret scope). Idempotente. Requer `az login` e
    os recursos já provisionados (`dm provision`).
    """
    sub = _az(["account", "show", "--query", "id", "-o", "tsv"], capture=True)
    operator_oid = _az(["ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"], capture=True)
    ns_id = (
        f"/subscriptions/{sub}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.EventHub/namespaces/{namespace}"
    )

    # Operador pode gravar segredos no vault (modelo access policy).
    _az(["keyvault", "set-policy", "--name", key_vault, "--object-id", operator_oid,
         "--secret-permissions", "get", "list", "set"], capture=True)

    # SPN idempotente: reutiliza a identidade e rotaciona a credencial, ou cria já com o
    # único papel necessário no escopo do namespace (sem Contributor no Resource Group).
    existing = _az(["ad", "sp", "list", "--display-name", spn_name, "--query", "[0].appId", "-o", "tsv"], capture=True)
    if not existing:
        out = _az(["ad", "sp", "create-for-rbac", "--name", spn_name,
                   "--role", "Azure Event Hubs Data Receiver", "--scopes", ns_id,
                   "-o", "json"], capture=True)
        sp = json.loads(out)
        app_id, secret, tenant = sp["appId"], sp["password"], sp["tenant"]
        typer.secho(f"[+] SPN '{spn_name}' criada (appId={app_id})", fg=typer.colors.GREEN)
    else:
        app_id = existing
        tenant = _az(["account", "show", "--query", "tenantId", "-o", "tsv"], capture=True)
        secret = _az(["ad", "sp", "credential", "reset", "--id", app_id, "--query", "password", "-o", "tsv"], capture=True)
        _az(["role", "assignment", "create", "--assignee", app_id,
             "--role", "Azure Event Hubs Data Receiver", "--scope", ns_id], capture=True, check=False)
        typer.secho(f"[=] SPN '{spn_name}' já existia (appId={app_id}) — credencial rotacionada", fg=typer.colors.YELLOW)

    for name, value in (
        ("ServicePrincipalDTBAppId", app_id),
        ("ServicePrincipalDTBSecret", secret),
        ("ServicePrincipalDTBTenantId", tenant),
    ):
        _az(["keyvault", "secret", "set", "--vault-name", key_vault, "--name", name, "--value", value], capture=True)

    # App first-party do Databricks precisa de Get/List para o AKV-backed secret scope.
    dbx_oid = _az(["ad", "sp", "list", "--display-name", "AzureDatabricks", "--query", "[0].id", "-o", "tsv"], capture=True)
    _az(["keyvault", "set-policy", "--name", key_vault, "--object-id", dbx_oid,
         "--secret-permissions", "get", "list"], capture=True)

    typer.secho("✓ SPN consumidora pronta (Data Receiver); segredos e access policies no Key Vault", fg=typer.colors.GREEN)


@app.command(name="setup-databricks")
def setup_databricks(
    resource_group: str = typer.Option("rsgcjtecprd001", "--resource-group", "-g"),
    workspace: str = typer.Option("dbwcjtecprd001", help="Databricks workspace."),
    profile: str = typer.Option("prd", "--profile", "-p"),
):
    """Configura o profile do Databricks CLI no ~/.databrickscfg.

    Resolve o host do workspace no Azure e grava o profile com `auth_type = azure-cli`
    e o `azure_tenant_id` do `az login`: a autenticação reaproveita o `az login` (sem
    browser à parte) e fornece o token do Entra ID que o AKV-backed secret scope exige
    (um PAT não satisfaz); o tenant é fixado porque a auto-descoberta da CLI Databricks
    pode extrair um valor inválido do host. Reconciliador — reescreve a seção a cada
    execução, atualizando host e tenant se o workspace mudou (ex.: rebuild do RG) e
    preservando os demais profiles. Requer `az login` e o workspace já provisionado.
    """
    # A extensão 'databricks' do az resolve o host do workspace (idempotente).
    _az(["extension", "add", "-n", "databricks", "--only-show-errors"], capture=True, check=False)
    url = _az(["databricks", "workspace", "show", "-g", resource_group, "-n", workspace,
               "--query", "workspaceUrl", "-o", "tsv"], capture=True)
    host = f"https://{url}"
    # Tenant fixado explicitamente: sem ele, a CLI Databricks tenta auto-descobrir o tenant
    # sondando o host e, em alguns workspaces, extrai um valor inválido (ex.: 'login.html'),
    # quebrando o azure-cli auth. O tenant do `az login` é a fonte correta.
    tenant = _az(["account", "show", "--query", "tenantId", "-o", "tsv"], capture=True)

    cfg_path = Path.home() / ".databrickscfg"
    cfg = configparser.ConfigParser()
    cfg.read(cfg_path)
    # Reescreve a seção do zero: para azure-cli auth só valem host + auth_type. Campos
    # de logins anteriores (azure_tenant_id, account_id, workspace_id, token) ficariam
    # obsoletos após um rebuild e quebrariam o auth — por isso são descartados. As demais
    # seções/profiles do arquivo são preservadas.
    existed = cfg.has_section(profile)
    if existed:
        cfg.remove_section(profile)
    cfg.add_section(profile)
    cfg.set(profile, "host", host)
    cfg.set(profile, "auth_type", "azure-cli")
    cfg.set(profile, "azure_tenant_id", tenant)
    with cfg_path.open("w", encoding="utf-8") as fh:
        cfg.write(fh)

    verb = "atualizado" if existed else "criado"
    typer.secho(f"✓ profile [{profile}] {verb} em {cfg_path} (host={host}, auth_type=azure-cli, tenant fixado)", fg=typer.colors.GREEN)
    typer.secho(f"  valide com: databricks --profile {profile} current-user me", fg=typer.colors.BRIGHT_BLACK)


def _credential_is_stale(validate: subprocess.CompletedProcess) -> bool:
    """A storage credential está obsoleta se a validação erra (returncode ≠0) ou traz
    algum resultado FAIL — capta o caso de rebuild em que o Access Connector mantém o
    mesmo resource id, mas a identidade por trás mudou."""
    if validate.returncode != 0:
        return True
    results = _json_body(validate.stdout, {}).get("results", [])
    return any(r.get("result") == "FAIL" for r in results)


@app.command(name="setup-catalog")
def setup_catalog(
    resource_group: str = typer.Option("rsgcjtecprd001", "--resource-group", "-g"),
    profile: str = typer.Option("prd", "--profile", "-p"),
):
    """Provisiona/reconcilia o Unity Catalog: secret scope, storage credential, external
    location e catalog `prd`.

    Reconciliador (não apenas "existe → pula"): cada objeto é levado ao estado desejado.
    Em especial, após um rebuild do RG o Access Connector é recriado e sua identidade
    muda (mesmo mantendo o nome) — a storage credential fica obsoleta e o managed storage
    falha com UC_AZURE_CREDENTIAL_NOT_FOUND. Aqui a credential é revalidada e reapontada
    in place (sem deletar external location, catalog ou schemas). Requer `az login` e o
    profile do Databricks configurado (`dm setup-databricks`).
    """
    storage_account = "stacjtecprd001"
    container = "ctcjtecprd001"
    key_vault = "akvcjtecprd001"
    access_connector = "ac-databricks-uc"
    catalog = "prd"
    secret_scope = "data-master-akv"
    storage_credential = "sc-dm-adls"
    external_location = "el-dm-lake"

    # Ids resolvidos SEMPRE do Azure (o ac_id reflete o Access Connector atual).
    ac_id = _az(["databricks", "access-connector", "show", "-g", resource_group,
                 "-n", access_connector, "--query", "id", "-o", "tsv"], capture=True)
    kv_id = _az(["keyvault", "show", "-n", key_vault, "--query", "id", "-o", "tsv"], capture=True)
    kv_dns = f"https://{key_vault}.vault.azure.net/"
    lake_url = f"abfss://{container}@{storage_account}.dfs.core.windows.net/"

    def dbx(args, check=True):
        return _dbx(args, profile=profile, check=check)

    # 1) Secret scope (AKV-backed). Referencia o Key Vault por resource_id (ARM, por nome,
    # estável no rebuild) e é lido pela app first-party 'AzureDatabricks' via access policy
    # — sem identidade por GUID, não sofre o "stale" do Access Connector: basta existir.
    scopes = dbx(["secrets", "list-scopes", "-o", "json"], check=False)
    # -o json devolve uma lista de scopes (ou, em outras versões, {"scopes": [...]}).
    scope_data = _json_body(scopes.stdout, []) if scopes.returncode == 0 else []
    scope_list = scope_data.get("scopes", []) if isinstance(scope_data, dict) else scope_data
    existing_scopes = [s.get("name") for s in scope_list]
    if secret_scope in existing_scopes:
        typer.secho(f"[=] secret scope '{secret_scope}' já existe", fg=typer.colors.BRIGHT_BLACK)
    else:
        body = {"scope": secret_scope, "scope_backend_type": "AZURE_KEYVAULT",
                "backend_azure_keyvault": {"resource_id": kv_id, "dns_name": kv_dns}}
        dbx(["secrets", "create-scope", "--json", json.dumps(body)])
        typer.secho(f"[+] secret scope '{secret_scope}' criado", fg=typer.colors.GREEN)

    # 2) Storage credential (reconcilia contra o Access Connector atual).
    cred_json = {"azure_managed_identity": {"access_connector_id": ac_id}}
    got = dbx(["storage-credentials", "get", storage_credential, "-o", "json"], check=False)
    if got.returncode == 0:
        cur_ac_id = _json_body(got.stdout, {}).get("azure_managed_identity", {}).get("access_connector_id", "")
        if cur_ac_id != ac_id:
            dbx(["storage-credentials", "update", storage_credential, "--force", "--json", json.dumps(cred_json)])
            typer.secho(f"[~] storage credential '{storage_credential}' atualizada para o Access Connector atual", fg=typer.colors.YELLOW)
        else:
            validate = dbx(["storage-credentials", "validate", "--storage-credential-name",
                            storage_credential, "--url", lake_url, "-o", "json"], check=False)
            if _credential_is_stale(validate):
                dbx(["storage-credentials", "update", storage_credential, "--force", "--json", json.dumps(cred_json)])
                typer.secho(f"[~] storage credential '{storage_credential}' reconciliada (mesmo id, identidade do Access Connector estava obsoleta)", fg=typer.colors.YELLOW)
            else:
                typer.secho(f"[=] storage credential '{storage_credential}' já está atualizada", fg=typer.colors.BRIGHT_BLACK)
    else:
        dbx(["storage-credentials", "create", "--json", json.dumps({"name": storage_credential, **cred_json})])
        typer.secho(f"[+] storage credential '{storage_credential}' criado", fg=typer.colors.GREEN)

    # 3) External location (reconcilia url + credential_name).
    el_desired = {"url": lake_url, "credential_name": storage_credential}
    got_el = dbx(["external-locations", "get", external_location, "-o", "json"], check=False)
    if got_el.returncode == 0:
        el = _json_body(got_el.stdout, {})
        if el.get("url") == lake_url and el.get("credential_name") == storage_credential:
            typer.secho(f"[=] external location '{external_location}' já está correta", fg=typer.colors.BRIGHT_BLACK)
        else:
            dbx(["external-locations", "update", external_location, "--json", json.dumps(el_desired)])
            typer.secho(f"[~] external location '{external_location}' atualizada (url/credential alinhados)", fg=typer.colors.YELLOW)
    else:
        dbx(["external-locations", "create", "--json", json.dumps({"name": external_location, **el_desired})])
        typer.secho(f"[+] external location '{external_location}' criado", fg=typer.colors.GREEN)

    # 4) Catalog. storage_root é IMUTÁVEL após a criação; o acesso ao managed storage é
    # reconciliado no passo 2 (credential). Basta criar se ainda não existe.
    catalog_storage = f"{lake_url}managed/prd"
    if dbx(["catalogs", "get", catalog, "-o", "json"], check=False).returncode == 0:
        typer.secho(f"[=] catalog '{catalog}' já existe", fg=typer.colors.BRIGHT_BLACK)
    else:
        dbx(["catalogs", "create", "--json", json.dumps({"name": catalog, "storage_root": catalog_storage})])
        typer.secho(f"[+] catalog '{catalog}' criado com managed storage em '{catalog_storage}'", fg=typer.colors.GREEN)

    typer.secho("✓ Unity Catalog pronto.", fg=typer.colors.GREEN)
    typer.secho("  Próximo passo: dm run setup-databases -l essential", fg=typer.colors.BRIGHT_BLACK)


@app.command(name="create-cluster")
def create_cluster(
    name: str = typer.Option("dm-all-purpose", help="Nome do cluster all-purpose."),
    node_type: str = typer.Option("Standard_D4ds_v6", help="SKU da VM dos nós."),
    workers: int = typer.Option(1, help="Número de workers (0 = single node)."),
    spark_version: str = typer.Option("15.4.x-scala2.12", help="Databricks Runtime (LTS)."),
    autotermination: int = typer.Option(20, help="Minutos ociosos até o auto-desligamento."),
    profile: str = typer.Option("prd", "--profile", "-p"),
):
    """Cria (ou reutiliza) um cluster all-purpose e imprime o `cluster_id`.

    Cluster pequeno com `data_security_mode = SINGLE_USER` (exigido pelo Unity Catalog) e
    autotermination curto (FinOps). Idempotente: se já existe um cluster com o mesmo nome,
    devolve o id existente em vez de criar outro. Serve para execução interativa/ad-hoc: os
    jobs dos bundles sobem com **job cluster** próprio, então o id não é escrito em lugar
    nenhum. Requer o profile do Databricks configurado (`dm setup-databricks`).
    """
    def dbx(args, check=True):
        return _dbx(args, profile=profile, check=check)

    # Idempotência por nome: reaproveita um cluster homônimo em vez de duplicar.
    listing = _json_body(dbx(["clusters", "list", "-o", "json"], check=False).stdout, [])
    clusters = listing.get("clusters", []) if isinstance(listing, dict) else listing
    existing = next((c for c in clusters if c.get("cluster_name") == name), None)
    if existing:
        cluster_id = existing["cluster_id"]
        typer.secho(f"[=] cluster '{name}' já existe (cluster_id={cluster_id})", fg=typer.colors.YELLOW)
    else:
        # SINGLE_USER precisa do dono nomeado — o próprio usuário autenticado.
        me = _json_body(dbx(["current-user", "me", "-o", "json"]).stdout, {})
        owner = me.get("userName", "")
        spec = {
            "cluster_name": name,
            "spark_version": spark_version,
            "node_type_id": node_type,
            "num_workers": workers,
            "autotermination_minutes": autotermination,
            "data_security_mode": "SINGLE_USER",
            "single_user_name": owner,
            "runtime_engine": "STANDARD",
        }
        created = _json_body(dbx(["clusters", "create", "--no-wait", "--json", json.dumps(spec)]).stdout, {})
        cluster_id = created.get("cluster_id", "")
        typer.secho(f"[+] cluster '{name}' criado (cluster_id={cluster_id}, {node_type}, {workers} worker(s))", fg=typer.colors.GREEN)

    typer.secho(f"\n  cluster_id: {cluster_id}", fg=typer.colors.CYAN, bold=True)
    typer.secho("  Uso interativo/ad-hoc: os jobs dos bundles sobem com job cluster próprio.", fg=typer.colors.BRIGHT_BLACK)


@app.command()
def deploy(
    layer: str = typer.Argument("all", help="essential | layer_bronze | layer_silver | layer_gold | orchestration | all"),
    target: str = typer.Option("prd", "--target", "-t"),
    dry_run: bool = typer.Option(False),
):
    """Publica os Databricks Asset Bundles (ordem: essential→bronze→silver→gold→orchestration)."""
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
    """Valida todos os bundles — essential/bronze/silver/gold/orchestration (CI-friendly)."""
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
    typer.echo("setup-spn : SPN consumidora + segredos (dm setup-spn)")
    typer.echo("bundles   : essential, layer_bronze, layer_silver, layer_gold, orchestration")


if __name__ == "__main__":  # pragma: no cover
    app()
