# Challenge 00 — Tenant, identity, and tooling setup

> **Outcome:** a hackathon-ready Fabric tenant, a service-principal identity wired to
> GitHub via OIDC, and a dev box with the Fabric MCP servers and at least one Skill
> for Fabric installed and verified.

## Why this challenge exists

Every other challenge assumes the same identity model: a single service principal
authenticated via OIDC from GitHub Actions, and a participant authenticated via Entra
ID from VS Code. Get that right once here and the rest of the hackathon is just
choosing which manifests to write.

## Learning objectives

By the end of this challenge you will be able to:

1. Explain the identity chain from a GitHub PR to a Fabric API call.
2. Toggle the Fabric tenant settings that allow service principals to act on the tenant.
3. Install and authenticate the **Fabric Core MCP Server** (remote) and the
   **Fabric MCP Server (local)**.
4. Install at least one **Skill for Fabric** and call it from your agent.
5. Confirm your environment is healthy with a documented smoke test.

## Prerequisites

- A Microsoft Fabric tenant where you (or a partner) have **Fabric Administrator**
  rights.
- A Microsoft Entra ID tenant where you can create app registrations and security
  groups (or a tenant admin to do the bootstrap for you).
- A GitHub organization with permission to create repos, environments,
  CODEOWNERS-protected branches, and federated credentials.
- At least one **Fabric capacity** (F2 or higher). F4+ recommended if you intend to
  do Challenge 05 (medallion) or 07 (audit observability).
- Local tools: **VS Code** (latest) + **GitHub Copilot** extension, **or**
  **GitHub Copilot CLI**; **Python 3.12+**; **Git**; **Azure CLI** (`az`).

## Tasks

### Task 1 — Create the SPN, security group, and federated credentials

Follow [`docs/setup.md`](../../docs/setup.md) end-to-end. The result should match the
"Identity already provisioned for this tenant" table in that doc:

- App registration: `gh-fabric-workspace-provisioner`
- Security group: `sg-fabric-workspace-provisioner`
- Federated credentials for `pull_request`, `refs/heads/main`, `environment:production`

If you are using a shared sandbox tenant prepared by event organizers, capture the
GUIDs that were provisioned for you and record them in `docs/setup.md` (or your
team's notes).

### Task 2 — Enable tenant settings

In **Fabric Admin Portal → Tenant settings**, scope the following to
`sg-fabric-workspace-provisioner`:

1. Service principals can use Fabric APIs
2. Service principals can access read-only admin APIs
3. Service principals can access admin APIs used for updates
4. Create workspaces (restrict to the security group)

Wait **up to 15 minutes** for propagation.

### Task 3 — Make the SPN a Fabric Administrator and Capacity Admin

- Microsoft 365 Admin Center → Roles → assign **Fabric Administrator** to the SPN.
- Azure Portal → your Fabric capacity → **Admins** → add the SPN's object ID.

### Task 4 — Configure the GitHub repo

In your fork of this repo:

1. **Variables**: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `FABRIC_CAPACITY_ID`,
   `DEFAULT_OWNER_UPN`, `LIVE_CHECKS=true`.
2. **Environment**: create `production` with at least one required reviewer.
3. **Branch protection** on `main`: require PR review, require the `validate`
   status check, require CODEOWNERS review, restrict pushes to GitHub Actions.

### Task 5 — Install the Fabric Core MCP Server (remote)

In VS Code:

1. Command palette → **MCP: Add Server** → **HTTP**.
2. URL: `https://api.fabric.microsoft.com/v1/mcp/core`
3. Name: `fabric`
4. Authenticate in the browser.

In Copilot CLI:

```bash
gh copilot mcp add fabric \
  --url https://api.fabric.microsoft.com/v1/mcp/core \
  --transport http
```

### Task 6 — Install the Fabric MCP Server (local)

1. Install the **Microsoft Fabric** VS Code extension.
2. Command palette → **Fabric: Enable MCP server**.
3. Confirm the agent sees the new tools by asking
   *"What `docs_*` tools do you have available?"*

### Task 7 — Install at least one Skill for Fabric

Pick one and install it:

```bash
copilot skill install spark-authoring-cli
# or
copilot skill install eventhouse-authoring-cli
```

Confirm it appears in your agent's skill list.

### Task 8 — Run the smoke test

Ask the agent, one by one:

| Prompt | Expected behavior |
|---|---|
| `List all my Fabric workspaces.` | The agent calls `list_workspaces` and returns a JSON array (possibly empty). |
| `Which Fabric workload types have API specs available?` | The agent calls `docs_workloads` and lists ≥ 6 workload types. |
| `Show me the OpenAPI spec for "Lakehouse".` | The agent calls `docs_workload-api-spec` and returns the spec. |
| `What capacities can I see in my tenant?` | The agent calls `list_capacities` and returns at least one capacity. |

Capture the agent's responses in your team notes.

## Success criteria

- [ ] The four MCP/Skills smoke-test prompts above each return a useful answer.
- [ ] The federated credential for `pull_request` works — you can open a draft PR
      against your fork and the `validate` workflow runs without auth errors
      (it can fail on the manifest, that's fine).
- [ ] You can describe the identity chain from PR to Fabric REST API in 60 seconds.

## Stretch goals

- Wire a second Skill (e.g., `eventhouse-authoring-cli` in addition to `spark-authoring-cli`)
  and demonstrate the agent picking between them based on intent.
- Replace the hosted runner with the **self-hosted runner** under
  `~/actions-runner-fabric-gov`. Verify `runs-on: [self-hosted, fabric-gov]` works
  by re-running a `validate` job.
- Configure **Microsoft Graph MCP** so email-to-objectId resolution works for role
  assignment prompts.

## MCP tips

- The remote Fabric Core MCP **always** uses your Entra identity, not the SPN's.
  When you "verify your work" via the agent you're confirming what *you* can see,
  not what the SPN sees. For SPN-side verification, run the workflow.

## Skills tips

- Each Skill ships its own README. Open it from the [Skills for Fabric
  repository](https://github.com/microsoft/skills-for-fabric) before you call it
  for the first time so you know which prompts it understands.

## References

- [`docs/setup.md`](../../docs/setup.md)
- [`docs/mcp-and-skills.md`](../../docs/mcp-and-skills.md)
- [`docs/identity-model.md`](../../docs/identity-model.md)
- [`docs/troubleshooting.md`](../../docs/troubleshooting.md)
- [Workload identity federation for GitHub Actions](https://learn.microsoft.com/azure/active-directory/workload-identities/workload-identity-federation-create-trust)
