# Fabric Workspace Provisioner — Copilot Studio agent (Function-App-free)

A **Microsoft Copilot Studio** authoring of the Fabric Workspace Provisioner
that uses **only native Power Platform + GitHub primitives**:

```
User in Teams / Power Apps / Web
        │
        ▼
Copilot Studio agent  (this folder)
        │
        ├──► InvokeFlow → "FWG - Get Policy"            (Power Automate)
        │                       └─ GitHub: Get file content (rules/policy.yaml)
        │
        └──► InvokeFlow → "FWG - Submit Workspace Request" (Power Automate)
                                ├─ GitHub: Create a reference  (new branch)
                                ├─ GitHub: Create or update file content
                                │     (workspaces/<name>.yaml)
                                └─ GitHub: Create a pull request
                                          │
                                          ▼
                          .github/workflows/validate.yml  (the deterministic gate)
                                          │
                                          ▼
                       Reviewer approval → merge → provision.yml
```

**Nothing in the request path runs in Azure.** The `api/`, `infra/`, and
`agent/appPackage/` folders are **legacy** for this option — see "Migration"
at the bottom of this README to retire them safely.

## Why this design

| Concern | Old design (Function App) | This design (Power Automate native) |
| --- | --- | --- |
| Compute we run | Azure Function (Python v2) + App Service Plan | None |
| Code we maintain | `api/`, `infra/`, OpenAPI plugin | A few flow steps in the portal |
| GitHub credential storage | Function App settings + Key Vault | Power Automate connection (OAuth) or Key Vault via PA connector |
| Validation source of truth | Function App rules engine + CI workflow (drift risk) | CI workflow only — no drift |
| Pre-flight UX | HTTP call to `/api/validate` | Power Fx in topic, instant |
| Cold start | ~1–3 s on Function App | ~0 s |
| Tenant isolation | Hosted in your Azure subscription | Hosted in your Power Platform environment |

The single deterministic policy gate is `.github/workflows/validate.yml`
running `scripts/validate.py`. The Copilot Studio agent only does
optimistic Power Fx pre-flight (regex / enum) for fast user feedback.

## Native Copilot Studio capabilities used (and the ones available next)

Currently wired up:

1. **Power Automate cloud flow with the GitHub connector** — replaces
   `/api/submit` (and `/api/policy`).
2. **Power Fx in topics** — replaces `/api/validate`.
3. **Knowledge sources (FileKnowledgeSource)** — grounded answers about
   the approval process and the `why` behind the policy.
4. **Conversation-scoped variables (`Global.PolicyCache`)** — cache the
   allow-lists once per session.

Easy follow-ons (skipped for now to keep the scaffold small — see
"Optional enhancements" below):

5. **Approvals connector** — Teams approval before the PR is opened.
6. **Office 365 Users connector** — auto-fill the requester's email into
   `owners[0]` so users only have to type their teammates.
7. **Microsoft Teams connector** — post the PR URL into a governance
   channel after submission.
8. **Adaptive Cards** — show the parsed manifest back to the user with
   confirm / cancel before submission.
9. **Authenticated agent + Microsoft Entra SSO** — capture
   `User.PrincipalName` instead of asking for `requesterEmail`.

## Prerequisites

- VS Code extension `ms-copilotstudio.vscode-copilotstudio` (already
  installed)
- The `skills-for-copilot-studio` plugin under `~/.copilot/installed-plugins/`
- A Microsoft Copilot Studio environment in your tenant
- A GitHub identity with `contents:write` and `pull-requests:write` on the
  governance repo. Two acceptable forms:
  - **A dedicated bot user** with a fine-scoped PAT (rotated quarterly).
  - **A GitHub App** installed on the org and authenticated via the
    Power Automate GitHub connector's OAuth (preferred where supported).

## Repository layout (this folder)

```
agent/copilotstudio/
├── README.md                              # This runbook
├── agent.mcs.yml                          # Display name, instructions, starters
├── settings.mcs.yml                       # Stub — replaced by portal pull
├── topics/
│   ├── greeting.topic.mcs.yml             # OnConversationStart welcome
│   ├── show-policy.topic.mcs.yml          # → FWG - Get Policy flow
│   ├── request-workspace.topic.mcs.yml    # 13-field slot-fill, Power Fx pre-flight, → FWG - Submit Workspace Request flow
│   └── knowledge-search.topic.mcs.yml     # OnUnknownIntent generative answers
├── actions/
│   ├── get-policy.action.mcs.yml          # InvokeFlowTaskAction stub
│   └── submit-workspace.action.mcs.yml    # InvokeFlowTaskAction stub
├── knowledge/
│   └── governance-docs.knowledge.mcs.yml  # FileKnowledgeSource stub
└── variables/
    └── policy-cache.variable.mcs.yml      # Conversation-scoped cache
```

