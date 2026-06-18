# Fabric Workspace Governance Agent — Deployment Handoff

**Date deployed:** 2026-05-06
**Subscription:** `MCAPS-Hybrid-REQ-134416-2025-frteix` (`4673f58d-c87c-40ea-a2cc-aae692d16d6f`)
**Tenant:** `16b3c013-d300-468d-ac64-7eda0820b6d3`
**Resource group:** `rg-fwg-dev` (region `northeurope`)

## What is live in Azure

| Resource | Name | Notes |
| --- | --- | --- |
| Function App (Flex Consumption FC1) | `fwg-func-rynra7bb2ogjk` | Python 3.11, v2 model, 4 HTTP triggers registered |
| User-assigned managed identity | `fwg-id-rynra7bb2ogjk` | Client id `4d8db7bd-20fc-44e1-a52c-05b59f7e5672` |
| Key Vault (RBAC, soft-delete 7d) | `fwg-kv-rynra7bb2ogjk` | URL `https://fwg-kv-rynra7bb2ogjk.vault.azure.net/` |
| Storage account | `fwgstrynra7bb2ogjk` | Blob container `app-package` holds the Function deployment zip |
| Application Insights / LAWS | `fwg-appi-rynra7bb2ogjk` / `fwg-laws-rynra7bb2ogjk` | Workspace-based |

The Function App authenticates to Storage and Key Vault via the user-assigned identity — there are no connection strings in app settings.

## Live API endpoints

Base URL: `https://fwg-func-rynra7bb2ogjk.azurewebsites.net/api`

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/healthz` | Anonymous | Liveness probe (returns `{"status":"ok"}`) |
| GET | `/policy` | Anonymous | Allowed countries/areas/subjects/domains/labels/cost centres/capacities — drives the agent's choice prompts |
| POST | `/validate` | Anonymous | Schema + MEO rule check; returns blocking + warning findings |
| POST | `/submit` | Anonymous | Validate, then open a governance PR on GitHub (currently `DRY_RUN=true`, so it returns a synthetic PR URL without calling GitHub) |

Smoke tests confirmed:

- `/healthz` → `{"status":"ok"}` (≈1.9 s)
- `/policy` → real allow-lists from `rules/policy.yaml`
- `/validate` with a valid manifest → `passed:true` (when all required fields supplied)
- `/validate` with a malformed manifest → 13 schema findings including the regex-failure for `BAD-NAME`

The validation endpoint runs the **same** `rules_engine.py` that gates the GitHub PR check, so there is no possibility of drift between what the agent tells the user and what the merge gate enforces.

## M365 declarative agent package

Built at `dist/fabric-workspace-provisioner.zip` (≈9 KB). Contents:

```
manifest.json           Teams app manifest v1.19, app id b2725383-3f2a-449c-ae3a-34e41319c454
declarativeAgent.json   Agent v1.6 spec (instructions + plugin reference)
instructions.md         System prompt for the agent
plugin.json             API plugin v2.4 (auth.type = None)
openapi.yaml            OpenAPI 3.0 — server URL points to the live Function App
color.png               192×192 brand icon
outline.png             32×32 outline icon
```

## Remaining manual steps

The agent works end-to-end **today** in dry-run mode (it will validate input and return a fake PR URL). To enable real PR creation, complete the following:

### 1. Create the GitHub App

1. In GitHub → **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Permissions (repository): **Contents: Read & write**, **Pull requests: Read & write**, **Metadata: Read**.
3. Webhook: not required (uncheck "Active").
4. Generate a private key (PEM). Note the **App ID**.
5. Install the app on your repo. Note the **Installation ID** (visible in the URL when viewing the install).

### 2. Upload the PEM to Key Vault

```bash
az keyvault secret set \
  --vault-name fwg-kv-rynra7bb2ogjk \
  --name github-app-private-key \
  --file /path/to/your-app.private-key.pem
```

The Function reads the secret name from app setting `GITHUB_PRIVATE_KEY_SECRET` (default `github-app-private-key`).

### 3. Wire the IDs and flip DRY_RUN

```bash
az functionapp config appsettings set \
  -g rg-fwg-dev -n fwg-func-rynra7bb2ogjk \
  --settings \
    GITHUB_APP_ID=<your-app-id> \
    GITHUB_INSTALLATION_ID=<your-installation-id> \
    GITHUB_OWNER=<github-org-or-user> \
    GITHUB_REPO=<repo-name> \
    GITHUB_BASE_BRANCH=main \
    DRY_RUN=false
```

The Function will pick up the new settings within ~30 seconds; no restart needed.

### 4. Sideload the Teams app

In Teams Admin Center (or Microsoft 365 Admin) → **Teams apps → Manage apps → Upload new app**, upload `dist/fabric-workspace-provisioner.zip`. Once approved by your tenant admin, end users find the agent under **Apps → Built for your org**.

For dev/test you can also "Upload custom app" directly inside Teams → Apps → Manage your apps.

### 5. Optional: harden auth on the Function

Today the four routes are anonymous because the agent's plugin uses `auth.type=None`. To require Entra ID:

1. Enable **Easy Auth** (App Service Authentication) on the Function App, configured for Entra ID.
2. Change `plugin.json` to use `OAuthPluginVault` with the application's client id + client secret stored in Key Vault.
3. Re-pack and re-sideload the Teams app.

## How the rule engine stays in sync

Both the GitHub PR check (`scripts/validate.py`) and the live `/validate` endpoint import the **same** `rules_engine.py`. The deploy pipeline mirrors the canonical files into `api/` so the Function package is self-contained:

- `scripts/rules_engine.py` → `api/rules_engine.py`
- `schemas/workspace.schema.json` → `api/workspace.schema.json`
- `rules/policy.yaml` → `api/policy.yaml`

Mirroring is done by the `services.api.hooks.prepackage` hook in `azure.yaml`. The mirrored files are also committed to `api/` as a belt-and-braces measure (some azd flows skip prepackage hooks). When you change `policy.yaml` or `workspace.schema.json` at the canonical location, just run `azd deploy` — the hook re-syncs the copies before packaging.

## Useful diagnostic commands

```bash
# Tail recent traces in App Insights
APPID=$(az monitor app-insights component show -g rg-fwg-dev -a fwg-appi-rynra7bb2ogjk --query appId -o tsv)
az monitor app-insights query --app $APPID --analytics-query \
  "union traces, exceptions | where timestamp > ago(15m) | order by timestamp desc | take 50"

# List registered functions (host master key)
KEY=$(az functionapp keys list -g rg-fwg-dev -n fwg-func-rynra7bb2ogjk --query masterKey -o tsv)
curl -sS -H "x-functions-key: $KEY" https://fwg-func-rynra7bb2ogjk.azurewebsites.net/admin/functions

# Inspect deployed package
az storage blob list --account-name fwgstrynra7bb2ogjk --container-name app-package \
  --auth-mode login -o table
```

## Files of interest

- [api/function_app.py](../api/function_app.py) — HTTP backend
- [api/shared/github_app.py](../api/shared/github_app.py) — GitHub App auth + PR creation
- [agent/appPackage/manifest.json](../agent/appPackage/manifest.json) — Teams manifest
- [agent/appPackage/openapi.yaml](../agent/appPackage/openapi.yaml) — API contract for the plugin
- [agent/appPackage/instructions.md](../agent/appPackage/instructions.md) — agent system prompt
- [infra/bicep/main.bicep](../infra/bicep/main.bicep) — full IaC
- [azure.yaml](../azure.yaml) — azd service + prepackage hook config
