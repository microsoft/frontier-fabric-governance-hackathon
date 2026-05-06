#!/usr/bin/env python3
"""Validate workspace manifests against schema + rules/policy.yaml.

Usage:
    python scripts/validate.py [--changed-only] [path ...]

Exit code: 0 if all manifests pass blocking rules; 1 otherwise.
Writes a markdown report to $GITHUB_STEP_SUMMARY (if set) and to ./validation-report.md.

The actual rule engine lives in scripts/rules_engine.py and is shared with the
Azure Functions backend that powers the M365 declarative agent.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from rules_engine import (
    REPO_ROOT,
    Finding,
    apply_rules,
    load_policy,
    load_schema,
    load_yaml,
    validate_schema,
)

WORKSPACES_DIR = REPO_ROOT / "workspaces"


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


def _display_path(path: Path) -> str:
    """Return a repo-relative string when possible, falling back to absolute."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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
        result = FileResult(path=_display_path(path))
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
