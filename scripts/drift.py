#!/usr/bin/env python3
"""Nightly drift detector.

Compares Fabric workspaces in the tenant to manifests in this repo:
  - Workspaces in tenant but not in repo  -> "unmanaged"
  - Workspaces in repo but not in tenant  -> "missing"
  - Description mismatch                  -> "drift"

Writes drift-report.md and exits non-zero if any drift is found.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fabric as fab  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = REPO_ROOT / "workspaces"


def main() -> int:
    manifests = {}
    for f in sorted(WORKSPACES_DIR.glob("*.yaml")):
        m = yaml.safe_load(f.read_text())
        manifests[m["name"]] = m

    tenant = {w["displayName"]: w for w in fab.list_workspaces()
              if w.get("type") in (None, "Workspace") and w.get("displayName")}

    unmanaged = sorted(set(tenant) - set(manifests))
    missing = sorted(set(manifests) - set(tenant))
    drift = []
    for name in sorted(set(manifests) & set(tenant)):
        if (tenant[name].get("description") or "") != manifests[name]["description"]:
            drift.append(name)

    lines = ["# Fabric Workspace Drift Report", ""]
    lines.append(f"- Manifests: {len(manifests)}")
    lines.append(f"- Tenant workspaces: {len(tenant)}")
    lines.append(f"- Unmanaged (in tenant, not in repo): **{len(unmanaged)}**")
    for n in unmanaged:
        lines.append(f"  - {n}")
    lines.append(f"- Missing (in repo, not in tenant): **{len(missing)}**")
    for n in missing:
        lines.append(f"  - {n}")
    lines.append(f"- Drifted (description mismatch): **{len(drift)}**")
    for n in drift:
        lines.append(f"  - {n}")

    md = "\n".join(lines) + "\n"
    (REPO_ROOT / "drift-report.md").write_text(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(md)
    print(md)
    return 0 if not (unmanaged or missing or drift) else 2


if __name__ == "__main__":
    sys.exit(main())
