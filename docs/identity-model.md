# Identity model

This document describes how identities are wired together so that a service
principal can act on the Fabric tenant **only when** a human-reviewed PR has
been merged. The same model is reused by every challenge in the hackathon.

## Actors

| Actor | What it is | Why it exists |
|---|---|---|
| **Hackathon participant** | Human with a Microsoft Entra ID account in the tenant | Opens PRs, reviews PRs, asks the agent questions |
| **`gh-fabric-workspace-provisioner`** | Entra app registration (service principal) | The *only* identity allowed to write to Fabric in production |
| **`sg-fabric-workspace-provisioner`** | Entra security group containing the SPN | The unit of grant for Fabric tenant settings |
| **GitHub Actions runner** | Self-hosted or hosted runner | Executes validate/provision/drift workflows |
| **Reviewer (CODEOWNERS)** | Human or team listed in `.github/CODEOWNERS` | Required PR approver before merge |
| **Environment approver** | Human(s) on the GitHub `production` environment | Manual gate between merge and provision |

## Trust chain

```
                ┌──────────────────────┐
                │ Participant          │
                └──────────┬───────────┘
                           │ opens / approves PR
                           ▼
                ┌──────────────────────┐
                │ GitHub Actions       │
                │ (validate / provision)│
                └──────────┬───────────┘
                           │ federated OIDC token
                           ▼
                ┌──────────────────────┐
                │ Microsoft Entra ID   │
                │ token exchange       │
                └──────────┬───────────┘
                           │ Bearer access token
                           ▼
                ┌──────────────────────┐
                │ Fabric / Power BI    │
                │ REST APIs            │
                └──────────────────────┘
```

No long-lived secrets exist anywhere in the chain. The SPN never holds a client
secret; GitHub trades its short-lived OIDC token for a Fabric access token at
runtime.

## Federated credential design

The SPN has **three** federated credentials, one per allowed GitHub subject:

| Purpose | Subject claim | When it fires |
|---|---|---|
| Read-only checks during PR | `repo:<org>/<repo>:pull_request` | `validate.yml` on `pull_request` |
| Drift detection | `repo:<org>/<repo>:ref:refs/heads/main` | nightly `drift.yml` |
| Write to Fabric in prod | `repo:<org>/<repo>:environment:production` | `provision.yml` only after the environment is approved |

Audience is always `api://AzureADTokenExchange`.

## Required Fabric tenant settings

These are toggled in **Fabric Admin Portal → Tenant settings** and scoped to
the security group `sg-fabric-workspace-provisioner`. Full details with screenshots
are in [`docs/setup.md`](setup.md).

- **Service principals can use Fabric APIs**
- **Service principals can access read-only admin APIs**
- **Service principals can access admin APIs used for updates**
- **Create workspaces** — restrict to `sg-fabric-workspace-provisioner` (+ break-glass admin)
- **Allow service principals to create and use profiles** (only if your scenario needs it)

## Roles assigned to the SPN

| Role | Granted at | Used for |
|---|---|---|
| Fabric Administrator | Microsoft 365 Admin Center → Roles | Domain assignment, admin APIs, tenant-wide listings |
| Capacity Admin | Each in-scope Fabric capacity | `assignToCapacity`, capacity scale ops |
| Member of MIP label publishing scope | Microsoft Purview → Information Protection | Applying sensitivity labels via API |

## What participants *don't* get

- Direct Fabric Administrator role.
- Owner of the SPN.
- Ability to push to `main` (branch-protected; only Actions can push).
- Ability to bypass the `production` environment gate.

## Day-2 changes you'll do during the hackathon

Each challenge that introduces a new resource type (items, domains, agents…)
extends the SPN's permissions, *not* by adding raw API scopes, but by:

1. Adding a new federated credential subject if it needs its own environment.
2. Adding new Fabric tenant settings to the same security group.
3. Documenting the change in the relevant challenge's `challenge.md`.

If you ever need to grant a *human* the ability to do something the SPN does,
add them to a security group that holds those grants — do not edit the SPN.

## References

- [Workload identity federation for GitHub Actions](https://learn.microsoft.com/azure/active-directory/workload-identities/workload-identity-federation-create-trust)
- [Power BI / Fabric service principals](https://learn.microsoft.com/fabric/admin/service-admin-service-principals)
- [Fabric admin role](https://learn.microsoft.com/fabric/admin/roles)
- [Microsoft Purview information protection scope](https://learn.microsoft.com/purview/sensitivity-labels)
