# Challenge 05 — Medallion architecture bootstrap

> **Outcome:** a single PR scaffolds a fully governed Bronze / Silver / Gold
> lakehouse set with the right sensitivity labels, endorsement, and reference
> notebooks — using the **`e2e-medallion-architecture`** Skill end-to-end.

## Why this challenge exists

Most data teams reinvent medallion bootstrap every project. The wheel they
reinvent is usually missing the governance spokes: labels are set "later",
endorsement never happens, gold workspaces inherit dev's sensitivity floor.
This challenge teaches you to ship medallion + governance as one atomic PR.

## Learning objectives

1. Drive a complex multi-item scaffold from a single high-level manifest.
2. Encode per-tier policy: tier ⇒ sensitivity, ⇒ endorsement, ⇒ owners group,
   ⇒ allowed users.
3. Use the `e2e-medallion-architecture` Skill to do the heavy lifting.
4. Wrap the Skill's output in your validate + provision loop.

## Prerequisites

- Challenges 00–02 complete (item manifests already work).
- Capacity at F4+ recommended.
- Skill installed: `e2e-medallion-architecture` (plus `spark-authoring-cli`,
  `sqldw-authoring-cli`, `powerbi-authoring-cli` for sub-tasks the medallion
  skill orchestrates).

## Tasks

### Task 1 — Design the medallion manifest

Add `schemas/medallion.schema.json` and example
`challenges/05-medallion-bootstrap/starter/medallion/finance-revenue.yaml`:

```yaml
name: finance-revenue
description: "End-to-end medallion stack for Finance Revenue Reporting."
businessUnit: Finance
domain: Finance
sourceSystem:
  kind: AzureSql
  connectionRef: kv-secret://finance-sql-prd
tiers:
  bronze:
    workspace: dev-fin-bronze
    lakehouse: lh_bronze_revenue
    sensitivityLabel: General
    endorsement: null
    ownersGroup: sg-fin-engineers
  silver:
    workspace: dev-fin-silver
    lakehouse: lh_silver_revenue
    sensitivityLabel: General
    endorsement: Promoted
    ownersGroup: sg-fin-engineers
  gold:
    workspace: prd-fin-gold
    lakehouse: lh_gold_revenue
    semanticModel: sm_gold_revenue
    sensitivityLabel: Confidential
    endorsement: Certified
    ownersGroup: sg-fin-admins
schedule:
  bronzeToSilver: "0 2 * * *"
  silverToGold: "0 4 * * *"
```

### Task 2 — Policy: per-tier defaults

Add a `medallion:` block to `rules/policy.yaml`:

- Gold tier must have `sensitivityLabel ≥ Confidential`.
- Gold tier must have `endorsement = Certified`.
- Gold tier `workspace` must match `^prd-`.
- Bronze and Silver workspaces must reference a non-prod capacity.
- The `ownersGroup` for gold must include at least one Security-cleared admin.

### Task 3 — Validator extension

`scripts/validate_medallion.py` (or extend `validate.py`):

1. For each medallion manifest, validate against the schema + medallion policy.
2. Validate that the referenced workspaces exist as manifests in `workspaces/`
   (or auto-create them in `starter/` based on the medallion manifest).
3. Validate that owners groups exist in Entra (live check).

### Task 4 — Provisioner: call the Skill

The Skill is the right tool for *creating* the artifacts. Your job is to call it
from a workflow with deterministic inputs.

In `.github/workflows/medallion.yml`:

```yaml
- name: Bootstrap medallion via Skill
  run: |
    copilot skill run e2e-medallion-architecture \
      --manifest ${{ matrix.manifest }} \
      --output-dir .skill-output/
- name: Capture artifacts into manifests
  run: python scripts/capture_medallion_output.py \
       --input .skill-output/ \
       --into items/
- name: Provision items
  run: python scripts/provision.py --items .skill-output/items.txt
```

The Skill scaffolds notebooks, lakehouse schemas, and a semantic model. Your
`capture_medallion_output.py` converts the Skill's output into proper item
manifests under `items/`, so the next drift run can reconcile them.

### Task 5 — Apply endorsement and labels

After provisioning, set:

- Endorsement (`Promoted` or `Certified`) via the Power BI admin API on
  semantic models / reports in the Gold workspace.
- Sensitivity labels on the lakehouses (Challenge 03 wiring already does this).

### Task 6 — Smoke test

Open a PR that adds your medallion manifest. After merge + environment approval:

1. Bronze, Silver, and Gold workspaces exist.
2. Bronze/Silver/Gold lakehouses exist with the per-tier label.
3. Gold semantic model exists, certified.
4. Drift detector reports zero drift.

Ask the Fabric Core MCP:

```
Search the catalog for items matching "revenue". Group by workspace.
What's the sensitivity label and endorsement of the "sm_gold_revenue" semantic model?
```

## Success criteria

- [ ] One medallion manifest produces ≥ 3 workspaces, ≥ 3 lakehouses, and ≥ 1
      semantic model, all with correct labels and endorsement.
- [ ] Removing the `endorsement: Certified` line on Gold fails validation.
- [ ] The Skill output is captured into `items/` so it's drift-checkable.

## Stretch goals

- **Templatized variants.** Parameterize the medallion manifest to support
  finance vs. marketing source schemas with one shared template.
- **Notebook tests.** Each tier's transformation notebook gets a companion test
  notebook the validate workflow runs in dry-run mode.
- **Cost guardrails.** Tag every medallion item with `cost-stream: finance-revenue`;
  build a Power BI report in Challenge 07 that breaks down spend per medallion.

## MCP tips

- Use the **local MCP** `docs_best-practices` tool with topic `medallion` before
  designing your manifest — it surfaces the official guidance the Skill follows.

## Skills tips

- The `e2e-medallion-architecture` skill is composable. If you only need
  Bronze → Silver, call it with just those tiers and skip Gold; your validator
  must allow that shape.

## References

- [Skills for Fabric — e2e-medallion-architecture](https://github.com/microsoft/skills-for-fabric/tree/main/skills/e2e-medallion-architecture)
- [Medallion architecture in Fabric](https://learn.microsoft.com/fabric/onelake/onelake-medallion-lakehouse-architecture)
- [Endorsement in Fabric](https://learn.microsoft.com/fabric/governance/endorsement-overview)
