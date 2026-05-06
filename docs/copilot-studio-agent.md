# Fabric Workspace Provisioner — Copilot Studio agent runbook

This is the operator runbook for **Option A2**: a Microsoft Copilot Studio
agent that opens the governance pull request through Power Automate cloud
flows + the GitHub connector, with **no Azure Function App**.

The full design notes, the architecture diagram, the Power Fx pre-flight
expressions, and the file layout are in
[`../agent/copilotstudio/README.md`](../agent/copilotstudio/README.md).
This file is the short, copy-paste-friendly version for someone wiring it
up for the first time.

## What you will build

```
Copilot Studio agent
    ├── Topic: Show Policy            → Flow A: FWG - Get Policy
    ├── Topic: Request Workspace      → Flow B: FWG - Submit Workspace Request
    └── Knowledge: docs + policy.yaml (Dataverse files)
```

Two Power Automate flows, both with the **"When an agent calls the flow"**
trigger.

## Constraints to remember

1. Agent flow inputs/outputs are limited to **String / Number / Boolean**
   ([reference](https://learn.microsoft.com/microsoft-copilot-studio/advanced-flow-input-output)).
   Pass complex data as a JSON-encoded string and `Parse JSON` inside the
   flow if needed.
2. The repo's policy engine is the **only** source of truth.
   `.github/workflows/validate.yml` runs `scripts/validate.py` on every PR.
   Do **not** re-implement the rules in Power Fx — only do regex / enum
   sanity checks.
3. The Power Automate **GitHub connector** uses an OAuth connection. The
   connection's GitHub identity needs `contents:write` and
   `pull-requests:write` on the governance repo. Treat that connection as
   a security boundary: rotate the connection's PAT (or re-consent the
   GitHub App installation) on the same cadence as your other secrets.

## Step 1 — Flow A: FWG - Get Policy

Trigger: **When an agent calls the flow**. No inputs.

| Step | Action | Configuration |
| --- | --- | --- |
| 1 | GitHub → **Get file content** | Owner=`<org>`, Repo=`<governance-repo>`, Path=`rules/policy.yaml`, Branch=`main` |
| 2 | Compose `policyText` | `body('Get_file_content')` decoded as UTF-8 |
| 3 | Initialize `regions`, `capacities`, `approvedDomains`, `approvedSubDomains`, `policyVersion` | See "Parsing YAML in Power Automate" below |
| 4 | Respond to the agent | Outputs: those 5 strings |

### Parsing YAML in Power Automate

Power Automate has no native YAML parser. Pick one:

- **Simple regex parsing** (works because `rules/policy.yaml` has flat
  keys + lists of scalars):

  ```
  // pseudocode for the "regions" Compose
  string(
    join(
      skip(
        split(
          first(
            split(
              last(split(outputs('policyText'), 'regions:')),
              'capacities:'
            )
          ),
          '- '
        ),
        1
      ),
      ', '
    )
  )
  ```

  Repeat per field with the right anchors. Brittle if you reorder the YAML
  — pin the order with a comment in `rules/policy.yaml`.

- **CI-emitted JSON sidecar (recommended for stability).** Add a small step
  to `.github/workflows/validate.yml` that runs

  ```bash
  python -c 'import yaml,json,sys; \
    json.dump(yaml.safe_load(open("rules/policy.yaml")), sys.stdout)' \
    > rules/policy.json
  ```

  on push to `main` and commits the file. The flow then reads
  `rules/policy.json` instead and uses **Parse JSON** directly. One file
  to keep in sync, but parsing becomes a one-liner.

- **Inline JS in a Logic Apps Standard sub-flow.** Heaviest; only worth it
  if `rules/policy.yaml` grows complex enough to need a real YAML parser.

## Step 2 — Flow B: FWG - Submit Workspace Request

Trigger: **When an agent calls the flow**. Inputs:

| Name | Type |
| --- | --- |
| `workspaceName` | Text |
| `yamlBody`      | Text (YAML body composed by the topic, with an embedded `ownersJsonRaw` line) |
| `requesterEmail`| Text |

| Step | Action | Configuration |
| --- | --- | --- |
| 1 | Compose `branch` | `concat('request/', triggerBody()?['workspaceName'], '-', utcNow('yyyyMMddHHmmss'))` |
| 2 | GitHub → **Get a reference** | Owner / Repo as above; Ref=`heads/main` |
| 3 | GitHub → **Create a reference** | Ref=`refs/heads/@{outputs('Compose_branch')}`, SHA=`@{body('Get_a_reference')?['object']?['sha']}` |
| 4 | Compose `expandedYaml` | Take `yamlBody` and replace the trailing `ownersJsonRaw: '…'` line with a real `owners:` YAML block. Use `Parse JSON` on the inner string + a `Select` projecting each owner to four `  - displayName:` / `    email:` / `    type:` / `    role:` lines, then `join(…, '\n')`. |
| 5 | GitHub → **Create or update file content** | Path=`workspaces/@{triggerBody()?['workspaceName']}.yaml`, Branch=`@{outputs('Compose_branch')}`, Content=`@{outputs('Compose_expandedYaml')}`, Commit message=`Add workspace request @{triggerBody()?['workspaceName']}` |
| 6 | GitHub → **Create a pull request** | Base=`main`, Head=`@{outputs('Compose_branch')}`, Title=`Request workspace @{triggerBody()?['workspaceName']}`, Body=`Submitted via Copilot Studio by @{triggerBody()?['requesterEmail']}.` |
| 7 | Respond to the agent | `pullRequestUrl=@{body('Create_a_pull_request')?['html_url']}`, `pullRequestNumber=@{string(body('Create_a_pull_request')?['number'])}`, `branch=@{outputs('Compose_branch')}`, `submitted=true`, `error=""` |

Wrap steps 2-6 in a **Scope** block, then add a second "Respond to the
agent" with `submitted=false` + the failure message and **Configure run
after → has failed / has timed out / is skipped** on the failure-path
respond.

## Step 3 — Wire flows into the agent

In Copilot Studio → agent → **Actions** → **+ Add an action**:

1. Add **Flow → FWG - Get Policy**.
2. Add **Flow → FWG - Submit Workspace Request**.

For each, copy the display name and AI description from
`../agent/copilotstudio/actions/*.action.mcs.yml`.

## Step 4 — Pull, edit, push

```
/copilot-studio:copilot-studio-manage pull
```

The two `actions/*.action.mcs.yml` are now overwritten with real
`flowId` GUIDs. Substitute those GUIDs into the two `InvokeFlowAction`
blocks in `topics/show-policy.topic.mcs.yml` and
`topics/request-workspace.topic.mcs.yml`, then:

```
/copilot-studio:copilot-studio-manage push
```

## Step 5 — Add knowledge

Knowledge tab → **+ Add knowledge → Files** → upload:

- `rules/policy.yaml`
- `docs/setup.md`
- `docs/workspace-approval-workflow.md`
- `schemas/workspace.schema.json`

Pull again to materialise `knowledge/governance-docs.knowledge.mcs.yml`.

## Step 6 — Test

```
/copilot-studio:copilot-studio-test
```

Three runs cover the surface:

1. "What regions are allowed?" — calls Flow A, returns the live allow-lists.
2. "Request a new workspace" with `costCenter=12345` (no `CC-` prefix) —
   the Power Fx pre-flight blocks before Flow B is called.
3. A fully valid request — Flow B returns a real PR URL; the repo's
   `validate.yml` workflow then runs the rules engine.

## Step 7 — Decommission the Function App (when ready)

Once the Copilot Studio agent has been piloted and you have decided to
drop Option A:

1. Delete `agent/appPackage/` (M365 declarative agent package).
2. `cd infra/terraform && terraform destroy` (or its Bicep equivalent).
3. Delete the GitHub App or rotate it so it no longer holds a private
   key for the governance repo (the Power Automate connection now has
   the only credential).
4. Remove `api/`, `infra/`, `azure.yaml`, and `dist/` from the repo on
   a follow-up PR. Update the top-level README to drop Option A from
   the "How to request a workspace" section.

The repository's `validate.yml`, `provision.yml`, `drift.yml`,
`scripts/`, `rules/`, `schemas/`, and `workspaces/` directories are
**unchanged** by any of this — they are the canonical governance
contract and survive both options.
