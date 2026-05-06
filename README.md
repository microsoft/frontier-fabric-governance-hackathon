# Fabric Workspace Governance

PR-based approval workflow for **Microsoft Fabric workspace creation**.

> No workspace exists in this tenant unless a YAML manifest for it lives in `main`,
> was reviewed via Pull Request, and was provisioned by a Service Principal through
> GitHub Actions.

## How to request a workspace

You have three options. All go through the same governance gate
(`.github/workflows/validate.yml` → `scripts/validate.py` against
`rules/policy.yaml`).

### Option A2 — Microsoft Copilot Studio agent (recommended, no Azure compute)

A Copilot Studio agent in [`agent/copilotstudio/`](agent/copilotstudio/) drives
the request through Power Automate cloud flows that talk directly to GitHub
via the GitHub connector — no Azure Function App, no custom OpenAPI plugin.
The single deterministic policy gate is the existing PR check. See the
operator runbook in [`docs/copilot-studio-agent.md`](docs/copilot-studio-agent.md)
and the design notes in
[`agent/copilotstudio/README.md`](agent/copilotstudio/README.md).

### Option A — Microsoft 365 Copilot declarative agent (legacy)

Open Copilot, pick **Fabric Workspace Provisioner**, and answer the agent's
questions. It calls the Azure Functions backend in [`api/`](api/) (deployed via
[`infra/terraform/`](infra/terraform/) or [`infra/bicep/`](infra/bicep/)) which
opens the PR. Setup is documented in [`docs/m365-agent.md`](docs/m365-agent.md).
The declarative agent package lives in [`agent/appPackage/`](agent/appPackage/).
Kept for tenants that prefer the M365 Copilot surface; can be retired in
favour of Option A2 by running `terraform destroy` once Option A2 is proven —
see the "Migration" section in the Copilot Studio README.

### Option B — Open the PR yourself

1. Fork or branch this repo.
2. Create a new manifest at `workspaces/<name>.yaml`. See `workspaces/dev-plt-sample-hello.yaml`.
3. Open a Pull Request.
4. The **validate** workflow checks your manifest against the schema and the rules in `rules/policy.yaml`. Fix any blocking issues.
5. A reviewer from `@frteix_microsoft` (or as defined in `.github/CODEOWNERS`) approves the PR.
6. On merge, the **provision** workflow (gated by the `production` GitHub environment) creates or updates the workspace in Fabric.

## Repo layout

```
.github/
  workflows/
    validate.yml      # PR: schema + policy checks, sticky comment with results
    provision.yml     # main: idempotent create-or-update via Fabric REST
    drift.yml         # nightly: list workspaces, flag drift / unmanaged
  CODEOWNERS
  pull_request_template.md
schemas/workspace.schema.json   # JSON Schema for manifests
rules/policy.yaml               # Declarative rule set (edit to evolve policy)
scripts/
  validate.py
  provision.py
  drift.py
  _fabric.py
  requirements.txt
workspaces/                     # one YAML per workspace
docs/
  workspace-approval-workflow.md   # full design doc
  setup.md                         # one-time operator setup runbook
```

## Tenant configuration (one-time)

See [`docs/setup.md`](docs/setup.md) for the operator runbook (tenant settings,
Fabric admin role, capacity admin, etc).

## Identity

GitHub Actions authenticates to Entra ID via **OIDC federation** — no client secrets.
Federated credentials are configured for:
- `pull_request` events (validate workflow can read tenant for live checks)
- `refs/heads/main` (provision workflow on merge)
- `environment:production` (manual-approval gate)
