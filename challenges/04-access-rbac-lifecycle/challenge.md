# Challenge 04 — Access & RBAC lifecycle

> **Outcome:** every Fabric workspace role assignment is declared in `access/`,
> Group-first, has an `expiresOn`, and is reviewed quarterly. Stale or risky
> bindings open automatic remediation PRs.

## Why this challenge exists

The default failure mode of every data platform is *role sprawl*: contractors
added directly to a workspace, never removed; user accounts as sole admins;
"temporary" elevation that becomes permanent. Move RBAC into version control with
explicit expiry, and the failure mode flips to obvious.

## Learning objectives

1. Model workspace role assignments as code with expiry.
2. Enforce "Group preferred, User by exception" in validation.
3. Automate quarterly access reviews via PR opened by a scheduled workflow.
4. Build a JIT "break-glass" PR template that auto-expires.
5. Query workspace roles from chat via the Fabric Core MCP.

## Prerequisites

- Challenges 00–01 complete.
- (Recommended) Microsoft Graph MCP installed so the agent can resolve UPNs to
  object IDs for you.

## Tasks

### Task 1 — Access manifest schema

Add `schemas/access.schema.json` and example manifests under `access/`:

```yaml
# access/dev-plt-myteam-playground.yaml
workspace: dev-plt-myteam-playground
bindings:
  - principalType: Group
    identifier: <objectId>
    displayName: sg-plt-myteam
    role: Admin
    expiresOn: null              # null allowed for Group bindings only
  - principalType: User
    identifier: alice@contoso.com
    role: Member
    expiresOn: 2026-08-31         # max 90 days from createdOn
    justification: "Migration project, ends 2026-08-31"
```

### Task 2 — Validation rules

Extend `scripts/validate.py`:

- `access-min-two-admins`: each workspace must have ≥ 2 Admins.
- `access-group-preferred`: warn on every `User` admin.
- `access-user-must-expire`: block any `User` binding without `expiresOn`.
- `access-expiry-within-90-days`: block any `expiresOn` > 90 days out for `User`.
- `access-justification-for-users`: block any `User` binding without
  `justification` ≥ 30 chars.
- `prd-no-user-admins`: in `prd-*` workspaces, *block* `User` Admins entirely.

### Task 3 — Provisioner reconciliation

Extend `scripts/provision.py` to reconcile access **declaratively**:

1. For each `access/<workspace>.yaml`, fetch the live role assignments.
2. Compute additions / updates / removals against the manifest.
3. Apply additions and updates. **Remove only with a confirmation field in the
   manifest** (`allowRemovals: true`) — drifting users should land in a drift
   issue first, not be silently kicked out.

### Task 4 — Quarterly access review

Add `.github/workflows/access-review.yml`:

- Schedule: cron `0 9 1 */3 *` (09:00 UTC, first day of every quarter).
- For each `access/*.yaml`, list bindings whose `expiresOn` falls in the next 30
  days. Open one PR per workspace that proposes:
  - removing the expired bindings, **or**
  - extending their `expiresOn` (requires justification update).

Assign the PR to the workspace's CODEOWNERS.

### Task 5 — JIT break-glass

Add `.github/PULL_REQUEST_TEMPLATE/jit-break-glass.md` and a workflow
`access-jit.yml` that:

1. Watches for PRs with the `break-glass` label.
2. Sets `expiresOn` to `now + 24h` on every `User` binding added in the PR.
3. After merge, schedules a follow-up PR (via `workflow_dispatch`) that removes
   the binding at expiry.

Document the audit trail: each break-glass binding leaves a paper trail
(PR + provisioning run + automatic remediation PR).

### Task 6 — Verify via Fabric Core MCP

From chat:

```
Which workspaces does alice@contoso.com have any role on?
List all User principals with Admin on prd-* workspaces.
Show role assignments for "<workspace>" — group by role.
```

Compare the answer with the contents of `access/`. They should match.

## Success criteria

- [ ] Every workspace under management has a corresponding `access/<name>.yaml`.
- [ ] A PR adding a `User` Admin to a `prd-*` workspace is blocked.
- [ ] The quarterly review workflow opens a PR with at least one expiring binding
      when you fast-forward `expiresOn`.
- [ ] A `break-glass`-labelled PR results in an automatic expiry follow-up.

## Stretch goals

- **Per-item access.** Extend the model to item-level permissions (e.g. semantic
  model build / read). Carry expiry semantics down.
- **Time-bound elevation.** Replace break-glass with PIM-style activation: a PR
  that sets `expiresOn=now+1h` and pins which `User` principal can claim it.
- **Slack/Teams notification.** When an expiry PR auto-opens, post to a channel
  with a link.

## MCP tips

- Pair Core MCP with **Microsoft Graph MCP**. Then prompts like *"Add
  alice@contoso.com as Member to workspace X expiring 2026-08-31"* resolve UPN
  to objectId without you fetching it manually.

## Skills tips

- No workload-specific skill is required here. You can use `activator-authoring-cli`
  to fire a Reflex when expiry < 7 days (notify the owner) as a stretch enhancement.

## References

- [Fabric workspace role assignments REST API](https://learn.microsoft.com/rest/api/fabric/core/workspaces/add-workspace-role-assignment)
- [Microsoft Graph MCP](https://learn.microsoft.com/graph/mcp-server/get-started)
- [Privileged Identity Management](https://learn.microsoft.com/azure/active-directory/privileged-identity-management/pim-configure)
