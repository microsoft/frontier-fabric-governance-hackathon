# Fabric Workspace Provisioner — Microsoft 365 Declarative Agent

> **Status: legacy.** This option (Option A in the top-level README) requires
> the Azure Functions backend in [`api/`](../api/) and the IaC in
> [`infra/`](../infra/). A simpler, **Function-App-free** alternative now
> lives in [`agent/copilotstudio/`](../agent/copilotstudio/) (Option A2):
> a Copilot Studio agent that uses Power Automate cloud flows + the GitHub
> connector to open the same pull request, with no Azure compute. Keep this
> path if you specifically need the M365 Copilot surface; otherwise prefer
> Option A2 and run `terraform destroy` in `infra/terraform/` once you have
> piloted the Copilot Studio agent.

A Microsoft 365 Copilot **declarative agent** that lets employees request a new
Microsoft Fabric workspace through chat. The agent collects the answers, runs
them through the same MEO governance rule engine that gates the repository,
and opens a pull request in this GitHub repo on the user's behalf.

## Why this design

Three architectural decisions, all locked in:

1. **Declarative agent (manifest v1.6) — not a custom engine agent.**
   - Built-in Microsoft 365 Copilot orchestration, no model hosting.
   - Follows the v1.6 schema: `name`, `description`, `instructions`,
     `conversation_starters`, `actions[]`. See
     [`agent/appPackage/declarativeAgent.json`](../agent/appPackage/declarativeAgent.json).
   - Tool calls are described in an **API plugin manifest v2.4**
     ([`plugin.json`](../agent/appPackage/plugin.json)) which points at an
     OpenAPI 3.0 spec ([`openapi.yaml`](../agent/appPackage/openapi.yaml)).

2. **GitHub App + Azure Functions Python v2 backend — not a SPFx web part
   and not a Power Automate flow.**
   - Stateless, easy to scale, easy to lock down with Managed Identity.
   - GitHub App auth (JWT → installation token) gives auditable,
     least-privilege PR creation. See
     [`api/shared/github_app.py`](../api/shared/github_app.py).
   - The private key lives in **Key Vault**; the Function reads it through
     **User-Assigned Managed Identity** with the `Key Vault Secrets User` role.

3. **Dual-layer validation — agent-side AND backend-side.**
   - The agent calls `POST /validate` while the user is still chatting so
     mistakes are caught early and explained conversationally.
   - The backend re-runs the same checks inside `POST /submit` before opening
     the PR — the agent can never bypass governance.
   - Both call into [`scripts/rules_engine.py`](../scripts/rules_engine.py),
     which is the single source of truth shared with the existing
     [`scripts/validate.py`](../scripts/validate.py) PR check.

## Repository layout

```
frontier-fabric-governance-hackathon/
├── agent/appPackage/             # M365 declarative agent package
│   ├── manifest.json             # Teams app manifest (wraps the agent)
│   ├── declarativeAgent.json     # v1.6 declarative agent manifest
│   ├── instructions.md           # Agent system prompt
│   ├── plugin.json               # v2.4 API plugin manifest
│   ├── openapi.yaml              # OpenAPI 3.0 spec for the backend
│   └── ICONS.md                  # How to add color.png / outline.png
├── api/                          # Azure Functions Python v2 backend
│   ├── function_app.py           # /validate /submit /policy /healthz
│   ├── shared/github_app.py      # GitHub App JWT + PR helpers
│   ├── host.json
│   ├── requirements.txt
│   └── local.settings.sample.json
├── infra/main.bicep              # Function App + Storage + KV + UAMI + RBAC
├── infra/main.parameters.json
├── azure.yaml                    # azd up / azd deploy
├── rules/policy.yaml             # Allow-lists, capacities, quotas
├── schemas/workspace.schema.json # JSON Schema for manifests
├── scripts/
│   ├── rules_engine.py           # Shared rule engine (CLI + Function)
│   ├── validate.py               # PR-check CLI (imports rules_engine)
│   ├── provision.py
│   ├── drift.py
│   └── _fabric.py
└── workspaces/                   # Manifest files PR'd by the agent
    └── pt-nlyt-sample-ndf-dev-hello1.yaml
```

## End-to-end flow

