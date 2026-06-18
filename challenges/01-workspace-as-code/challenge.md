# Challenge 01 — Workspace as code

> **Outcome:** you can create, update, and decommission Fabric workspaces by opening
> Pull Requests against YAML manifests. The tenant has zero workspaces that aren't in
> `main`.

## Why this challenge exists

Workspaces are the unit of access control, capacity assignment, and domain placement
in Fabric. If you can't govern who creates workspaces and how, every other
governance control downstream is on quicksand.

This challenge teaches the **core loop** every later challenge reuses:

```
PR → schema check → policy check → CODEOWNERS approval →
merge → environment approval → OIDC token → Fabric REST → marker written →
nightly drift reconciliation
```

## Learning objectives

By the end of this challenge you will be able to:

1. Author a workspace manifest that conforms to `schemas/workspace.schema.json`.
2. Read the validation feedback posted as a sticky PR comment and fix issues.
3. Trace a successful provision through GitHub Actions, Entra OIDC, and Fabric REST.
4. Use the Fabric Core MCP Server from chat to **verify** that the live tenant
   matches your manifest.
5. Detect and remediate drift introduced out-of-band.

## Prerequisites

- All of Challenge 00 complete.
- You can run `python scripts/validate.py` locally without auth errors
  (`LIVE_CHECKS=false` is fine for local).

## Tasks

### Task 1 — Reproduce the sample manifest

`workspaces/pt-nlyt-sample-ndf-dev-hello1.yaml` already exists. Read it. Then open a PR
that adds **a second** manifest, e.g. `workspaces/dev-plt-myteam-playground.yaml`,
following the same shape.

Watch the `validate` workflow run. The sticky PR comment summarises every rule from
`rules/policy.yaml` with ✅ / ⚠️ / ❌. Fix any blocking issues.

### Task 2 — Get a deliberate policy failure and fix it

Try one of these and confirm `validate` blocks the PR:

- A name that doesn't match `^(prd|stg|dev|sbx)-[a-z0-9]{2,6}-[a-z0-9-]{3,40}$`.
- A `costCenter` that isn't in `rules/policy.yaml`'s `approvedCostCenters`.
- A single owner (the rule requires ≥ 2).
- `environment: prd` with sensitivity `General` (prod requires Confidential+).

Then fix the manifest and confirm the PR turns green.

### Task 3 — Merge and provision

1. Get the PR reviewed by a CODEOWNERS-listed teammate.
2. Merge. The `provision` workflow starts and pauses at the **`production`**
   environment gate.
3. Approve the environment. Provisioning runs; check the run logs to see:
   - `azure/login@v2` exchanging the OIDC token,
   - `POST /workspaces` returning the new workspace ID,
   - `assignToCapacity` posting,
   - role assignments reconciled,
   - description ending in `managed-by:gh:<org>/<repo>@<sha>`.

### Task 4 — Verify via the Fabric Core MCP

In VS Code chat, ask:

```
Get the workspace called "<your-new-workspace-name>" and show me its description.
List the role assignments for that workspace.
```

The description should end with the `managed-by:` marker. The role assignments
should match your manifest's `owners` array.

### Task 5 — Detect drift

In the Fabric portal, manually change something about the workspace (e.g., remove
an admin or change the description). Trigger `drift.yml` from the Actions tab
(`workflow_dispatch`).

Confirm an issue is opened tagged `drift/configuration` with a diff body.

Open a PR that either reverts the live change or updates the manifest to match
the new desired state. Merge → re-run drift → confirm the issue closes (or stays
closed because there's no longer drift).

### Task 6 — Decommission

Open a PR that removes a manifest. Decide as a team what removal means:

- Option A (default): keep the workspace in the tenant, but stop managing it.
  Manifest deletion only removes governance, not the workspace.
- Option B: extend the provisioner to delete the workspace on manifest removal.
  This is *destructive*; only do it if your team controls the data.

Document the chosen behavior in `docs/`.

## Success criteria

- [ ] One workspace you created via PR exists in the tenant and shows the
      `managed-by:` marker.
- [ ] You can reproduce a blocking policy failure on demand.
- [ ] You can detect injected drift via `drift.yml`.
- [ ] You can describe what the SPN does on `validate` vs. `provision` vs. `drift`.

## Stretch goals

- **New blocking rule.** Add a rule to `rules/policy.yaml` (e.g., prd workspaces
  must reference a cost center starting `CC-9`). Implement it in `scripts/validate.py`,
  prove it fails then passes with a PR.
- **Adoption.** Pick an existing tenant workspace (created outside the repo) and
  write an `adopt.py` that adds the manifest + writes the marker without
  re-creating the workspace.
- **PR template tweaks.** Customize `.github/pull_request_template.md` to ask the
  requester for the business justification, expected lifespan, and data
  classification.

## MCP tips

- `list_workspaces` returns paginated results; for tenants with many workspaces,
  ask the agent to filter by display name prefix.
- The agent will happily call `delete_workspace` if you ask it to. **Do not** rely
  on chat to manage prod — that's what the workflow + environment gate is for.

## Skills tips

- Skills aren't required for this challenge, but Challenge 02 builds straight on
  this scaffolding. If you have spare time, install `spark-authoring-cli` now and
  ask it for a Notebook template — you'll need it next.

## What you're using under the hood

This challenge maps to these files in the repo root:

- `schemas/workspace.schema.json`
- `rules/policy.yaml`
- `scripts/validate.py`, `scripts/provision.py`, `scripts/drift.py`, `scripts/_fabric.py`
- `workspaces/pt-nlyt-sample-ndf-dev-hello1.yaml`
- `.github/workflows/validate.yml`, `provision.yml`, `drift.yml`
- `.github/CODEOWNERS`, `.github/pull_request_template.md`

The full design walkthrough lives in
[`docs/workspace-approval-workflow.md`](../../docs/workspace-approval-workflow.md).

## References

- [`docs/workspace-approval-workflow.md`](../../docs/workspace-approval-workflow.md)
- [`docs/setup.md`](../../docs/setup.md)
- [`docs/identity-model.md`](../../docs/identity-model.md)
- [Fabric REST API — workspaces](https://learn.microsoft.com/rest/api/fabric/core/workspaces)
