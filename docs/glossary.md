# Glossary

Quick reference for terms used across the hackathon.

## Microsoft Fabric

- **Workspace** — the unit of collaboration and access control in Fabric. Hosts items.
- **Item** — anything inside a workspace: lakehouse, warehouse, notebook, semantic model,
  pipeline, eventhouse, KQL database, eventstream, reflex/activator, dataflow, mirror, etc.
- **Capacity** — the compute/SKU (F2, F4, F64…) backing one or more workspaces. Required
  for almost all Fabric workloads. Capacity admins are distinct from workspace admins.
- **Domain / subdomain** — a tenant-wide grouping of workspaces for governance and
  discoverability. Managed via the Fabric admin portal or admin API.
- **OneLake** — the single, tenant-wide data lake underneath Fabric. Items that contain
  data (lakehouses, warehouses, KQL DBs) are projections over OneLake.
- **OneLake catalog** — searchable index of items across the tenant.
- **Tenant setting** — a Fabric admin portal toggle that scopes a capability to all users,
  a security group, or none.
- **Endorsement** — Promoted or Certified label on an item that signals trust.
- **Sensitivity label** — Microsoft Purview MIP label (Public, General, Confidential,
  Highly Confidential, plus sublabels). Drives encryption, access, and visibility.
- **Capacity admin** — granted per-capacity; required for `assignToCapacity` calls.
- **Fabric Administrator** — tenant-wide role; required for admin APIs (domains,
  list-all-workspaces, sensitivity label apply).
- **Deployment pipeline** — Fabric-native promotion mechanism between dev / test / prod
  workspaces.
- **Fabric Data Agent** — a configurable, governed Q&A agent that queries lakehouses,
  warehouses, semantic models, KQL DBs or ontologies on behalf of users.

## Identity

- **SPN / Service principal** — the machine identity of an Entra app registration in this
  tenant. The hackathon uses one SPN (`gh-fabric-workspace-provisioner`).
- **Federated credential** — Entra-side configuration that trusts a specific external
  issuer (here: GitHub Actions) + subject (here: a repo + branch / environment).
- **OIDC** — OpenID Connect; the protocol used by GitHub to mint a short-lived token
  that Entra trades for an Entra access token.
- **CODEOWNERS** — GitHub file listing who must approve changes to which paths.
- **Branch protection** — GitHub rule set on `main` requiring PR review, status checks,
  signed commits, etc.
- **GitHub environment** — a deployment target with optional required reviewers, wait
  timers, and secrets. The hackathon uses `production` as the manual-approval gate.

## Governance / Purview

- **Drift** — divergence between declared (manifest) state and live (tenant) state.
- **Unmanaged** — a tenant resource with no manifest in the repo.
- **Orphan manifest** — a manifest in the repo whose tenant resource was deleted out of band.
- **Adoption** — bringing an existing tenant resource under repo management by writing
  a manifest and applying the `managed-by:` marker.
- **DLP** — Data Loss Prevention; Purview policies that block sensitive data movement.
- **DSPM** — Data Security Posture Management; Purview signals about risk in data sources.
- **Audit log** — Fabric + Purview record of every action with actor identity.

## MCP / Skills

- **MCP** — Model Context Protocol; a standard for AI agents to call typed tools.
- **MCP server** — process exposing tools to MCP clients. May be remote (Fabric Core)
  or local (Fabric local MCP).
- **MCP tool** — a single typed operation an agent can invoke.
- **Skill (for Fabric)** — a packaged set of agent instructions + tool calls that
  solves a workload-specific task (e.g., "create a KQL database with these tables").

## This repo

- **Manifest** — a YAML file under `workspaces/`, `items/`, `domains/`, etc. that
  declares the desired state of one resource.
- **Policy** — `rules/policy.yaml`; declarative rules the validator enforces.
- **Validator** — `scripts/validate.py`; schema + policy checker that runs in PRs.
- **Provisioner** — `scripts/provision.py`; idempotent applier that runs on merge.
- **Drift detector** — `scripts/drift.py`; nightly reconciliation between repo and tenant.
- **Marker** — `managed-by:gh:<org>/<repo>@<sha>` string written into a workspace
  description so drift can identify repo-managed resources.
