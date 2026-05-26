# Challenge 06 — Fabric Data Agent governance

> **Outcome:** Fabric Data Agents (the natural-language Q&A layer over OneLake)
> can only be created via PR, with an explicit allow-list of data sources, RAI-linted
> instructions, and Purview-aware risk gating.

## Why this challenge exists

A Fabric Data Agent is a *governance amplifier*: one approved data source can be
reached by anyone the agent is shared with. That makes agents fantastic for
business users — and dangerous if you don't constrain which data sources they
can touch, what they can say, and which workspaces they live in.

## Learning objectives

1. Design a Fabric Data Agent manifest that constrains data sources to those
   explicitly approved.
2. Lint agent instructions for Responsible AI red flags before merge.
3. Enforce sensitivity-based clearance: an agent can only point at data sources
   whose label is ≤ the agent owners' clearance.
4. Optionally integrate Purview DSPM signals to block agents over risky sources.
5. Use the Fabric Core MCP to inspect provisioned agents.

## Prerequisites

- Challenges 00–04 complete.
- A capacity with the **Fabric Data Agent** feature enabled (F2+ with feature on).
- Purview integration set up if you intend to do the DSPM stretch.

## Tasks

### Task 1 — Agent manifest schema

Add `schemas/agent.schema.json`; example:

```yaml
# agents/agent-finance-revenue-qa.yaml
name: agent-finance-revenue-qa
workspace: prd-fin-gold
description: >
  Natural-language Q&A over the Finance Revenue gold semantic model
  for CFO-org users. Answers questions about monthly close and revenue
  trends; refuses anything outside that scope.
owners:
  - principalType: Group
    identifier: <objectId>
    displayName: sg-fin-admins
clearance: Confidential
dataSources:
  - kind: SemanticModel
    workspace: prd-fin-gold
    name: sm_gold_revenue
  - kind: Lakehouse
    workspace: prd-fin-gold
    name: lh_gold_revenue
instructionsFile: agents/instructions/agent-finance-revenue-qa.md
exampleQuestions:
  - "What was net revenue last quarter?"
  - "How did Q3 close-day variance compare to Q2?"
  - "List the top 5 product lines by gross margin in 2026."
```

The `instructionsFile` is a separate Markdown file with the persona, allowed
topics, refusal rules, and tone.

### Task 2 — Approved-source policy

Add `agents:` to `rules/policy.yaml`:

- Each `dataSources[*]` must reference an item manifest in `items/`.
- The data source's `sensitivityLabel` must be ≤ the agent's `clearance`.
- `clearance` must match the workspace's sensitivity label.
- Owners must include at least one `Group` and zero `User` for prd workspaces
  (re-use Challenge 04 rules).

### Task 3 — RAI lint on instructions

Add `scripts/lint_agent_instructions.py`:

- Must contain a **refusal pattern** section (regex on the markdown).
- Must contain an **out-of-scope behavior** section.
- Must **not** instruct the agent to ignore Purview / DLP.
- Must **not** include any of the project's "high-risk phrase" list
  (`rules/agent/banned_phrases.yaml`).
- Word count of the instructions: 200–2000.

Wire the linter into `validate.yml` and surface findings in the sticky comment.

### Task 4 — Provisioner

Extend `scripts/provision.py` (or add `scripts/provision_agents.py`) to:

1. For each agent manifest, look up the workspace ID.
2. Use the Fabric Data Agent creation API (or the Fabric local MCP `core_create-item`
   with item kind `DataAgent`) to create the agent.
3. Set the agent's instructions and example questions from the manifest.
4. Configure data sources via the API, refusing anything outside the manifest's
   `dataSources`.
5. Share the agent with the owners group (Member role).

### Task 5 — Verify via Fabric Core MCP

Ask:

```
What items of type DataAgent exist in workspace prd-fin-gold?
Get the definition of "agent-finance-revenue-qa" — what data sources is it pointed at?
```

The list of data sources must equal the manifest's `dataSources`.

### Task 6 — Drift on agents

Extend `drift.py` to detect:

- Agents in tenant with no manifest → `drift/unmanaged-agent`.
- Manifests whose `dataSources` don't match live → `drift/agent-source-mismatch`.
- Instruction file SHA drift (live agent's instructions differ from
  `instructionsFile`'s content).

## Success criteria

- [ ] One governed agent is provisioned via PR and answers an example question
      using the Confidential gold semantic model.
- [ ] An agent manifest that points at an unmanaged data source is blocked.
- [ ] An agent instructions file missing a refusal section is blocked.
- [ ] Drift detects an out-of-band instruction change and opens an issue.

## Stretch goals

- **Purview DSPM integration.** Before provisioning, query Purview for active
  DSPM findings on each data source. If any `High` finding exists, block.
- **Cross-tenant agents.** Add a `crossTenant: true` flag and the required
  OneLake external data sharing checks.
- **Microsoft 365 Copilot surfacing.** Approve agents for surfacing inside
  Microsoft 365 Copilot via additional CODEOWNERS approval.

## MCP tips

- The agent's `dataSources` are visible via `get_item_definition` on the
  DataAgent item; use that in drift detection rather than parsing the portal.

## Skills tips

- This challenge doesn't depend on a Skill, but `powerbi-consumption-cli` is
  useful for the smoke test (you can ask it to run the example questions against
  the semantic model and confirm the data is reachable).

## References

- [Fabric data agent concepts](https://learn.microsoft.com/fabric/data-science/concept-data-agent)
- [Create a Fabric data agent](https://learn.microsoft.com/fabric/data-science/how-to-create-data-agent)
- [Microsoft Purview governance for Fabric Copilots and agents](https://learn.microsoft.com/purview/ai-microsoft-purview)
