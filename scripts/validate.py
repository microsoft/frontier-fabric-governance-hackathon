#!/usr/bin/env python3
"""Validate workspace manifests against schema + rules/policy.yaml.

Usage:
    python scripts/validate.py [--changed-only] [path ...]

Exit code: 0 if all manifests pass blocking rules; 1 otherwise.
Writes a markdown report to $GITHUB_STEP_SUMMARY (if set) and to ./validation-report.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "workspace.schema.json"
POLICY_PATH = REPO_ROOT / "rules" / "policy.yaml"
WORKSPACES_DIR = REPO_ROOT / "workspaces"

# Live-tenant checks (group existence, etc.) require auth. Allow opt-out.
LIVE_CHECKS = os.environ.get("LIVE_CHECKS", "false").lower() == "true"


@dataclass
class Finding:
    rule_id: str
    severity: str  # block | warn | info
    message: str


@dataclass
class FileResult:
    path: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "block"]

    @property
    def passed(self) -> bool:
        return not self.blocking


def load_yaml(p: Path) -> dict:
    with p.open() as f:
        return yaml.safe_load(f)


def load_policy() -> dict:
    return load_yaml(POLICY_PATH)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def changed_workspace_files() -> list[Path]:
    base = os.environ.get("GITHUB_BASE_REF", "main")
    try:
        subprocess.run(["git", "fetch", "origin", base, "--depth=1"], check=False, capture_output=True)
        out = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base}...HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout
    except Exception:
        out = ""
    paths = []
    for line in out.splitlines():
        if line.startswith("workspaces/") and (line.endswith(".yaml") or line.endswith(".yml")):
            p = REPO_ROOT / line
            if p.exists():
                paths.append(p)
    return paths


def all_workspace_files() -> list[Path]:
    return sorted([p for p in WORKSPACES_DIR.glob("*.yaml")])


def validate_schema(manifest: dict, schema: dict) -> list[Finding]:
    v = Draft202012Validator(schema)
    out = []
    for err in v.iter_errors(manifest):
        path = ".".join(str(x) for x in err.absolute_path) or "<root>"
        out.append(Finding("schema", "block", f"{path}: {err.message}"))
    return out


PERSONAL_RX = re.compile(r"\b(my|personal|mine|me)\b", re.IGNORECASE)


def apply_rules(manifest: dict, policy: dict) -> list[Finding]:
    findings: list[Finding] = []
    name = manifest.get("name", "")
    env = manifest.get("environment", "")

    # naming-convention is enforced by schema pattern; double-check env prefix matches
    if name and env and not name.startswith(f"{env}-"):
        findings.append(Finding("env-prefix-matches-environment", "block",
                                f"name '{name}' does not start with '{env}-'"))

    cap_name = manifest.get("capacity")
    cap_cfg = policy.get("approvedCapacities", {}).get(cap_name)
    if not cap_cfg:
        findings.append(Finding("capacity-allow-list", "block",
                                f"capacity '{cap_name}' is not in approvedCapacities"))
    else:
        if env and env not in cap_cfg.get("allowedEnvironments", []):
            findings.append(Finding("capacity-allowed-for-env", "block",
                                    f"capacity '{cap_name}' does not allow environment '{env}'"))
        if manifest.get("region") and manifest["region"] != cap_cfg.get("region"):
            findings.append(Finding("region-matches-capacity", "block",
                                    f"region '{manifest['region']}' != capacity region '{cap_cfg.get('region')}'"))

    owners = manifest.get("owners", []) or []
    groups = [o for o in owners if o.get("principalType") == "Group"]
    if len(owners) < 2 or len(groups) < 1:
        findings.append(Finding("owners-min-two-groups", "block",
                                "need >= 2 owners and at least one Group"))
    if not any(o.get("role") == "Admin" for o in owners):
        findings.append(Finding("owners-have-admin", "block",
                                "at least one owner must have role=Admin"))

    domain = manifest.get("domain")
    if domain and domain not in policy.get("approvedDomains", []):
        findings.append(Finding("domain-allow-list", "warn",
                                f"domain '{domain}' not in approvedDomains"))

    sl = manifest.get("sensitivityLabel")
    if not sl:
        findings.append(Finding("sensitivity-required", "block", "sensitivityLabel is required"))
    elif sl not in policy.get("approvedSensitivityLabels", []):
        findings.append(Finding("sensitivity-required", "block",
                                f"sensitivityLabel '{sl}' not in approved set"))

    cc = manifest.get("costCenter")
    if cc and cc not in policy.get("approvedCostCenters", []):
        findings.append(Finding("cost-center-allow-list", "block",
                                f"costCenter '{cc}' not in approvedCostCenters"))

    desc = manifest.get("description", "") or ""
    if len(desc.strip()) < 30:
        findings.append(Finding("description-quality", "block",
                                "description must be >= 30 chars"))

    if PERSONAL_RX.search(name):
        findings.append(Finding("no-personal-workspaces", "block",
                                f"name '{name}' looks personal"))

    if env == "prd":
        if sl not in ("Confidential", "Highly Confidential"):
            findings.append(Finding("prod-extra-controls", "block",
                                    "prd workspaces require Confidential or higher sensitivity"))
        if len(groups) < 2:
            findings.append(Finding("prod-extra-controls", "block",
                                    "prd workspaces require at least 2 Group owners"))

    if LIVE_CHECKS:
        try:
            from _fabric import graph_group_exists  # type: ignore
            for g in groups:
                if not graph_group_exists(g["identifier"]):
                    findings.append(Finding("owner-groups-exist", "block",
                                            f"group {g['identifier']} not found in Entra"))
        except Exception as e:
            findings.append(Finding("owner-groups-exist", "warn", f"live check skipped: {e}"))

    return findings


def render_markdown(results: list[FileResult]) -> str:
    lines = ["# Workspace request validation", ""]
    if not results:
        lines.append("_No workspace manifests changed in this PR._")
        return "\n".join(lines)
    overall_ok = all(r.passed for r in results)
    lines.append(f"**Overall:** {'✅ PASS' if overall_ok else '❌ FAIL'}")
    lines.append("")
    for r in results:
        lines.append(f"## `{r.path}`")
        if not r.findings:
            lines.append("- ✅ All rules passed.")
            continue
        for f in r.findings:
            icon = {"block": "❌", "warn": "⚠️", "info": "ℹ️"}.get(f.severity, "•")
            lines.append(f"- {icon} **{f.rule_id}** ({f.severity}): {f.message}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed-only", action="store_true")
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args()

    if args.paths:
        files = [Path(p) for p in args.paths]
    elif args.changed_only:
        files = changed_workspace_files()
    else:
        files = all_workspace_files()

    schema = load_schema()
    policy = load_policy()
    results: list[FileResult] = []

    for path in files:
        result = FileResult(path=str(path.relative_to(REPO_ROOT)))
        try:
            manifest = load_yaml(path)
        except Exception as e:
            result.findings.append(Finding("yaml-parse", "block", f"YAML parse error: {e}"))
            results.append(result)
            continue
        result.findings.extend(validate_schema(manifest, schema))
        if not result.blocking:
            result.findings.extend(apply_rules(manifest, policy))
        results.append(result)

    md = render_markdown(results)
    (REPO_ROOT / "validation-report.md").write_text(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(md + "\n")
    print(md)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
