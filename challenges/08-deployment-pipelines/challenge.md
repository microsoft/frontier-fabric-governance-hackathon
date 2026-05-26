# Challenge 08 — Deployment pipelines & cross-environment promotion

> **Outcome:** items promote dev → stg → prd through **Fabric deployment
> pipelines**, gated by PR labels and the same `production` environment approval
> as Challenge 01.

## Why this challenge exists

A governed workspace + governed items aren't enough if "going to prod" still
means a human dragging items between workspaces in the portal. This challenge
plugs Fabric's native deployment pipelines into the same PR review + OIDC +
environment-gate machine you've used since Challenge 01.

## Learning objectives

1. Model Fabric deployment pipelines as code.
2. Trigger a stage promotion (`dev → stg`, `stg → prd`) from a PR label.
3. Reuse the `production` GitHub environment as the manual gate for prod
   promotions.
4. Implement a rollback flow (`revert/prd`) that re-applies the previous
   successful state.

## Prerequisites

- Challenges 00–02 complete.
- For each pipeline you intend to model, you have a dev / stg / prd workspace
  trio under repo management.

## Tasks

### Task 1 — Pipeline manifest

Add `schemas/pipeline.schema.json` and example:

```yaml
# pipelines/finance-revenue.yaml
name: finance-revenue
description: "Promotion pipeline for the Finance Revenue medallion stack."
stages:
  - name: dev
    workspace: dev-fin-gold
  - name: stg
    workspace: stg-fin-gold
  - name: prd
    workspace: prd-fin-gold
promotionRules:
  - from: dev
    to: stg
    label: promote/stg
    requiresReviewers: ["@org/fabric-platform"]
  - from: stg
    to: prd
    label: promote/prd
    requiresReviewers: ["@org/fabric-governance", "@org/security"]
    environment: production
itemsToPromote:
  - kind: Lakehouse
    namePattern: "lh_gold_*"
  - kind: SemanticModel
    namePattern: "sm_gold_*"
  - kind: Report
    namePattern: "rpt_gold_*"
```

### Task 2 — Validate pipeline manifests

Extend `scripts/validate.py`:

- Every `stages[*].workspace` references a workspace manifest.
- Stages are in order `dev` → `stg` → `prd`.
- `prd` rule must require `environment: production`.
- `itemsToPromote[*].namePattern` is a valid regex.

### Task 3 — `promote.yml` workflow

Add `.github/workflows/promote.yml`:

```yaml
on:
  pull_request:
    types: [labeled]
jobs:
  promote:
    if: startsWith(github.event.label.name, 'promote/')
    runs-on: [self-hosted, fabric-gov]
    environment: ${{ contains(github.event.label.name, 'prd') && 'production' || '' }}
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
      - run: python scripts/promote.py --label "${{ github.event.label.name }}" \
                                      --pr ${{ github.event.pull_request.number }}
```

### Task 4 — Implement `scripts/promote.py`

Steps inside `promote.py`:

1. Resolve the pipeline manifest whose items match the PR diff (or accept an
   explicit `--pipeline` argument set by a PR comment).
2. Look up the Fabric deployment pipeline ID by name (create if absent).
3. Bind stages to workspace IDs via the deployment pipelines API.
4. Compute the item set to promote (intersect `itemsToPromote[*].namePattern`
   with items present in the *source* stage workspace).
5. Call **Deploy stage** API for `from → to`.
6. Poll the long-running operation; on success, comment back on the PR with the
   summary; on failure, leave the PR open.

### Task 5 — Rollback

`revert/prd` label triggers `scripts/promote.py --revert prd`:

1. Find the previous successful deployment for the pipeline.
2. Re-deploy that snapshot to prd (via the deployment pipelines API).
3. Open a follow-up issue requiring a post-mortem PR.

### Task 6 — Verify via Fabric Core MCP

```
Show items in workspace prd-fin-gold. Highlight which were updated in the last hour.
List the deployment pipelines I have access to. Which stage is each workspace in?
```

## Success criteria

- [ ] Labelling a PR with `promote/stg` promotes items from `dev` → `stg`.
- [ ] Labelling a PR with `promote/prd` *also* triggers the `production`
      environment gate before the items move.
- [ ] `revert/prd` puts prd back to the prior successful snapshot.

## Stretch goals

- **Schema-drift checks.** Before promoting Gold semantic models, run a schema
  diff between source and target — block on breaking changes.
- **Selective promotion.** Allow PR comments like `/promote only sm_gold_revenue`
  to override `itemsToPromote`.
- **Canary releases.** Use deployment rules / source-control branching to ship a
  subset of users a new gold report first; gate full rollout on a metric.

## MCP tips

- The Core MCP `get_operation_state` + `get_operation_result` tools wrap the
  long-running operation polling. Use them from `promote.py` too — same API,
  just in Python.

## Skills tips

- `sqldw-operations-cli` and `spark-operations-cli` are useful for promotion
  pre-checks: warehouse runtime stats, Spark job health. Run them before
  promotion as a "stage gate" check.

## References

- [Fabric deployment pipelines](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines)
- [Deployment pipelines REST API](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines)
- [Git integration in Fabric](https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration)
