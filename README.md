# Agentic Governance Blueprint for Fabric

An agent-assisted governance framework that helps teams deploy Fabric the "right way"
faster—codifying standards and producing repeatable templates, checks, and guidance
using Fabric Skills and GitHub Copilot powered by *skills-for-fabricAgents*.

> Treat the Fabric tenant as **declarative infrastructure**. Nothing exists unless a YAML
> manifest for it lives in `main`, was reviewed via Pull Request, and was provisioned by a
> service principal through GitHub Actions.

## Who this is for

- **Platform engineers** standing up Fabric for a regulated enterprise.
- **Fabric admins** who want to move from ClickOps to Git-driven governance.
- **Data engineers** who need a safe, repeatable way to land lakehouses, warehouses,
  and notebooks inside a governance frame.

## What you'll learn

By the end of the hackathon each team will have a working, auditable, PR-driven
governance plane that covers:

1. Workspace lifecycle (create / update / decommission / drift detect)
2. Item lifecycle (lakehouse, notebook, warehouse, semantic model)
3. Domains, capacities, sensitivity labels, endorsement
4. Group-based access with expiring assignments and access reviews
5. Bronze/Silver/Gold (medallion) bootstrap with policy-correct defaults
6. Governed Fabric Data Agents with allow-listed data sources
7. Real-time audit & observability dashboards
8. Cross-environment promotion via Fabric deployment pipelines

Every challenge teaches you how to do the same job two ways:

- **Conversationally**, through the **Fabric Core MCP Server** and **Fabric local MCP**
  from inside VS Code or GitHub Copilot CLI.
- **Declaratively**, through manifests + PRs + Actions, so the same operation is
  reviewable, auditable, and replayable.

## The learning path

```
┌──────────────────────────┐
│ 00 — Setup               │  Tenant, identity, MCP + Skills install
└────────────┬─────────────┘
             │
┌────────────▼─────────────┐
│ 01 — Workspace as code   │  PR → validate → OIDC provision → drift
└────────────┬─────────────┘
             │
   ┌─────────┼──────────────────────────────┬──────────────┐
   │         │                              │              │
┌──▼──┐  ┌───▼────┐   ┌─────────────┐  ┌────▼────┐   ┌─────▼────┐
│ 02  │  │  03    │   │     04      │  │   05    │   │    06    │
│Items│  │Domains │   │ Access /    │  │Medallion│   │  Data    │
│     │  │Capacit.│   │ RBAC        │  │Bootstrap│   │  Agents  │
│     │  │Sensit. │   │ lifecycle   │  │         │   │          │
└──┬──┘  └────────┘   └─────────────┘  └─────────┘   └──────────┘
   │
┌──▼──────────────────────┐    ┌───────────────────────────┐
│ 07 — Audit & observ.    │    │ 08 — Deployment pipelines │
└──────────┬──────────────┘    └─────────────┬─────────────┘
           │                                 │
           └────────────┬────────────────────┘
                        │
              ┌─────────▼──────────┐
              │     Capstone        │
              └─────────────────────┘
```

Challenges **02 → 08** branch from Challenge **01** and can be tackled in parallel by
different teams or in any order; the **Capstone** integrates them all.

## Prerequisites

- A Microsoft Fabric tenant with at least one capacity (F2 or higher; F4+ recommended for
  Challenges 05 and 07).
- Microsoft Entra ID app registration permissions (or a tenant admin to do Challenge 00 for you).
- A GitHub organization where you can create repos, environments, branch-protection rules,
  and federated credentials.
- VS Code (latest) and the GitHub Copilot extension, **or** GitHub Copilot CLI.
- Python 3.12+ and Git on your machine.

The full prerequisite checklist lives in [`challenges/00-setup/challenge.md`](challenges/00-setup/challenge.md).

## How to run the hackathon

1. Fork this repo into the org you'll use during the event.
2. Complete **Challenge 00** to make your tenant + dev box hackathon-ready.
3. Complete **Challenge 01** to learn the core PR → validate → provision loop.
4. Pick one or more of **Challenges 02–08** based on your team's interests.
5. Finish with the **Capstone**: a single PR that exercises every challenge you completed.

> **Facilitators / coaches / customer-engagement leads:** start from
> [`docs/delivery-guide.md`](docs/delivery-guide.md) for pre-flight checklists,
> sample agendas, per-challenge coaching cards, judging logistics, and the
> PR-driven model for evolving the blueprint after each delivery. For a
> customer-facing visual tour of the 10 challenges, share
> [`docs/challenges-overview.md`](docs/challenges-overview.md).

Each challenge folder contains:

- `challenge.md` — the lab instructions (scenario, objectives, prereqs, tasks,
  success criteria, stretch goals, MCP + Skills tips, references).
- Optional `starter/` — manifests, schemas, and scripts you extend (added per
  challenge as materials are published).
- Optional `solution/` — a reference implementation when available.

## Repo layout

```
.
├── README.md                       ← you are here
├── README.original.md              ← the pre-hackathon README, kept for reference
├── docs/                           ← cross-challenge reference material
│   ├── setup.md                    ← one-time operator runbook
│   ├── delivery-guide.md           ← facilitator runbook (agendas, coaching, retro)
│   ├── challenges-overview.md      ← customer-facing visual tour of the 10 challenges
│   ├── workspace-approval-workflow.md
│   ├── mcp-and-skills.md           ← Fabric MCP + Skills install & usage
│   ├── identity-model.md           ← OIDC, federated credentials, SPN scopes
│   ├── troubleshooting.md          ← shared error catalog
│   └── glossary.md                 ← Fabric + governance terms
├── challenges/
│   ├── 00-setup/
│   ├── 01-workspace-as-code/
│   ├── 02-items-as-code/
│   ├── 03-domains-capacities-sensitivity/
│   ├── 04-access-rbac-lifecycle/
│   ├── 05-medallion-bootstrap/
│   ├── 06-data-agent-governance/
│   ├── 07-audit-observability/
│   ├── 08-deployment-pipelines/
│   └── capstone/
├── schemas/                        ← JSON schemas (workspace today; item/access/... per challenge)
├── rules/                          ← declarative policy
├── scripts/                        ← validate, provision, drift (extended per challenge)
├── workspaces/                     ← Challenge 01 manifests
└── .github/
    ├── CODEOWNERS
    ├── pull_request_template.md
    └── workflows/                  ← validate.yml, provision.yml, drift.yml (+ more per challenge)
```

## Tools you'll use

| Tool | What it gives you | Used in |
|---|---|---|
| [Fabric Core MCP Server (remote)](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server) | Natural-language workspace / item / role / folder ops; RBAC + audit enforced | 00, 01, 02, 03, 04, 06 |
| [Fabric MCP Server (local)](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/pro-dev-local/overview-local-mcp-server) | Offline API docs, OneLake operations, item scaffolding, best-practices retrieval | 00, 02, 05, 08 |
| [Skills for Fabric](https://github.com/microsoft/skills-for-fabric) | Workload-specific authoring / consumption / operations skills (Spark, SQLDW, Eventhouse, Power BI, Dataflows, Eventstream, Activator, medallion) | 02, 05, 07 |
| GitHub Actions + OIDC | Identity-federated provisioning, validation, drift, audit, promotion | every challenge |
| Microsoft Purview | Sensitivity labels, DLP, audit, agent governance | 03, 06, 07 |

## Contributing back

Found a gap or a better idea? Open a PR against `challenges/`. Every challenge should
demonstrate at least one MCP server **and** one Skill, and every change to policy or
schemas needs a CODEOWNERS review.

## License

License: TBD — to be added before the first public release.
