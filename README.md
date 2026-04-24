# Fabric Workspace Governance

PR-based approval workflow for **Microsoft Fabric workspace creation**.

> No workspace exists in this tenant unless a YAML manifest for it lives in `main`,
> was reviewed via Pull Request, and was provisioned by a Service Principal through
> GitHub Actions.

## How to request a workspace

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
