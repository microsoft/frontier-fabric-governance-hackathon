# Capstone — End-to-end integration

> **Outcome:** a single Pull Request, opened by your team, exercises every
> challenge you completed — workspace, items, domain, label, access, medallion,
> agent, audit, promotion — and you can prove it all worked from the dashboard.

## Goal

Pick a realistic business scenario and ship it through your governance plane in
one coordinated PR (or a short series of stacked PRs). Then demo the artifacts
to the judges:

1. Manifests committed.
2. Validate workflow green.
3. Provision workflow green (with the `production` environment gate visibly approved).
4. Live Fabric resources matching the manifests.
5. Governance dashboard showing the new activity.
6. Drift detector showing zero drift.
7. (Bonus) An Activator alert that fired on something interesting.

## Suggested scenario

> **"Finance Revenue Reporting goes live in production"**
>
> A new business line in Finance needs to ship a certified revenue dashboard
> across dev → stg → prd in two weeks. They need ingestion from Azure SQL into a
> bronze lakehouse, dedup + standardize in silver, build a certified gold
> semantic model, and expose a Fabric Data Agent for executives.

Adapt freely. The scenario just exists to keep your team's PR coherent.

## Required artifacts

Map each row to the relevant challenge(s).

| # | Artifact | Challenge(s) |
|---|---|---|
| 1 | `workspaces/dev-fin-revenue.yaml`, `workspaces/stg-fin-revenue.yaml`, `workspaces/prd-fin-revenue.yaml` | 01 |
| 2 | `domains/finance.yaml`, `capacities/<your-capacity>.yaml` | 03 |
| 3 | `items/<workspace>/lh_bronze_*.yaml`, `lh_silver_*.yaml`, `lh_gold_*.yaml` | 02 |
| 4 | `items/prd-fin-revenue/sm_gold_revenue.yaml` (Certified) | 02, 05 |
| 5 | `access/<workspace>.yaml` for each workspace, group-first, expiring user bindings | 04 |
| 6 | `medallion/finance-revenue.yaml` | 05 |
| 7 | `agents/agent-finance-revenue-qa.yaml` + instructions file | 06 |
| 8 | Eventhouse + Eventstream + dashboard already provisioned in `dev-plt-gov-audit` | 07 |
| 9 | `pipelines/finance-revenue.yaml` + a `promote/stg` PR and a `promote/prd` PR | 08 |

You don't have to do every row — finishing any 5 is a strong submission.

## Judging rubric

100 points total.

| Area | Points | What we look for |
|---|---|---|
| **Correctness** | 25 | Manifests pass validate; resources actually exist; labels and endorsement applied. |
| **Coverage** | 20 | Number of challenge areas integrated into the PR chain. |
| **Governance discipline** | 20 | No out-of-band portal clicks; `managed-by:` marker present everywhere; drift = 0. |
| **MCP + Skills usage** | 15 | Evidence the team used both Fabric MCP and at least 2 Skills in the workflow. |
| **Observability** | 10 | Dashboard reflects this scenario's activity; at least one Activator alert wired. |
| **Story** | 10 | Demo articulates the business benefit, not just the plumbing. |

## Demo expectations

A ~10-minute walkthrough that includes:

1. The original PR (open in GitHub).
2. The sticky validate comment (passing).
3. The provision run (with environment approval timestamp).
4. The Fabric portal (showing the workspaces and items).
5. The governance dashboard (one filter on the team's pipeline).
6. The agent answering a sample question.
7. Optional: an injected drift event, with the detector catching it.

## Stretch (if you have spare time)

- Demonstrate the **rollback** flow on prd (Challenge 08).
- Demonstrate the **break-glass** access path (Challenge 04) with the
  automatic expiry follow-up PR.
- Show a Purview DSPM signal blocking an agent (Challenge 06).
- Add the team's own new policy rule (e.g., "no Lakehouse may be unowned by
  a Group") to `rules/policy.yaml` with tests.

## References

Every previous challenge — keep them open in tabs during the capstone.
