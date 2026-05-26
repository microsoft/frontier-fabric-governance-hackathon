# Challenge 07 — Audit & observability

> **Outcome:** every governance event (PRs, workflow runs, Fabric activity, drift
> findings) lands in an Eventhouse, surfaces in a Power BI dashboard, and trips
> Activator alerts when anomalies appear.

## Why this challenge exists

Governance you can't see is governance that has already failed. This challenge
closes the loop: PR → provision → audit → dashboard → alert → next PR. It is
also the densest "Skills for Fabric" challenge — you'll use four authoring
skills end-to-end.

## Learning objectives

1. Use `eventhouse-authoring-cli` to stand up a KQL database for governance audit.
2. Use `eventstream-authoring-cli` to ingest GitHub webhook events and Fabric
   activity events into that KQL database in near real-time.
3. Use `powerbi-authoring-cli` to publish a "Governance Health" dashboard.
4. Use `activator-authoring-cli` to fire alerts when metrics breach thresholds.
5. Use `eventhouse-consumption-cli` to answer governance questions ad-hoc from chat.

## Prerequisites

- Challenges 00–02 complete (you need at least one provisioned workspace and the
  items machinery).
- Capacity F4+ recommended (Eventhouse + Power BI consume compute).
- Skills installed: `eventhouse-authoring-cli`, `eventhouse-consumption-cli`,
  `eventstream-authoring-cli`, `powerbi-authoring-cli`, `activator-authoring-cli`.

## Tasks

### Task 1 — Provision the audit workspace via PR

Add a workspace manifest `workspaces/dev-plt-gov-audit.yaml` with sensitivity
`Confidential` and a `gov-audit` cost-center tag. Merge it (Challenge 01 flow).

### Task 2 — Stand up the Eventhouse + KQL database

From chat:

```
@eventhouse-authoring-cli In workspace "dev-plt-gov-audit", create an Eventhouse
"eh_gov_audit" with KQL database "gov_audit" and tables:
  - pr_events(received_at:datetime, pr_id:long, action:string, repo:string,
              author:string, labels:dynamic, payload:dynamic)
  - workflow_runs(received_at:datetime, run_id:long, name:string, status:string,
                  conclusion:string, repo:string, head_sha:string, payload:dynamic)
  - fabric_activity(received_at:datetime, activity:string, user:string,
                    workspaceId:string, itemId:string, payload:dynamic)
Apply 90-day retention on all tables.
```

Commit the Skill's output (KQL `.kql` files + Eventhouse definition) into
`items/dev-plt-gov-audit/`.

### Task 3 — Ingest GitHub webhook events

Use **Eventstream**:

```
@eventstream-authoring-cli In workspace "dev-plt-gov-audit", create an Eventstream
"es_gh_audit" with:
  - Source: Custom App (HTTP) — used by a GitHub webhook
  - Destinations: Eventhouse "eh_gov_audit", tables "pr_events" and "workflow_runs"
```

Configure a **GitHub webhook** on the repo pointing at the Eventstream's HTTP
ingestion URL. Pick events: `pull_request`, `workflow_run`, `pull_request_review`.

### Task 4 — Ingest Fabric activity events

Two options; pick one:

**Option A (admin API export).** A scheduled workflow
`.github/workflows/audit-export.yml` calls
`GET /admin/activityevents` once per hour and posts events to the Eventstream HTTP
source.

**Option B (Purview audit pipe).** Configure Purview Audit → Activity Explorer
→ Eventstream connector (preview, where available).

Either way: the `fabric_activity` table fills up.

### Task 5 — Build the governance dashboard

From chat:

```
@powerbi-authoring-cli In workspace "dev-plt-gov-audit", create a Power BI report
"Governance Health" connected to KQL database "gov_audit" with pages:
  - Workspaces: count by domain, label coverage %
  - PR throughput: median time from PR open to merge, by week
  - Provision outcomes: success / failure counts by week
  - Drift: open drift issues by category
  - Access: number of User Admin bindings on prd workspaces (target = 0)
```

Commit the report definition into `items/dev-plt-gov-audit/`.

### Task 6 — Activator alerts

From chat:

```
@activator-authoring-cli In workspace "dev-plt-gov-audit", create reflexes that fire when:
  - More than 5 unmanaged workspaces are detected in a 24h window.
  - Any User Admin appears on a prd-* workspace.
  - A provision run fails 3+ times in a row.
  - A drift issue stays open for more than 7 days.
```

Wire reflex outputs to a Teams / email channel.

### Task 7 — Answer questions from chat

Use `eventhouse-consumption-cli` to validate:

```
@eventhouse-consumption-cli In gov_audit, how many PRs labelled "break-glass"
were merged in the last 30 days, and who reviewed them?
```

```
@eventhouse-consumption-cli In gov_audit, show median minutes from PR open to
provision success per repo, weekly, last 8 weeks.
```

## Success criteria

- [ ] PR open / merge events appear in `pr_events` within 60 seconds.
- [ ] Workflow run completions appear in `workflow_runs` within 60 seconds.
- [ ] Fabric activity events appear hourly (Option A) or live (Option B).
- [ ] The Power BI report renders all five pages with real data.
- [ ] At least one Activator reflex has fired and notified a channel.

## Stretch goals

- **Cross-tenant audit.** Add a second tenant's activity feed via OneLake external
  sharing; show a unified dashboard.
- **Anomaly detection.** Add a KQL query using `series_decompose_anomalies` on
  PR throughput and feed it to the Activator.
- **Skill catalog usage telemetry.** Track which Skills your teams call and how
  often; surface as a fifth dashboard page.

## MCP tips

- The local MCP's `docs_best-practices` tool has a "real-time intelligence" topic
  that catalogs the patterns the Eventhouse + Eventstream skills follow.

## Skills tips

- The four authoring skills (Eventhouse, Eventstream, Power BI, Activator) are
  separate processes. The agent will sequence them; you can also call them
  individually if you want to debug step-by-step.

## References

- [Eventhouse in Fabric](https://learn.microsoft.com/fabric/real-time-intelligence/eventhouse)
- [Eventstream sources & destinations](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/overview)
- [Activator (Reflex) overview](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-introduction)
- [Skills for Fabric — Eventhouse authoring CLI](https://github.com/microsoft/skills-for-fabric/tree/main/skills/eventhouse-authoring-cli)
- [Skills for Fabric — Eventstream authoring CLI](https://github.com/microsoft/skills-for-fabric/tree/main/skills/eventstream-authoring-cli)
- [Skills for Fabric — Power BI authoring CLI](https://github.com/microsoft/skills-for-fabric/tree/main/skills/powerbi-authoring-cli)
- [Skills for Fabric — Activator authoring CLI](https://github.com/microsoft/skills-for-fabric/tree/main/skills/activator-authoring-cli)
