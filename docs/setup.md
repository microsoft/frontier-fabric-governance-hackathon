# One-time Setup Runbook

This runbook captures the **manual** steps required to make this repo functional
in your tenant. The automation in this repo handles GitHub-side wiring; some
Fabric tenant settings require Fabric Admin Portal access.

## Capture your tenant bootstrap values

| Item | Value |
|---|---|
| Tenant ID | `<your-tenant-id>` |
| Provisioner App | `gh-fabric-workspace-provisioner` (or your chosen app name) |
| App (client) ID | `<your-app-client-id>` |
| SPN object ID | `<your-spn-object-id>` |
| Security group | `sg-fabric-workspace-provisioner` (or your chosen group name) |
| Security group ID | `<your-security-group-id>` |
| Capacity (initial) | `<capacity-name>` (`<sku>`, `<region>`) |

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

## Capacity admin

Add the SPN object ID to the target capacity administrators via ARM or the
Azure/Fabric portal. Verify in Azure Portal → Microsoft Fabric → Capacities
→ Admins.

## GitHub repo configuration

- Repo variables: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `FABRIC_CAPACITY_ID`,
  `DEFAULT_OWNER_UPN`, `LIVE_CHECKS`.
- `production` environment with at least one required reviewer.
- Branch protection on `main`: required PR review, required `validate` check,
  CODEOWNERS review.

## Day-1 smoke test

1. Branch from `main`.
2. Add `workspaces/pt-nlyt-sample-ndf-dev-hello1.yaml` (sample provided).
3. Open PR — `validate` workflow should post a sticky comment with results.
4. Approve & merge — `provision` workflow runs (after manual environment approval).
5. Workspace appears in Fabric.
