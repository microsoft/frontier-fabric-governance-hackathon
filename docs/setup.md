# One-time Setup Runbook

This runbook captures the **manual** steps required to make this repo functional
in your tenant. The automation in this repo handles GitHub-side wiring; some
Fabric tenant settings require Fabric Admin Portal access.

## Identity already provisioned for this tenant

| Item                   | Value |
|------------------------|-------|
| Tenant ID              | `6cf3d520-2c8c-4e6f-b4a7-54827eac42be` |
| Provisioner App        | `gh-fabric-workspace-provisioner` |
| App (client) ID        | `ad57fd37-192d-41b0-ad74-73ce420f11bc` |
| SPN object ID          | `cac92145-75da-4a17-839f-e97c6f552247` |
| Security group         | `sg-fabric-workspace-provisioner` |
| Security group ID      | `4add5496-18af-4d7b-b095-58eba1fa2dc3` |
| Capacity (initial)     | `frteixfabriccp1` (F2, northeurope) |

## Required Fabric Admin Portal settings

Go to **Fabric Admin Portal → Tenant settings**:

1. **Service principals can use Fabric APIs** → *Enabled* for the security group
   `sg-fabric-workspace-provisioner`.
2. **Service principals can access read-only admin APIs** → *Enabled* for the same group.
3. **Service principals can access admin APIs used for updates** → *Enabled* for the same group.
4. **Create workspaces** → *Restrict to specific security groups* → add
   `sg-fabric-workspace-provisioner` (and any human admin group you want to
   keep able to create out-of-band).
5. **Allow service principals to create and use profiles** (if you plan to use
   profiles) → *Enabled*.

> Tenant setting changes can take **up to 15 minutes** to propagate.

## Make the SPN a Fabric Administrator (for admin APIs)

Microsoft 365 Admin Center → Roles → assign **Fabric Administrator** to the SPN
`gh-fabric-workspace-provisioner`. (Required for: list-all-workspaces admin
endpoints, domain assignment, sensitivity-label operations.)

## Capacity admin (already done by automation)

The SPN object ID has been added to capacity `frteixfabriccp1` administrators
via ARM. Verify in Azure Portal → Microsoft Fabric → Capacities → Admins.

## GitHub repo configuration (already done by automation)

- Repo variables: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `FABRIC_CAPACITY_ID`,
  `DEFAULT_OWNER_UPN`, `LIVE_CHECKS`.
- `production` environment with required reviewer (you).
- Branch protection on `main`: required PR review, required `validate` check,
  CODEOWNERS review.

## Day-1 smoke test

1. Branch from `main`.
2. Add `workspaces/dev-plt-sample-hello.yaml` (sample provided).
3. Open PR — `validate` workflow should post a sticky comment with results.
4. Approve & merge — `provision` workflow runs (after manual environment approval).
5. Workspace appears in Fabric.