The `*.mcs.yml` files are **scaffolds**. The flow IDs and connection
references are filled in only after you create the corresponding objects
in the portal and run the plugin's `pull`.

Search for `<TODO-` to find the placeholders.

## End-to-end wire-up procedure

The plugin model is **portal-first**: create the agent and the two cloud
flows in the Power Platform portal, then pull / push YAML.

### 1. Create the agent shell

In Copilot Studio (`copilotstudio.microsoft.com`):

1. **+ Create → New agent → Skip to configure**.
2. Name: `Fabric Workspace Provisioner`.
3. Copy `agent.mcs.yml`'s `instructions` and `starters` into the portal.
4. **Save**. You now have an empty agent with a real `schemaName`.

### 2. Build "Flow A: FWG - Get Policy"

In Power Automate (`make.powerautomate.com` → **+ Create → Instant cloud
flow → When an agent calls the flow**):

| Step | Action | Configuration |
| --- | --- | --- |
| Trigger | When an agent calls the flow | No inputs |
| 1 | GitHub → **Get file content** | Owner: `<your-org>`, Repo: `<governance-repo>`, Path: `rules/policy.yaml`, Branch: `main` |
| 2 | Data Operations → **Compose** (`policyText`) | Inputs: `body('Get_file_content')` |
| 3 | Built-in → **Initialize variable** (`regions`, string) | `<extract `regions:` block as comma list — see note below>` |
| 4 | Built-in → **Initialize variable** (`capacities`, string) | extract `capacities:` block |
| 5 | Built-in → **Initialize variable** (`approvedDomains`, string) | extract `approvedDomains:` block |
| 6 | Built-in → **Initialize variable** (`approvedSubDomains`, string) | extract `approvedSubDomains:` block |
| 7 | Built-in → **Initialize variable** (`policyVersion`, string) | extract `version:` field |
| 8 | Respond to the agent | Outputs: `regions`, `capacities`, `approvedDomains`, `approvedSubDomains`, `policyVersion` (all `String`) |

**YAML-parsing note**: Power Automate has no native YAML parser. Easiest
options, in order of preference:

- **Keep `rules/policy.yaml` simple** (it already is — flat keys, lists of
  strings) and use a single `Filter array` + `string()` + `split()` chain
  per field. Works for the current schema.
- **Maintain `rules/policy.json`** alongside `rules/policy.yaml`, generated
  by CI on push to `main`. Then the flow uses `Parse JSON` directly.
- **Run an Azure Logic Apps Standard inline JS step** inside the flow to
  do a real YAML→JSON conversion. Heavier; only worth it if you grow the
  policy schema.

### 3. Build "Flow B: FWG - Submit Workspace Request"

Same trigger ("When an agent calls the flow") with these inputs:

| Name | Type |
| --- | --- |
| `workspaceName` | Text |
| `yamlBody` | Text |
| `requesterEmail` | Text |

