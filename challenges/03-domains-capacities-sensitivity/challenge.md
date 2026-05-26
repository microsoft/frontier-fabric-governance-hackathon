# Challenge 03 — Domains, capacities, and sensitivity

> **Outcome:** every workspace lands in the right Fabric **domain**, on the right
> **capacity**, with the right **sensitivity label** — and the only way to change
> any of those is a PR.

## Why this challenge exists

Domain, capacity, and label aren't just descriptive metadata. They control who can
discover a workspace in the OneLake catalog, who pays for it, what compute it
gets, and how Purview policies enforce data movement. Out-of-band changes to any
of them silently break audit and chargeback. Drive them from manifests too.

## Learning objectives

1. Model Fabric **domains** and **capacities** as code (`domains/*.yaml`,
   `capacities/*.yaml`).
2. Enforce per-environment capacity allow-lists and region matches.
3. Apply sensitivity labels at provision time and detect label drift nightly.
4. Implement a "label promotion" review flow that requires extra CODEOWNERS approval.
5. Use the Fabric Core MCP to interrogate domain/capacity/label state from chat.

## Prerequisites

- Challenges 00–01 complete.
- The SPN is a member of the Microsoft Purview publishing scope for every label
  listed in `rules/policy.yaml`'s `approvedSensitivityLabels`.
- The SPN is **Fabric Administrator** (required for domain admin APIs).

## Tasks

### Task 1 — Domains as code

Author one manifest per domain under `domains/`:

```yaml
# domains/finance.yaml
name: Finance
description: "Workspaces, lakehouses, and reports owned by the Finance org."
contributors:
  - principalType: Group
    identifier: <objectId-of-finance-admins>
parentDomain: null
subdomains:
  - name: FinanceReporting
    description: "Reporting marts and Power BI assets."
```

Add `schemas/domain.schema.json` and a `domains:` section to `rules/policy.yaml`
that enforces:

- domain name in `approvedDomains` (existing rule), or
- new manifest must also include a justification (`businessJustification` ≥ 60 chars).

### Task 2 — Capacities as code

Author one manifest per capacity under `capacities/`:

```yaml
# capacities/frteix-f2-northeurope.yaml
logicalName: frteix-f2-northeurope
capacityId: <guid>
region: northeurope
sku: F2
allowedEnvironments: [dev, sbx, stg]
admins:
  - principalType: Group
    identifier: <objectId-of-capacity-admins>
```

Replace the `approvedCapacities:` block in `rules/policy.yaml` with a thin loader
that reads `capacities/*.yaml`. Now adding a capacity is a PR, not a policy edit.

### Task 3 — Enforce capacity + region + environment matches

Extend `scripts/validate.py` so workspace manifests fail validation when:

- `capacity` doesn't reference a manifest in `capacities/`.
- `region` ≠ the capacity's `region`.
- `environment` ∉ the capacity's `allowedEnvironments`.

### Task 4 — Apply domain at provision time

Extend `scripts/provision.py` to call the Fabric admin API to assign each
provisioned workspace to its declared `domain`:

```
POST https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/assignWorkspaces
{ "workspacesIds": ["<wsId>"] }
```

Resolve `domainId` from the domain manifest. If the workspace's `domain` field is
empty, leave domain assignment alone (don't unassign).

### Task 5 — Apply sensitivity labels at provision time

For each workspace, after creation and capacity assignment, set its sensitivity
label using the Power BI admin API:

```
POST https://api.powerbi.com/v1.0/myorg/admin/workspaces/{id}/sensitivityLabel
```

Add the label name → label ID lookup to `rules/policy.yaml` (or fetch dynamically
from Purview). Document any MIP permission issues in `docs/troubleshooting.md`.

### Task 6 — Extend drift detection

In `scripts/drift.py`, additionally compare:

- workspace ↔ domain assignment
- workspace ↔ capacity assignment (already partially there)
- workspace ↔ sensitivity label

For each mismatch, raise a `drift/configuration` issue with the field diff.

### Task 7 — Label promotion flow

A move from `General` → `Confidential` (or higher) for an existing workspace must
require an additional CODEOWNERS review. Implement by:

1. Adding `/workspaces/*.yaml` `@org/security` to CODEOWNERS for paths whose
   sensitivity is being raised. (Simplest: require security on all
   `workspaces/prd-*.yaml`.)
2. Adding a validation rule that posts a warning if a PR changes `sensitivityLabel`
   in a direction that increases risk.

## Success criteria

- [ ] A workspace's domain, capacity, and label are all set automatically after PR
      merge, with no manual portal clicks.
- [ ] A PR that puts a `prd-*` workspace on a `dev`-only capacity fails validation.
- [ ] Detection works: removing the label via the portal causes the next drift run
      to open an issue.

## Stretch goals

- **Subdomain support.** Add `subdomain` to the workspace manifest; resolve to the
  correct subdomain ID at provision time.
- **Capacity scale governance.** Add `desiredSku` to capacity manifests and
  reconcile via ARM (`Microsoft.Fabric/capacities`). Treat upscale > F8 as
  CODEOWNERS-gated.
- **Purview-side enforcement.** Add a Purview DLP policy that blocks export of
  `Confidential` data to non-managed workspaces; show that workflows still pass.

## MCP tips

- `list_capacities` from Core MCP returns SKU and region per capacity. Use it from
  chat to draft your `capacities/*.yaml` quickly.
- The catalog `search_catalog` tool lets you spot-check that a workspace surfaces
  in the right domain after provisioning.

## Skills tips

- No workload-specific skill is strictly required for this challenge, but
  `powerbi-authoring-cli` can build a "Governance Health" Power BI report that
  visualizes label coverage and domain assignment counts.

## References

- [Fabric domains REST API](https://learn.microsoft.com/rest/api/fabric/admin/domains)
- [Power BI sensitivity labels admin API](https://learn.microsoft.com/rest/api/power-bi/admin/workspaces-set-workspaces-sensitivity-label)
- [Microsoft Purview MIP scope](https://learn.microsoft.com/purview/sensitivity-labels)
