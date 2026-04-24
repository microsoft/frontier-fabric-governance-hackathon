#!/usr/bin/env python3
"""Idempotently create-or-update Fabric workspaces from manifests.

Strategy:
  - For each manifest under workspaces/*.yaml:
      - Look up workspace by displayName (== manifest.name).
      - If absent: create with capacity assignment + description.
      - If present: ensure capacity assignment + description match.
      - Reconcile role assignments (add missing; do NOT remove unknown to
        avoid locking ourselves out — emit a warning instead).

Auth: DefaultAzureCredential (azure/login OIDC env vars in CI).
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
POLICY_PATH = REPO_ROOT / "rules" / "policy.yaml"

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def log(msg: str) -> None:
    print(msg, flush=True)


def resolve_capacity_id(logical_name: str, policy: dict) -> str:
    cfg = policy.get("approvedCapacities", {}).get(logical_name)
    if not cfg:
        raise RuntimeError(f"capacity '{logical_name}' not in approvedCapacities")
    cap_id = cfg.get("capacityId")
    if cap_id and cap_id != "FILL-ME-AT-FIRST-RUN":
        return cap_id
    # Look up by display name == logical_name's "<env>-<sku>-<region>" or use env var fallback
    fallback = os.environ.get("FABRIC_CAPACITY_ID")
    if fallback:
        return fallback
    looked = fab.find_capacity_id_by_display_name(logical_name.split("-", 1)[0]) or \
             fab.find_capacity_id_by_display_name(logical_name)
    if looked:
        return looked
    raise RuntimeError(
        f"could not resolve capacity id for '{logical_name}'. "
        "Set capacityId in rules/policy.yaml or set FABRIC_CAPACITY_ID env var."
    )


def reconcile_workspace(manifest: dict, policy: dict) -> None:
    name = manifest["name"]
    desc = manifest["description"]
    cap_id = resolve_capacity_id(manifest["capacity"], policy)

    log(f"--- {name} ---")
    existing = fab.get_workspace_by_name(name)
    if existing is None:
        log(f"  creating workspace (capacity={cap_id})")
        if DRY_RUN:
            log("  [dry-run] skipping create")
            return
        ws = fab.create_workspace(name, desc, capacity_id=cap_id)
        ws_id = ws["id"]
    else:
        ws_id = existing["id"]
        log(f"  exists: {ws_id} — updating description + capacity")
        if not DRY_RUN:
            fab.update_workspace(ws_id, description=desc)
            try:
                fab.assign_to_capacity(ws_id, cap_id)
            except Exception as e:
                log(f"  warn: assignToCapacity: {e}")

    # Role assignments
    desired = manifest.get("owners", [])
    existing_ras = [] if DRY_RUN else fab.list_role_assignments(ws_id)
    existing_keys = {(ra["principal"]["id"], ra["role"]) for ra in existing_ras}
    for o in desired:
        pid = o["identifier"]
        ptype = o["principalType"]
        role = o["role"]
        if (pid, role) in existing_keys:
            log(f"  ok: {ptype} {pid} {role}")
            continue
        log(f"  adding: {ptype} {pid} {role}")
        if DRY_RUN:
            continue
        try:
            fab.add_role_assignment(ws_id, pid, ptype, role)
        except Exception as e:
            log(f"  warn: role assignment failed for {pid}: {e}")


def main() -> int:
    policy = yaml.safe_load(POLICY_PATH.read_text())
    files = sorted(WORKSPACES_DIR.glob("*.yaml"))
    if not files:
        log("No manifests to provision.")
        return 0
    failed = 0
    for f in files:
        try:
            m = yaml.safe_load(f.read_text())
            reconcile_workspace(m, policy)
        except Exception as e:
            log(f"ERROR processing {f.name}: {e}")
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
