# Challenge 02 — Items as code

> **Outcome:** governance now reaches down inside the workspace. Every lakehouse,
> notebook, and warehouse exists because a manifest in `items/<workspace>/` was
> reviewed via PR.

## Why this challenge exists

A clean workspace boundary is useful, but most data-leak and naming-mess scenarios
play out *inside* the workspace, at the item level: a lakehouse with no description,
a notebook full of hard-coded secrets, a warehouse table with column names like
`col1`. This challenge extends the Challenge 01 loop one level deeper.

## Learning objectives

1. Author item manifests for lakehouses, notebooks, and warehouses.
2. Extend `schemas/` and `rules/` with item-level governance.
3. Provision items idempotently and tied to a workspace manifest.
4. Use the **Fabric local MCP** `docs_item-definitions` and `docs_best-practices`
   tools to generate item definitions deterministically.
5. Use the **Skills for Fabric** `spark-authoring-cli` and `sqldw-authoring-cli` to
   scaffold notebook + warehouse contents.

## Prerequisites

- Challenges 00 and 01 complete.
- At least one workspace you own end-to-end via manifest.
- Skills installed: `spark-authoring-cli`, `sqldw-authoring-cli`.

## Tasks

### Task 1 — Design the item manifest

Create `schemas/item.schema.json` covering at least:

- `workspace` (must reference an existing workspace manifest by `name`)
- `kind` (`Lakehouse` | `Notebook` | `Warehouse` to start)
- `name` (kind-specific regex; e.g., `^lh_[a-z0-9_]{3,40}$` for lakehouses)
- `description` (≥ 60 chars)
- `sensitivityLabel` (optional override; defaults to workspace's label)
- `owners` (≥ 1, Group preferred)
- `tags` (free-form key/value)
- Per-kind blocks:
  - `Lakehouse.shortcuts[]`, `Lakehouse.schemaEnabled`
  - `Notebook.defaultLanguage`, `Notebook.attachedLakehouse`
  - `Warehouse.collation`, `Warehouse.caseSensitive`

Add an example for each kind under
`challenges/02-items-as-code/starter/items/<workspace>/`.

### Task 2 — Extend `rules/policy.yaml`

Add rules under a new top-level key `items:`:

- `naming-per-kind` (regex by `kind`)
- `description-min-length` (≥ 60)
- `lakehouse-must-have-owner-group`
- `notebook-no-hardcoded-secret` (regex check against the notebook payload)
- `warehouse-must-set-collation`
- `sensitivity-inherits-or-stricter` (item label must be ≥ workspace label)

Document the new rules in your team's `challenge.md` notes.

### Task 3 — Extend the validator

Edit `scripts/validate.py` (or add `scripts/validate_items.py` for clarity) to:

1. Load all `items/**/*.yaml` manifests.
2. Validate against `schemas/item.schema.json`.
3. Enforce the new policy rules.
4. Emit findings into the existing sticky comment, grouped by file.

### Task 4 — Extend the provisioner

Edit `scripts/provision.py` (or add `scripts/provision_items.py`) to:

1. For each item manifest, look up its parent workspace by display name.
2. Idempotently create the item if absent, update if present.
3. Use `core_create-item` semantics: load the JSON item definition from the
   manifest, POST to `/workspaces/{ws}/items`, poll long-running operations.
4. Apply role assignments and tags.

Use the **Fabric local MCP** `docs_item-definitions` tool *at design time* to
pull the canonical schema for each item kind into your manifest examples.

### Task 5 — Scaffold real content with Skills

For lakehouses and notebooks, use **`spark-authoring-cli`** from chat:

```
@spark-authoring-cli In workspace "dev-plt-myteam-playground", scaffold a notebook
"nb_silver_clean" that reads "lh_bronze_raw.events" and writes to
"lh_silver_clean.events_clean" with deduplication on (event_id, timestamp).
```

For warehouses, use **`sqldw-authoring-cli`**:

```
@sqldw-authoring-cli In workspace "dev-plt-myteam-playground", create a warehouse
"wh_marts_finance" with a "dim_date" dimension table and a "fact_orders" fact
table. Set collation Latin1_General_100_CI_AS_SC_UTF8.
```

Commit the scaffolded artifacts under `items/<workspace>/` and open the PR.

### Task 6 — Add a `items.yml` workflow

Add `.github/workflows/items.yml`, modelled on `validate.yml`, with `paths:`
filters for `items/**`, `schemas/item.schema.json`, and `scripts/validate_items.py`.

Wire item provisioning into `provision.yml` (same merge → environment gate
→ apply flow as Challenge 01).

## Success criteria

- [ ] At least one lakehouse, one notebook, and one warehouse exist in your
      workspace because a manifest under `items/` was merged.
- [ ] An item manifest with a missing description blocks the PR.
- [ ] The agent (via local MCP) can fetch the item definition for any of your
      items and the JSON matches the manifest you committed.

## Stretch goals

- **Table-level governance for lakehouses.** Add an optional `tables:` block to
  the lakehouse manifest with required column descriptions; validate by running
  a notebook (in dry-run mode) that introspects the lakehouse schema.
- **OneSecurity for warehouses.** Capture row- and column-level security policies
  in the warehouse manifest; apply via SQLDW skill.
- **`bulk_move_items`.** Add a `folder:` field to item manifests and reconcile
  using `bulk_move_items` so items end up in the right folder.

## MCP tips

- **Local MCP first.** `docs_item-definitions` + `docs_api-examples` save you from
  guessing payload shapes. Pull the schema, fill in the manifest, then commit.
- **Core MCP for verification.** After provisioning, ask
  `"Get the definition of <item> in <workspace>"` and diff against the manifest.

## Skills tips

- Skills generate code; your manifest is still the source of truth. After a Skill
  scaffolds a notebook, copy the notebook payload into the manifest's
  `definition:` block, **not** the other way around.

## References

- [`docs/mcp-and-skills.md`](../../docs/mcp-and-skills.md)
- [Fabric items REST API](https://learn.microsoft.com/rest/api/fabric/core/items)
- [Skills for Fabric — Spark authoring CLI](https://github.com/microsoft/skills-for-fabric/tree/main/skills/spark-authoring-cli)
- [Skills for Fabric — SQLDW authoring CLI](https://github.com/microsoft/skills-for-fabric/tree/main/skills/sqldw-authoring-cli)