**Important**: agent flow inputs/outputs are limited to **String, Number,
and Boolean** ([reference](https://learn.microsoft.com/microsoft-copilot-studio/advanced-flow-input-output)).
Pass complex data as a JSON-encoded string and `Parse JSON` inside the
flow if needed.

| Step | Action | Configuration |
| --- | --- | --- |
| 1 | Compose `branch` | `request/<workspaceName>-utcNow('yyyyMMddHHmmss')` |
| 2 | GitHub → **Get a reference** | `heads/main` → captures main SHA |
| 3 | GitHub → **Create a reference** | Ref: `refs/heads/<branch>`, SHA from step 2 |
| 4 | Data Operations → **Compose** `expandedYaml` | Build the final YAML body. Take `yamlBody` and substitute the trailing `ownersJsonRaw: '…'` line with a proper YAML `owners:` block by `Parse JSON` on the inner string + `Select` to YAML lines. (See `docs/copilot-studio-agent.md` for the exact expression.) |
| 5 | GitHub → **Create or update file content** | Path: `workspaces/<workspaceName>.yaml`, Branch: `<branch>`, Content: `expandedYaml`, Commit message: `Add workspace request <workspaceName>` |
| 6 | GitHub → **Create a pull request** | Base: `main`, Head: `<branch>`, Title: `Request workspace <workspaceName>`, Body: `Submitted via Copilot Studio by <requesterEmail>.` |
| 7 | Respond to the agent | `pullRequestUrl`, `pullRequestNumber` (cast to String), `branch`, `submitted`=`true`, `error`=`""` |

Wrap steps 2-6 in a **Try-Catch (Scope + Configure run after)** so a
failure routes to a "Respond" with `submitted=false` and the GitHub
error details in `error`.

### 4. Add both flows to the agent

In Copilot Studio → agent → **Actions** → **+ Add an action**:

1. Pick **Flow** → **FWG - Get Policy** → Save.
2. Repeat for **FWG - Submit Workspace Request**.

For each, set the display name and AI description from the matching YAML
in `actions/`.

### 5. Pull the agent locally

```
/copilot-studio:copilot-studio-manage pull
```

The two `actions/*.action.mcs.yml` files are now overwritten with the
portal-generated versions, including real `flowId` GUIDs.

### 6. Merge in the topics + instructions from this folder

Replace the empty topics with the ones from `topics/` (overwriting the
pulled blanks). The two `InvokeFlowAction` blocks have `<TODO-flowId-…>`
placeholders — substitute the real `flowId` GUIDs from step 5.

Push:

```
/copilot-studio:copilot-studio-manage push
```

### 7. Add the knowledge source

In the portal **Knowledge** tab → **+ Add knowledge** → **Files**, upload:

- `rules/policy.yaml`
- `docs/setup.md`
- `docs/workspace-approval-workflow.md`
- `schemas/workspace.schema.json`

Pull again to materialize `knowledge/governance-docs.knowledge.mcs.yml`
with the real Dataverse file IDs.

### 8. Test

```
/copilot-studio:copilot-studio-test
```

Cover at minimum:

- "What regions are allowed?" → calls **FWG - Get Policy**, returns the
  current `rules/policy.yaml` allow-lists.
- "Request a new workspace" with a deliberately invalid `costCenter` →
  Power Fx pre-flight blocks before the flow is called.
- A fully valid request → calls **FWG - Submit Workspace Request**,
  returns a real PR URL.

## Optional enhancements

Drop in any of these without touching the existing flows:

| Goal | How |
| --- | --- |
| Pre-PR approval in Teams | Add an **Approvals → Start and wait for an approval** step at the top of Flow B. Reject branch → `submitted=false`, `error="Rejected by <approver>"`. |
| Auto-fill `owners[0]` with the requester | Enable **Authenticated agent (Microsoft Entra)**, drop the `q_owners_*` question, build owners from `User.PrincipalName` + `User.DisplayName` in the Power Fx YAML build. |
| Post PR URL to a governance Teams channel | Add a **Teams → Post message in chat or channel** step at the end of Flow B. |
| Confirm/cancel adaptive card | Replace the final `SendActivity` in `request-workspace.topic` with an `AdaptiveCardAction` that posts the parsed manifest and gates the flow call on the user's confirm. |
| Lookup manager / department | Add an **Office 365 Users → Get manager (V2)** step in Flow B to enrich the PR body with org context. |

## Migration: retiring the Function App and the M365 declarative agent

The Function App at `https://fwg-func-rynra7bb2ogjk.azurewebsites.net`
and `agent/appPackage/` (M365 declarative agent) are now **legacy**.
Recommended order:

1. Deploy the Copilot Studio agent (steps 1-8 above) and pilot it with
   one team for a week.
2. Confirm `validate.yml` is catching all the same blocking findings
   the old `/api/validate` did. (It should — same `scripts/validate.py`.)
3. Decide whether to keep the M365 declarative agent path:
   - **Keep both**: the Function App stays. Both UIs reach the same PR.
   - **Drop M365**: delete `agent/appPackage/`, then run
     `terraform destroy` in `infra/terraform/` (or its Bicep equivalent).
     The compute, the OpenAPI plugin, and the GitHub App private-key
     wiring all go away. The governance repo is unchanged.
4. Update top-level `README.md` "Architecture" to remove Option A if
   you dropped M365.

The CI workflows (`.github/workflows/validate.yml`,
`.github/workflows/provision.yml`) and the rules engine
(`scripts/validate.py`, `rules/policy.yaml`) are untouched by any
of this — they remain the canonical governance contract.
