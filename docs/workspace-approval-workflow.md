# Microsoft Fabric — PR-Based Workspace Creation Approval Workflow

> **Status:** Reference design • **Audience:** Platform / Governance / Data Engineering teams
> **Goal:** Treat Fabric workspaces as **declarative infrastructure**. No workspace exists in the tenant unless a YAML manifest for it exists in `main` of this repo, was reviewed via PR, and was provisioned by a service principal through GitHub Actions.

---

## 1. Architecture Overview

### 1.1 End-to-end flow

```
┌──────────┐   1. open PR         ┌─────────────────┐
│Requester │ ───────────────────► │  Git repo (main)│
└──────────┘  workspaces/foo.yaml └────────┬────────┘
                                           │
                                  2. PR triggers
                                  ┌────────▼────────┐
                                  │ validate.yml CI │  schema + rules/policy.yaml
                                  │  → sticky PR    │  posts pass/fail per rule
                                  │    comment      │
                                  └────────┬────────┘
                                           │ green checks
                                  3. CODEOWNERS review
                                  ┌────────▼────────┐
                                  │ Reviewers:      │
                                  │  @platform      │
                                  │  @governance    │
                                  │  @security (prd)│
                                  └────────┬────────┘
                                           │ approved + merged
                                  4. push to main
                                  ┌────────▼────────┐
                                  │ provision.yml CD│  GitHub Environment: "fabric-prod"
                                  │  OIDC → Entra   │  (manual approval gate)
                                  │  → Fabric REST  │
                                  └────────┬────────┘
                                           │
        ┌──────────────────────────────────┼──────────────────────────────────┐
        ▼                ▼                 ▼                ▼                  ▼
  Create workspace  Assign capacity   Role assignments  Assign domain    Sensitivity label
  (POST /workspaces)(assignToCapacity)(roleAssignments) (admin PATCH)    (admin API)
        │                │                 │                │                  │
        └────────────────┴─────────────────┴────────────────┴──────────────────┘
                                           │
                                  5. write tag/marker
                                  in workspace description:
                                  `managed-by: gh:org/repo#<sha>`
                                           │
                                  6. PR closed, audit log entry
```

### 1.2 Tenant-setting prerequisites

Configured in **Fabric Admin Portal → Tenant settings**:

| Setting | Value | Scope |
|---|---|---|
| **Create Fabric items** | Enabled for specific security group | `sg-fabric-provisioner` only |
| **Create workspaces** | Enabled for specific security group | `sg-fabric-provisioner` only |
| **Service principals can use Fabric APIs** | Enabled | `sg-fabric-provisioner` |
| **Service principals can call admin APIs (read-only)** | Enabled | `sg-fabric-provisioner` |
| **Service principals can update/delete via admin APIs** | Enabled | `sg-fabric-provisioner` |
| **Allow service principals to create and use profiles** | Enabled | `sg-fabric-provisioner` |
| **Block users from creating workspaces in My workspace** | Enabled | All users (optional but recommended) |

> ⚠️ Tenant setting changes take **up to 15 minutes** to propagate. Validate before kicking off the first provisioning run.

### 1.3 Identity model

- **Entra ID app registration:** `app-fabric-provisioner`
  - Member of security group `sg-fabric-provisioner`
  - Granted **Fabric Administrator** role (required for domain assignment & admin APIs)
- **Federated credentials (OIDC)** — no client secrets:
  - Issuer: `https://token.actions.githubusercontent.com`
  - Subject (per environment):
    - `repo:org/fabric-governance:environment:fabric-nonprod`
    - `repo:org/fabric-governance:environment:fabric-prod`
  - Audience: `api://AzureADTokenExchange`
- **API permissions** (delegated/application as required):
  - `https://api.fabric.microsoft.com/.default` (application token)
  - Power BI Service: `Tenant.ReadWrite.All` (for admin API surface still under PBI)