```
Employee chats with Copilot
        │
        ▼
M365 declarative agent (instructions.md)
        │  GET  /policy            ← live approved values
        │  POST /validate          ← pre-flight check while chatting
        │  POST /submit            ← only on user confirmation
        ▼
Azure Functions backend (api/)
        │  validate via rules_engine.py (same code as PR check)
        │  Mint GitHub App JWT (key from Key Vault via UAMI)
        │  Branch + commit workspaces/<name>.yaml + open PR
        ▼
GitHub PR opened in this repo
        │
        ▼
PR validation workflow (.github/workflows + scripts/validate.py)
        │  Re-runs the SAME rule engine on the file in the PR
        ▼
Reviewer approves and merges  →  Workspace gets provisioned downstream
```

## Setting up the GitHub App (one-time)

1. **Create the App.** GitHub → Settings → Developer settings → GitHub Apps → New.
   - Repository permissions: `Contents: Read and write`, `Pull requests: Read and write`, `Metadata: Read-only`.
   - No webhooks needed.
   - Generate and download the **private key** (`.pem`).
2. **Install it on this repo only.**
3. Note the **App ID** and the **Installation ID**
   (`https://github.com/organizations/<org>/settings/installations` →
   *Configure* → URL ends with the installation id).

## Deploying the backend

Prereqs: Azure CLI, [`azd`](https://aka.ms/azd), Python 3.11.

```bash
cd frontier-fabric-governance-hackathon
azd auth login

azd env new fwg-dev
azd env set GITHUB_APP_ID            <app-id>
azd env set GITHUB_INSTALLATION_ID   <installation-id>
azd env set GITHUB_OWNER             <org>
azd env set GITHUB_REPO              frontier-fabric-governance-hackathon

azd up   # provisions infra + deploys api/
```

After the first `azd up`:

```bash
az keyvault secret set \
  --vault-name "$(azd env get-values | grep AZURE_KEY_VAULT_NAME | cut -d= -f2 | tr -d '\"')" \
  --name github-app-private-key \
  --file /path/to/your-app.private-key.pem

# Flip out of dry-run so /submit actually opens PRs
az functionapp config appsettings set \
  --name "$(azd env get-values | grep AZURE_FUNCTION_APP_NAME | cut -d= -f2 | tr -d '\"')" \
  --resource-group "$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d= -f2 | tr -d '\"')" \
  --settings DRY_RUN=false
```

Sanity check:

```bash
HOST=$(azd env get-values | grep AZURE_FUNCTION_APP_HOSTNAME | cut -d= -f2 | tr -d '"')
curl https://$HOST/api/healthz
curl https://$HOST/api/policy
```

## Packaging the M365 agent

1. Drop `color.png` (192×192) and `outline.png` (32×32) into `agent/appPackage/`
   (see [`ICONS.md`](../agent/appPackage/ICONS.md)).
2. Edit `agent/appPackage/openapi.yaml` and replace the `servers[0].url` with
   `https://<your-function-host>/api`.
3. Edit `agent/appPackage/manifest.json` and replace the `id` with a new GUID
   (`uuidgen`).
4. Zip the `appPackage/` folder contents (not the folder itself):
   ```bash
   cd agent/appPackage
   zip ../fabric-workspace-provisioner.zip ./*
   ```
5. Upload the zip in **Microsoft 365 Admin Center → Integrated apps → Upload
   custom apps**, or sideload via the Teams Toolkit for VS Code while testing.

## Running the backend locally

```bash
cd api
cp local.settings.sample.json local.settings.json   # set DRY_RUN=true while developing
pip install -r requirements.txt
func start
```

`DRY_RUN=true` makes `/submit` skip the GitHub call and report the PR it
*would* have opened — useful for testing the agent against a local tunnel
without touching the repo.

## Verifying that the agent and the PR check stay in sync

Both call `apply_rules()` and `validate_schema()` from
[`scripts/rules_engine.py`](../scripts/rules_engine.py). The `azure.yaml`
prepackage hook copies `rules_engine.py`, `workspace.schema.json` and
`policy.yaml` into the Function deployment package, so the Function and the
CLI run **byte-identical** rule code. To prove it after a change:

```bash
python scripts/validate.py                     # PR-check CLI
curl -X POST https://$HOST/api/validate \      # M365 agent backend
  -H 'content-type: application/json' \
  --data @workspaces/pt-nlyt-sample-ndf-dev-hello1.yaml
```

The `findings` list must be identical for the same input.

## Updating governance rules

Change `rules/policy.yaml` or `schemas/workspace.schema.json` in a PR. The PR
check enforces the new rules immediately. Run `azd deploy api` to ship the
same rules to the M365 agent backend. There is no separate rule store.
