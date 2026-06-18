# Fabric MCP servers and Skills for Fabric

This document is the **shared reference** for every challenge that uses
Fabric MCP servers or Skills for Fabric. Read it once during Challenge 00,
then come back to specific sections as needed.

## TL;DR

- **Fabric Core MCP Server (remote)** — your *runtime*. Lets agents do things in
  your tenant: list workspaces, create items, change roles, search the catalog.
  Audit-logged. RBAC-enforced.
- **Fabric MCP Server (local)** — your *toolbox*. Gives agents API specs, best
  practices, and OneLake file/table ops without burning tenant calls.
- **Skills for Fabric** — your *templates*. Pre-baked, opinionated workflows
  per workload (Spark, SQLDW, Eventhouse, Power BI, Dataflows, Eventstream,
  Activator, medallion, migrations).

You will use **all three** during the hackathon. They compose; they do not replace each other.

---

## Fabric Core MCP Server (remote)

### What it is

A remote MCP endpoint at `https://api.fabric.microsoft.com/v1/mcp/core` that
exposes Fabric's REST surface as typed MCP tools. You authenticate via OAuth 2.0
with Microsoft Entra ID; every call respects your Fabric RBAC and lands in the
Fabric audit log under **your** identity.

### Available tools (today)

| Tool | What it does |
|---|---|
| `search_catalog` | OneLake catalog search across workspaces |
| `list_workspaces`, `get_workspace`, `create_workspace`, `update_workspace`, `delete_workspace` | Workspace CRUD |
| `list_workspace_roles`, `get_workspace_role`, `add_workspace_role`, `update_workspace_role`, `delete_workspace_role` | RBAC management |
| `list_items`, `get_item`, `create_item`, `update_item`, `delete_item` | Item CRUD |
| `get_item_definition`, `update_item_definition` | Item schema/definition |
| `bulk_move_items`, `create_folder`, `list_folders`, `get_folder`, `update_folder`, `delete_folder`, `move_folder` | Folder organization |
| `list_capacities` | Capacity discovery |
| `get_operation_state`, `get_operation_result` | Long-running operation tracking |
| `get_knowledge` | Built-in guidance / best practices per item type |

> Tool list will grow over time. Always run `list_workspaces` once after install
> to confirm auth, then ask the agent **"what tools do you have for Fabric?"**
> to see the current surface.

### Install in VS Code

1. Open the command palette (`Ctrl/Cmd + Shift + P`).
2. **MCP: Add Server** → **HTTP**.
3. Endpoint: `https://api.fabric.microsoft.com/v1/mcp/core`
4. Name it `fabric`.
5. Complete the browser-based Entra sign-in.

### Install in GitHub Copilot CLI

```bash
gh copilot mcp add fabric \
  --url https://api.fabric.microsoft.com/v1/mcp/core \
  --transport http
```