- **Capacity admin:** `app-fabric-provisioner` added as **Capacity Admin** on every Fabric capacity it should be able to assign workspaces to.
- **MIP / Sensitivity labels:** SPN must be granted permission to apply labels (Purview → Information Protection → label scope includes the SPN's group).

---

## 2. Repository Layout

```
fabric-governance/
├── README.md
├── docs/
│   └── workspace-approval-workflow.md     ← this document
├── workspaces/
│   ├── prd-fin-revenue-reporting.yaml
│   ├── dev-mkt-experiments.yaml
│   └── stg-ops-telemetry.yaml
├── schemas/
│   └── workspace.schema.json
├── rules/
│   ├── policy.yaml                        ← declarative rule set
│   └── allowlists/
│       ├── capacities.yaml
│       ├── domains.yaml
│       ├── sensitivity-labels.yaml
│       └── cost-centers.yaml
├── scripts/
│   ├── validate.py                        ← schema + rules engine
│   ├── provision.py                       ← idempotent provisioner
│   ├── audit_drift.py                     ← nightly drift detector
│   └── lib/
│       ├── fabric_client.py
│       └── entra_client.py
├── .github/
│   ├── CODEOWNERS
│   └── workflows/
│       ├── validate.yml
│       ├── provision.yml
│       └── audit-drift.yml
└── .gitignore
```

---

## 3. Starter Rule Set

`rules/policy.yaml` — rules are data, not code, so governance can evolve via PR.

```yaml
version: 1
rules:
  - id: naming-convention
    severity: block
    description: Workspace name must match <env>-<bu>-<purpose>
    check:
      type: regex
      field: name
      pattern: '^(prd|stg|dev|sbx)-[a-z0-9]{2,6}-[a-z0-9-]{3,40}$'

  - id: required-capacity
    severity: block
    description: Capacity must be on the per-environment allow-list
    check:
      type: allowlist
      field: capacity.id
      source: rules/allowlists/capacities.yaml
      partition_by: environment

  - id: required-owners
    severity: block
    description: At least 2 owners; must be Entra security groups (no users)
    check:
      type: composite
      all:
        - { type: min_length, field: roleAssignments.admins, value: 2 }
        - { type: foreach, field: roleAssignments.admins,
            rule: { type: principal_kind, equals: Group } }
        - { type: foreach, field: roleAssignments.admins,
            rule: { type: entra_group_exists } }

  - id: domain-assignment
    severity: block
    description: Workspace must be assigned to an approved Fabric domain
    check:
      type: allowlist
      field: domain
      source: rules/allowlists/domains.yaml

  - id: sensitivity-label
    severity: block
    description: Sensitivity label is required and must be approved
    check:
      type: allowlist
      field: sensitivityLabel
      source: rules/allowlists/sensitivity-labels.yaml

  - id: environment-tag
    severity: block
    description: environment field must match name prefix
    check:
      type: cross_field_match
      left: environment
      right_regex_group: { field: name, pattern: '^([a-z]+)-', group: 1 }

  - id: cost-center
    severity: block
    description: cost-center must exist in finance allow-list
    check:
      type: allowlist
      field: costCenter
      source: rules/allowlists/cost-centers.yaml

  - id: region
    severity: block
    description: workspace.region must equal capacity.region
    check:
      type: cross_field_equal
      left: region
      right: capacity.region

  - id: description
    severity: block
    description: Description >= 30 chars and must mention business purpose
    check:
      type: composite
      all:
        - { type: min_length, field: description, value: 30 }
        - { type: regex, field: description,
            pattern: '(?i)(purpose|use case|enables|supports)' }

  - id: quota-per-team
    severity: warn
    description: Owning group cannot own more than N workspaces per env
    check:
      type: quota
      group_by: [roleAssignments.admins[0], environment]
      max:
        prd: 10
        stg: 20
        dev: 50
        sbx: 100
      source: fabric_admin_api   # live lookup

  - id: prod-extra-approval
    severity: block
    description: prd-* requires governance + security CODEOWNERS approval
    check:
      type: codeowners_required
      when: { field: environment, equals: prd }
      teams: ['@org/fabric-governance', '@org/security']

  - id: no-personal-workspaces
    severity: block
    description: Reject personal/My workspace style names
    check:
      type: regex_not
      field: name
      pattern: '(?i)(my[- ]?workspace|personal|sandbox-[a-z]+\.[a-z]+)'
```

Severity semantics:
- `block` → fails the check, blocks PR merge.
- `warn` → posts a warning comment, does not block.

---

## 4. Sample Manifest

`workspaces/prd-fin-revenue-reporting.yaml`

```yaml
apiVersion: fabric.governance/v1
kind: Workspace
metadata:
  name: prd-fin-revenue-reporting
  environment: prd
  costCenter: CC-10421
  region: westeurope
spec:
  description: >
    Production workspace supporting the Finance Revenue Reporting use case.
    Hosts the gold-layer lakehouse, certified semantic model, and executive
    Power BI reports consumed by the CFO org. Purpose: monthly close + daily
    revenue tracking.
  capacity:
    id: 11111111-2222-3333-4444-555555555555
    name: cap-fabric-prd-weu-01
    region: westeurope
  domain:
    name: Finance
    id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
  sensitivityLabel: Confidential\Finance
  roleAssignments:
    admins:
      - { kind: Group, id: 00000000-0000-0000-0000-000000000a01, displayName: sg-fabric-fin-admins }
      - { kind: Group, id: 00000000-0000-0000-0000-000000000a02, displayName: sg-platform-oncall }
    members:
      - { kind: Group, id: 00000000-0000-0000-0000-000000000b01, displayName: sg-fabric-fin-engineers }
    contributors: []
    viewers:
      - { kind: Group, id: 00000000-0000-0000-0000-000000000c01, displayName: sg-cfo-readers }
  tags:
    owner-team: finance-data-platform
    data-classification: confidential
    backup-tier: gold
    on-call: pagerduty:finance-data
```

---

## 5. Sample Validation Workflow

`.github/workflows/validate.yml`

```yaml
name: validate-workspace-request

on:
  pull_request:
    paths:
      - 'workspaces/**.yaml'
      - 'rules/**'
      - 'schemas/**'

permissions:
  contents: read
  pull-requests: write   # for sticky comment
  id-token: write        # for OIDC quota lookups (read-only admin API)

jobs:
  validate:
    runs-on: ubuntu-latest
    environment: fabric-readonly   # SPN with admin read scope only
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }

      - run: pip install -r scripts/requirements.txt

      - name: Detect changed manifests
        id: changes
        run: |
          git fetch origin ${{ github.base_ref }}
          CHANGED=$(git diff --name-only origin/${{ github.base_ref }}...HEAD \
            -- 'workspaces/*.yaml' | tr '\n' ' ')
          echo "files=$CHANGED" >> "$GITHUB_OUTPUT"

      - uses: azure/login@v2
        with:
          client-id:     ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id:     ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          allow-no-subscriptions: true

      - name: Run schema + policy validation
        id: validate
        run: |
          python scripts/validate.py \
            --schema schemas/workspace.schema.json \
            --policy rules/policy.yaml \
            --files ${{ steps.changes.outputs.files }} \
            --report report.md \
            --junit  report.xml
        continue-on-error: true

      - name: Upload report
        uses: actions/upload-artifact@v4
        with: { name: validation-report, path: report.* }

      - name: Sticky PR comment
        uses: marocchino/sticky-pull-request-comment@v2
        with:
          header: fabric-workspace-validation
          path: report.md

      - name: Fail if blocking rules failed
        if: steps.validate.outcome == 'failure'
        run: exit 1
```

`report.md` produced by `validate.py` looks like:

```markdown
### Fabric Workspace Validation — `prd-fin-revenue-reporting.yaml`

| Rule | Severity | Result |
|---|---|---|
| naming-convention | block | ✅ pass |
| required-capacity | block | ✅ pass |
| required-owners | block | ✅ pass |
| domain-assignment | block | ✅ pass |
| sensitivity-label | block | ✅ pass |
| environment-tag | block | ✅ pass |
| cost-center | block | ✅ pass |
| region | block | ✅ pass |
| description | block | ✅ pass |
| quota-per-team | warn | ⚠️ team owns 9/10 prd workspaces |
| prod-extra-approval | block | ⏳ awaiting @org/security |
| no-personal-workspaces | block | ✅ pass |

**Overall:** ✅ checks pass — awaiting CODEOWNERS approval.
```

---

## 6. Sample Provisioning Workflow

`.github/workflows/provision.yml`

```yaml
name: provision-workspace

on:
  push:
    branches: [main]
    paths: ['workspaces/**.yaml']

permissions:
  contents: read
  id-token: write

concurrency:
  group: fabric-provision-${{ github.ref }}
  cancel-in-progress: false

jobs:
  plan:
    runs-on: ubuntu-latest
    outputs:
      manifests: ${{ steps.diff.outputs.files }}
      env:       ${{ steps.diff.outputs.env }}
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 2 }
      - id: diff
        run: |
          CHANGED=$(git diff --name-only HEAD~1 HEAD -- 'workspaces/*.yaml' | tr '\n' ' ')
          echo "files=$CHANGED" >> "$GITHUB_OUTPUT"
          # If any prd-*.yaml changed → require prod environment
          if echo "$CHANGED" | grep -q '/prd-'; then
            echo "env=fabric-prod"    >> "$GITHUB_OUTPUT"
          else
            echo "env=fabric-nonprod" >> "$GITHUB_OUTPUT"
          fi

  apply:
    needs: plan
    runs-on: ubuntu-latest
    environment: ${{ needs.plan.outputs.env }}    # manual approval on fabric-prod
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r scripts/requirements.txt

      - uses: azure/login@v2
        with:
          client-id:     ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id:     ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          allow-no-subscriptions: true

      - name: Provision (idempotent)
        env:
          GH_REPO:    ${{ github.repository }}
          GH_SHA:     ${{ github.sha }}
        run: |
          python scripts/provision.py \
            --files ${{ needs.plan.outputs.manifests }} \
            --marker "managed-by:gh:${GH_REPO}@${GH_SHA}"
```

### 6.1 Provisioner behavior (`scripts/provision.py`)

Pseudocode for the idempotent operations:

```python
TOKEN = az_get_token("https://api.fabric.microsoft.com/.default")
HDR   = {"Authorization": f"Bearer {TOKEN}"}
BASE  = "https://api.fabric.microsoft.com/v1"

def upsert(manifest, marker):
    existing = find_workspace_by_name(manifest.metadata.name)
    if existing and marker_in_description(existing, "managed-by:gh:"):
        ws_id = existing.id
        patch_workspace(ws_id, manifest, marker)
    elif existing:
        raise RuntimeError(
            f"Workspace {manifest.metadata.name} exists but is unmanaged. "
            "Adopt it via scripts/adopt.py first."
        )
    else:
        ws_id = create_workspace(manifest, marker)

    assign_capacity(ws_id, manifest.spec.capacity.id)
    sync_role_assignments(ws_id, manifest.spec.roleAssignments)
    assign_domain(ws_id, manifest.spec.domain.id)          # admin API
    apply_sensitivity_label(ws_id, manifest.spec.sensitivityLabel)
    return ws_id
```

### 6.2 REST calls used

| Operation | Method & URL | Body / Notes |
|---|---|---|
| Create workspace | `POST {BASE}/workspaces` | `{ "displayName": "...", "description": "<user desc>\n\nmanaged-by:gh:org/repo@<sha>" }` |
| Find by name | `GET  {BASE}/workspaces?$filter=displayName eq '...'` | paginated |
| Update workspace | `PATCH {BASE}/workspaces/{id}` | description / displayName |
| Assign capacity | `POST {BASE}/workspaces/{id}/assignToCapacity` | `{ "capacityId": "..." }` |
| Unassign capacity | `POST {BASE}/workspaces/{id}/unassignFromCapacity` | — |
| List role assignments | `GET  {BASE}/workspaces/{id}/roleAssignments` | reconcile loop |
| Add role assignment | `POST {BASE}/workspaces/{id}/roleAssignments` | `{ "principal": {...}, "role": "Admin\|Member\|Contributor\|Viewer" }` |
| Update role | `PATCH {BASE}/workspaces/{id}/roleAssignments/{principalId}` | — |
| Delete role | `DELETE {BASE}/workspaces/{id}/roleAssignments/{principalId}` | drift removal |
| Assign domain | `POST https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/assignWorkspaces` | `{ "workspacesIds": ["..."] }` |
| Sensitivity label | `POST https://api.powerbi.com/v1.0/myorg/admin/workspaces/{id}/sensitivityLabel` | requires admin + MIP perms |

All calls wrapped in retry with exponential backoff on `429`/`5xx` honoring `Retry-After`.

---

## 7. Approval Model

### 7.1 `.github/CODEOWNERS`

```
# Default: platform team owns the framework
*                                @org/fabric-platform

# Any workspace manifest change needs governance
/workspaces/*.yaml               @org/fabric-platform @org/fabric-governance

# Production manifests additionally need security
/workspaces/prd-*.yaml           @org/fabric-platform @org/fabric-governance @org/security

# Rules and schemas: governance + security only
/rules/                          @org/fabric-governance @org/security
/schemas/                        @org/fabric-governance @org/security
/scripts/                        @org/fabric-platform   @org/security
/.github/workflows/              @org/fabric-platform   @org/security
```

### 7.2 Branch protection on `main`

- Require PR before merge.
- Require **2 approving reviews** (3 for `prd-*` via CODEOWNERS expansion).
- Require review from CODEOWNERS.
- Require status checks: `validate-workspace-request / validate`.
- **Dismiss stale approvals** on new commits.
- Require **linear history** (squash merge only).
- Restrict who can push to `main` to GitHub Actions only.
- Require **signed commits**.

### 7.3 GitHub Environments

| Environment | Reviewers | Wait timer | Secrets |
|---|---|---|---|
| `fabric-readonly` | none (CI only) | 0 | `AZURE_CLIENT_ID` (read-only SPN) |
| `fabric-nonprod`  | `@org/fabric-platform` | 0 | provisioner SPN client id |
| `fabric-prod`     | `@org/fabric-governance` AND `@org/security` (required reviewers) | 10 min | provisioner SPN client id |

The `fabric-prod` environment gate means even after merge, a human must click **Approve** before any prd workspace touches Fabric.

---

## 8. Audit & Drift Detection

`.github/workflows/audit-drift.yml`

```yaml
name: audit-drift
on:
  schedule: [{ cron: '17 2 * * *' }]   # 02:17 UTC nightly
  workflow_dispatch:

permissions:
  contents: read
  issues:   write
  id-token: write

jobs:
  audit:
    runs-on: ubuntu-latest
    environment: fabric-readonly
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r scripts/requirements.txt
      - uses: azure/login@v2
        with:
          client-id:     ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id:     ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          allow-no-subscriptions: true
      - run: python scripts/audit_drift.py --open-issues
```

`audit_drift.py` logic:

1. `GET https://api.fabric.microsoft.com/v1/admin/workspaces` (paginated) → live inventory.
2. Load all `workspaces/*.yaml` → desired inventory.
3. Compute three sets:
   - **Unmanaged** — exists in tenant, no manifest, no `managed-by:` marker → opens issue tagged `drift/unmanaged`.
   - **Drifted** — exists in both, but live state differs (capacity, roles, domain, label, description) → opens issue tagged `drift/configuration` with a diff in the body.
   - **Orphaned manifest** — manifest in repo, workspace deleted in tenant → opens issue tagged `drift/orphan-manifest`.
4. Reuses an existing open issue if the same key already has one (no duplicates).

Issue body template:

```markdown
## Drift detected: `prd-fin-revenue-reporting`

**Type:** configuration drift
**Detected:** 2025-01-14T02:17:00Z
**Workspace ID:** 11111111-...

### Differences

| Field | Manifest | Live |
|---|---|---|
| capacity.id | cap-prd-weu-01 | cap-prd-weu-02 |
| roleAssignments.admins | [sg-fin-admins, sg-oncall] | [sg-fin-admins, sg-oncall, alice@contoso] |

### Remediation

- Open a PR re-asserting the manifest, or
- Open a PR updating the manifest to match live state (with justification).
```

---

## 9. Limitations & Gotchas

- **Rate limits.** Fabric/Power BI APIs throttle aggressively (often per-tenant). Implement retries with exponential backoff and **always honor `Retry-After`**. Batch role assignments where possible; serialize admin-API calls.
- **SPN cannot be sole admin.** Some Fabric flows (e.g., gateway management, certain item types) misbehave if the only Admin is a service principal. **Always co-assign at least one Entra security group as Admin** — enforced by `required-owners` rule.
- **Domain assignment requires Fabric Administrator role** on the SPN — not just tenant-setting access. Assign via Entra → Roles → Fabric Administrator.
- **Sensitivity labels require MIP permissions.** The SPN must be in the publishing scope of the labels in Microsoft Purview, otherwise `sensitivityLabel` calls return 403 with a misleading message.
- **Tenant settings propagate slowly.** Up to 15 minutes after a change. Don't run validation immediately after toggling settings.
- **Capacity assignment requires Capacity Admin** rights on the *target* capacity for the SPN. This is granted on each capacity individually in the Admin Portal.
- **Workspace name uniqueness** is tenant-wide and case-insensitive. The `naming-convention` regex helps, but races between two simultaneous PRs can still collide — the provisioner must handle 409 by re-querying and surfacing a clear error.
- **`assignToCapacity` is asynchronous.** Poll `GET /workspaces/{id}` until `capacityId` reflects the desired value before subsequent operations.
- **Description field is the only durable marker** for "managed-by" today (no native tags on workspaces). Keep the marker on its own line at the end of the description to avoid clobbering user content.
- **Admin APIs return all workspaces including personal/`MyWorkspace`** — filter `type != 'PersonalGroup'` in drift detection.
- **OIDC subject claims** must match exactly per environment, including the `environment:` segment. A typo silently falls back to "no federated credential matched" → token request fails.
- **CODEOWNERS does not enforce "AND" across teams natively** — branch protection's "Require review from Code Owners" treats each owner line as sufficient. Use the `prod-extra-approval` rule in CI to verify both teams approved before allowing merge.
- **Power BI vs Fabric API surface** is still split. Some admin operations (sensitivity labels, certain tenant settings) live under `api.powerbi.com/v1.0/myorg/admin/...`. Keep both base URLs in your client.

---

## 10. Implementation Checklist

**Tenant & identity**
- [ ] Create Entra security group `sg-fabric-provisioner`.
- [ ] Create Entra app registration `app-fabric-provisioner`; add to `sg-fabric-provisioner`.
- [ ] Add federated credentials for `repo:org/fabric-governance:environment:fabric-nonprod` and `…:fabric-prod`.
- [ ] Grant Fabric Administrator role to the SPN.
- [ ] Add the SPN as Capacity Admin on each in-scope Fabric capacity.
- [ ] Add the SPN to MIP label publishing scope for all approved sensitivity labels.
- [ ] Configure tenant settings per §1.2; wait 15 min for propagation.

**Repository**
- [ ] Create repo `org/fabric-governance` with the layout in §2.
- [ ] Commit `schemas/workspace.schema.json` derived from §4.
- [ ] Commit `rules/policy.yaml` and per-env allow-lists.
- [ ] Implement `scripts/validate.py`, `scripts/provision.py`, `scripts/audit_drift.py`.
- [ ] Add `requirements.txt` (`pyyaml`, `jsonschema`, `requests`, `azure-identity`).

**GitHub configuration**
- [ ] Create environments `fabric-readonly`, `fabric-nonprod`, `fabric-prod` with reviewers per §7.3.
- [ ] Set repo secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
- [ ] Configure branch protection on `main` per §7.2.
- [ ] Commit `.github/CODEOWNERS`.
- [ ] Commit the three workflows (`validate.yml`, `provision.yml`, `audit-drift.yml`).

**Bootstrap & adoption**
- [ ] Run `scripts/audit_drift.py` once against the live tenant; treat output as the adoption backlog.
- [ ] Author manifests for each existing workspace; add the `managed-by:` marker via a one-time `scripts/adopt.py` run.
- [ ] Open the first real PR end-to-end as a smoke test; verify sticky comment, environment gate, and provisioning succeed.

**Operationalize**
- [ ] Document the requester journey in `README.md` (copy a sample manifest, fill in fields, open PR).
- [ ] Wire drift issues to the platform team's on-call rotation.
- [ ] Schedule a quarterly review of `rules/policy.yaml` and allow-lists via PR.