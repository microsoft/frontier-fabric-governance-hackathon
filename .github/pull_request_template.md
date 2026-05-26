## Change summary

- **Type:** Workspace / Item / Domain / Capacity / Access / Agent / Pipeline / Other
- **Challenge:** 01 / 02 / 03 / 04 / 05 / 06 / 07 / 08 / capstone
- **Business purpose:**
- **Manifest(s) touched:**

## Workspace-specific (Challenge 01 / 03)

- **Environment:** dev / stg / prd / sbx
- **Owner group(s):**
- **Capacity:**
- **Domain:**
- **Sensitivity label:**

## Checklist

- [ ] Manifest follows the naming convention enforced by `rules/policy.yaml`.
- [ ] At least 2 owners specified; Group preferred over User.
- [ ] Capacity / domain references resolve to existing manifests.
- [ ] Description ≥ 30 chars and explains business purpose.
- [ ] Reviewed cost-center, region, and sensitivity label.
- [ ] If this PR introduces a new resource kind, the matching challenge has been read.

The **validate** workflow posts a sticky comment with pass/fail per rule.
See the relevant challenge under `challenges/` for the lab flow.
