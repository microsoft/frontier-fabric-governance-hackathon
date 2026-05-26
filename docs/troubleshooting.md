# Troubleshooting

Shared error catalog. Each challenge can link here instead of duplicating
content. If you hit something that isn't listed, open a PR adding it.

## MCP / Skills

### "401 Unauthorized" calling Fabric Core MCP

Cause: cached OAuth token expired, or you signed in with an account that
doesn't have access to the tenant.

Fix:

1. **MCP: Remove Server** → `fabric`
2. **MCP: Add Server** → `https://api.fabric.microsoft.com/v1/mcp/core`
3. Complete the browser sign-in with the right account.

### "Invalid workspace ID" from an MCP tool

Cause: you passed a display name where a GUID was expected.

Fix: run `list_workspaces` first and use the returned `id`.

### Skill says "tool not available"

Cause: the Skill expects an MCP server that isn't installed, or you're using a
chat host that doesn't surface the Skill.

Fix: confirm both Fabric Core MCP and Fabric local MCP are installed; verify
the Skill is installed via your agent's `skill list` command.

## OIDC / Azure login

### `AADSTS70021` (no matching federated identity record)

Cause: the federated credential subject in Entra does not match the GitHub
claim exactly. Typical typo: `environment:Production` vs. `environment:production`.

Fix: open Entra → App → Certificates & secrets → Federated credentials, and
make the subject **exactly** match `repo:<org>/<repo>:environment:<env-name>`
(case-sensitive).

### `azure/login@v2` succeeds but Fabric returns 403

Cause: token was issued, but the SPN is not in the tenant setting allow-list,
*or* the tenant setting hasn't propagated yet (up to 15 minutes), *or* the SPN
isn't Capacity Admin on the target capacity.

Fix: check each of the prereqs in [`docs/setup.md`](setup.md) and
[`docs/identity-model.md`](identity-model.md). Wait 15 minutes after the last
tenant setting change.

## Fabric REST

### `429 Too Many Requests`

Cause: Fabric and Power BI APIs throttle aggressively per-tenant.

Fix: every call in `scripts/_fabric.py` already retries on `429`/`5xx` with
exponential backoff honoring `Retry-After`. If you're adding new calls,
wrap them in the same helper.

### `409 Conflict` on `POST /workspaces`

Cause: workspace name collision (tenant-wide, case-insensitive) — possibly a
race between two simultaneous PRs.

Fix: the provisioner re-queries by name and either adopts (if the marker
matches) or surfaces a clear error. Resolve by renaming the manifest.

### `assignToCapacity` succeeds but `capacityId` doesn't change

Cause: `assignToCapacity` is asynchronous. Don't assume the next call will
see the new state.

Fix: poll `GET /workspaces/{id}` until `capacityId` matches the desired value
before continuing.

### Sensitivity label apply returns 403

Cause: SPN is not in the publishing scope of the label in Microsoft Purview.

Fix: Purview → Information Protection → Labels → for each label used in
`rules/policy.yaml`, add `sg-fabric-workspace-provisioner` to the publishing scope.

## GitHub

### `validate` workflow doesn't run on a PR

Cause: the workflow's `paths:` filter excluded all your changes (e.g. you only
edited `README.md`).

Fix: not a bug. If you want to test the workflow itself, edit any file under
`workspaces/`, `rules/`, `schemas/`, or `scripts/`.

### CODEOWNERS approval not required

Cause: branch protection is off, or the CODEOWNERS file is malformed (a
single bad line silently disables the whole file).

Fix: GitHub → Settings → Branches → confirm "Require review from Code Owners"
on `main`. Run `gh api repos/:owner/:repo/codeowners/errors` to find malformed lines.

### "Refusing to allow a Personal Access Token to create or update workflow"

Cause: a PAT without the `workflow` scope tried to modify `.github/workflows/`.

Fix: use a fine-grained token with the `workflow` permission, or push via
`gh auth login` with the GitHub CLI which handles scopes for you.

## Python / scripts

### `ModuleNotFoundError: No module named 'jsonschema'`

Cause: the runner started a fresh interpreter without the project venv.

Fix:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
```

The workflows already do this; if you're running locally, repeat the steps.

### `validate.py` reports a Python-side rule error you can't reproduce

Cause: live-tenant checks rely on an Azure login. The CI workflow runs
`azure/login@v2` with `continue-on-error: true` so that local runs don't fail
without credentials.

Fix: set `LIVE_CHECKS=false` for offline development:

```bash
LIVE_CHECKS=false python scripts/validate.py
```