(Replace with your CLI's idiomatic command if it differs — the endpoint is the same.)

### Smoke test prompts

```
List all my Fabric workspaces.
Show the role assignments for the workspace called "pt-nlyt-sample-ndf-dev-hello1".
What lakehouses exist in "pt-nlyt-sample-ndf-dev-hello1"?
Get the definition of the item named "CustomerData" in that workspace.
```

If any of these return `401`/`403`, re-run **MCP: Remove Server** → **MCP: Add Server**
and re-authenticate.

---

## Fabric MCP Server (local)

### What it is

An open-source MCP server that runs as a subprocess on your machine. It does
not call the tenant for documentation — everything ships with the package.
It also exposes OneLake file/table operations that *do* hit the service.

Repository: <https://github.com/microsoft/mcp/tree/main/servers/Fabric.Mcp.Server>

### Tool categories

**API documentation & best practices** (offline):

- `docs_workloads` — list workload types with public APIs
- `docs_workload-api-spec` — fetch OpenAPI for a specific workload
- `docs_platform-api-spec` — core Fabric platform APIs
- `docs_item-definitions` — JSON schemas for item definitions
- `docs_best-practices` — guidance per topic (throttling, naming, etc.)
- `docs_api-examples` — example request/response payloads

**OneLake data operations** (hits service):

- `onelake_list_workspaces`, `onelake_list_files`
- `onelake_download_file`, `onelake_upload_file`
- table listing and basic SQL/KQL query helpers (varies by release)

**Core Fabric operations** (subset; prefer the remote Core MCP for these in production):

- `core_create-item` and friends

### Install in VS Code (recommended)

1. Install the **Microsoft Fabric** VS Code extension.
2. Open the command palette → **Fabric: Enable MCP server**.
3. The extension starts the local server and registers it with Copilot Chat.

### Install via `npx`

```bash
npx @microsoft/fabric-mcp-server
```

Add the resulting command to your MCP client's config as a `stdio` server.

### When to reach for local vs. core

| You want to… | Use |
|---|---|
| List or change resources in the tenant | **Core (remote)** |
| Look up an API shape, schema, or best practice | **Local** |
| Pull a file out of OneLake to read locally | **Local** |
| Bulk-edit role assignments | **Core (remote)** |
| Search the OneLake catalog | **Core (remote)** |
| Scaffold a notebook from an OpenAPI sample | **Local** |

---

## Skills for Fabric

### What they are

Reusable, workload-specific **skills** (a.k.a. "agent skills") that teach an AI
agent to author, query, operate, and govern a Fabric workload. They ship as
versioned packages from the open-source repo and are invoked by name from your
agent.

Repository: <https://github.com/microsoft/skills-for-fabric>

### Skills used in this hackathon

| Skill | Type | Used in |
|---|---|---|
| `spark-authoring-cli` | Authoring | Challenge 02, 05 |
| `spark-consumption-cli` | Consumption | Challenge 05 |
| `spark-operations-cli` | Operations | Challenge 05 |
| `sqldw-authoring-cli` | Authoring | Challenge 02, 08 |
| `sqldw-consumption-cli` | Consumption | Challenge 08 |
| `sqldw-operations-cli` | Operations | Challenge 08 |
| `eventhouse-authoring-cli` | Authoring | Challenge 07 |
| `eventhouse-consumption-cli` | Consumption | Challenge 07 |
| `eventstream-authoring-cli` | Authoring | Challenge 07 |
| `eventstream-consumption-cli` | Consumption | Challenge 07 |
| `powerbi-authoring-cli` | Authoring | Challenge 07 |
| `powerbi-consumption-cli` | Consumption | Challenge 07 |
| `dataflows-authoring-cli` | Authoring | Stretch |
| `activator-authoring-cli` | Authoring | Challenge 07 |
| `e2e-medallion-architecture` | Composite | Challenge 05 |

### Install

Skills are invoked through agents that support them (GitHub Copilot Chat,
Copilot CLI, etc.). Install on demand from the catalog:

```bash
# Example — exact command depends on your agent host
copilot skill install eventhouse-authoring-cli
copilot skill install e2e-medallion-architecture
```

In VS Code with Copilot Chat, type `@` and then start typing the skill name to
discover and install it.

### Calling a skill

Inside a chat session:

```
@eventhouse-authoring-cli  Create a KQL database "gov_audit" in workspace
  "dev-plt-audit" with tables "pr_events" and "fabric_activity".
```

The skill decides which tools (often a mix of the Core MCP + Fabric REST)
to call to accomplish the request, and reports back what it did.

---

## How MCP + Skills fit your governance plane

Mental model:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Author / reviewer                                                    │
│  • opens PR with a manifest                                          │
│  • asks the agent (via MCP) to verify tenant state matches manifest  │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Agent in VS Code / Copilot CLI                                       │
│  • picks the right MCP tool or Skill                                 │
│  • reads tenant state, scaffolds items, edits YAML manifest          │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ GitHub: validate.yml runs schema + policy checks on the PR           │
│         provision.yml applies the manifest via OIDC + Fabric REST    │
│         drift.yml reconciles tenant state nightly                    │
└──────────────────────────────────────────────────────────────────────┘
```

The agent is the **fast path** for one-off exploration and authoring. The PRs
and workflows are the **governed path** for any change that lands in the tenant.

## Further reading

- [Fabric MCP Servers overview](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/what-is-fabric-mcp-server)
- [Fabric Core MCP Server tools reference](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Fabric local MCP Server tools reference](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/pro-dev-local/tools-local-mcp-server)
- [Skills for Fabric (GitHub)](https://github.com/microsoft/skills-for-fabric)
- [Fabric REST API reference](https://learn.microsoft.com/rest/api/fabric/articles/)
