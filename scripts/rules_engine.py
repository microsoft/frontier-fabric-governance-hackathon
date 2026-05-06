"""Shared MEO Fabric workspace governance rule engine.

Used by:
- scripts/validate.py (CLI used in PR validation)
- api/function_app.py (Azure Functions backend powering the M365 agent)

Source of truth for rules:
- rules/policy.yaml      — allow-lists, capacities, quotas
- schemas/workspace.schema.json — JSON Schema for manifests
- docs/meo-governance-rules.md — narrative rules from the MEO PPTX

Keep this module pure-Python with no I/O side effects beyond the explicit
load_* helpers, so it can be safely imported from short-lived Functions.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


# ---------- Repo-relative paths ----------
# The CLI runs from the repo root where schemas/ and rules/ are siblings of
# scripts/. The Azure Function bundles workspace.schema.json and policy.yaml
# next to this module (see azure.yaml prepackage hook). Resolve both layouts
# so the same file works in both environments without code changes.
_HERE = Path(__file__).resolve().parent
_REPO_CANDIDATE = _HERE.parent
REPO_ROOT = _REPO_CANDIDATE if (_REPO_CANDIDATE / "schemas").is_dir() else _HERE


def _resolve_path(repo_relative: Path, flat_name: str) -> Path:
    """Pick the repo-layout path if the file is there, else the flat sibling."""
    if repo_relative.is_file():
        return repo_relative
    flat = _HERE / flat_name
    if flat.is_file():
        return flat
    return repo_relative  # fall back so error messages reference the canonical path


SCHEMA_PATH = _resolve_path(REPO_ROOT / "schemas" / "workspace.schema.json", "workspace.schema.json")
POLICY_PATH = _resolve_path(REPO_ROOT / "rules" / "policy.yaml", "policy.yaml")


# ---------- Regexes (single source of truth) ----------
NAME_RX = re.compile(
    r"^(?P<country>[a-z]{2})-(?P<area>[a-z]{2,4})-(?P<subject>[a-z]{2,8})-"
    r"(?P<dataProductType>brz|slv|gld|ndf)-"
    r"(?P<environment>poc|dev|sit|uat|stg|prd)-(?P<suffix>[a-z0-9]{1,6})$"
)
GROUP_NAME_RX = re.compile(
    r"^grp_(fabric|powerbi)_(dev|sit|uat|prd)_[a-z]{2,5}_(admin|member|contributor|viewer)$"
)
SUBDOMAIN_RX = re.compile(r"^sdm-[a-z]{2,4}-[a-z0-9]{2,6}$")
DOMAIN_RX = re.compile(r"^dom-[a-z]{2,4}-[a-z0-9]{2,6}$")
PERSONAL_RX = re.compile(r"\b(my|personal|mine|me)\b", re.IGNORECASE)


@dataclass
class Finding:
    rule_id: str
    severity: str  # block | warn | info
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"rule_id": self.rule_id, "severity": self.severity, "message": self.message}


@dataclass
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "block"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warn"]

    @property
    def passed(self) -> bool:
        return not self.blocking

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
            "blockingCount": len(self.blocking),
            "warningCount": len(self.warnings),
        }


# ---------- Loaders ----------
def load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def load_policy(path: Path | None = None) -> dict:
    return load_yaml(path or POLICY_PATH)


def load_schema(path: Path | None = None) -> dict:
    return json.loads((path or SCHEMA_PATH).read_text())


# ---------- Schema validation ----------
def validate_schema(manifest: dict, schema: dict) -> list[Finding]:
    v = Draft202012Validator(schema)
    out: list[Finding] = []
    for err in v.iter_errors(manifest):
        path = ".".join(str(x) for x in err.absolute_path) or "<root>"
        out.append(Finding("schema", "block", f"{path}: {err.message}"))
    return out


# ---------- MEO rule checks ----------
def apply_rules(manifest: dict, policy: dict) -> list[Finding]:
    findings: list[Finding] = []
    name = manifest.get("name", "") or ""
    env = manifest.get("environment", "") or ""

    # Naming convention + segment cross-check
    m = NAME_RX.match(name)
    if not m:
        findings.append(
            Finding("naming-convention", "block",
                    f"name '{name}' does not match MEO 6-segment pattern")
        )
    else:
        for seg in ("country", "area", "subject", "dataProductType", "environment", "suffix"):
            expected = m.group(seg)
            actual = manifest.get(seg)
            if actual is None:
                findings.append(
                    Finding("name-segments-match-fields", "block",
                            f"missing required field '{seg}'")
                )
            elif str(actual) != expected:
                findings.append(
                    Finding("name-segments-match-fields", "block",
                            f"name segment '{seg}' is '{expected}' but field '{seg}' is '{actual}'")
                )

    # Capacity
    cap_name = manifest.get("capacity")
    cap_cfg = policy.get("approvedCapacities", {}).get(cap_name)
    if not cap_cfg:
        findings.append(
            Finding("capacity-allow-list", "block",
                    f"capacity '{cap_name}' is not in approvedCapacities")
        )
    else:
        if env and env not in cap_cfg.get("allowedEnvironments", []):
            findings.append(
                Finding("capacity-allowed-for-env", "block",
                        f"capacity '{cap_name}' does not allow environment '{env}'")
            )
        if manifest.get("region") and manifest["region"] != cap_cfg.get("region"):
            findings.append(
                Finding("region-matches-capacity", "block",
                        f"region '{manifest['region']}' != capacity region '{cap_cfg.get('region')}'")
            )

    # Allow-lists per segment
    country = manifest.get("country")
    if country and country not in policy.get("approvedCountries", []):
        findings.append(
            Finding("country-allow-list", "warn",
                    f"country '{country}' not in approvedCountries")
        )
    area = manifest.get("area")
    if area and area not in policy.get("approvedAreas", []):
        findings.append(
            Finding("area-allow-list", "warn",
                    f"area '{area}' not in approvedAreas")
        )
    subject = manifest.get("subject")
    if subject and subject not in policy.get("approvedSubjects", []):
        findings.append(
            Finding("subject-allow-list", "warn",
                    f"subject '{subject}' not in approvedSubjects")
        )

    # Owners
    owners = manifest.get("owners", []) or []
    groups = [o for o in owners if o.get("principalType") == "Group"]
    if len(owners) < 2 or len(groups) < 1:
        findings.append(
            Finding("owners-min-two-groups", "block",
                    "need >= 2 owners and at least one Group")
        )
    if not any(o.get("role") == "Admin" for o in owners):
        findings.append(
            Finding("owners-have-admin", "block",
                    "at least one owner must have role=Admin")
        )
    for g in groups:
        gname = g.get("groupName")
        if gname and not GROUP_NAME_RX.match(gname):
            findings.append(
                Finding("owner-group-naming", "warn",
                        f"group display name '{gname}' does not match grp_<service>_<env>_<area>_<role>")
            )

    # Domain / sub-domain
    domain = manifest.get("domain")
    if not domain:
        findings.append(Finding("domain-allow-list", "block", "domain is required"))
    elif not DOMAIN_RX.match(domain):
        findings.append(
            Finding("domain-allow-list", "block",
                    f"domain '{domain}' does not match dom-<area>-<produto>")
        )
    elif domain not in policy.get("approvedDomains", []):
        findings.append(
            Finding("domain-allow-list", "block",
                    f"domain '{domain}' is not one of the 19 MEO approvedDomains")
        )

    sub_domain = manifest.get("subDomain")
    if not sub_domain:
        findings.append(Finding("subdomain-pattern", "block", "subDomain is required"))
    elif not SUBDOMAIN_RX.match(sub_domain):
        findings.append(
            Finding("subdomain-pattern", "block",
                    f"subDomain '{sub_domain}' does not match sdm-<area>-<produto>")
        )

    # Sensitivity
    sl = manifest.get("sensitivityLabel")
    if not sl:
        findings.append(Finding("sensitivity-required", "block", "sensitivityLabel is required"))
    elif sl not in policy.get("approvedSensitivityLabels", []):
        findings.append(
            Finding("sensitivity-required", "block",
                    f"sensitivityLabel '{sl}' not in approved set")
        )

    # Cost center
    cc = manifest.get("costCenter")
    if cc and cc not in policy.get("approvedCostCenters", []):
        findings.append(
            Finding("cost-center-allow-list", "block",
                    f"costCenter '{cc}' not in approvedCostCenters")
        )

    # Description quality
    desc = manifest.get("description", "") or ""
    if len(desc.strip()) < 30:
        findings.append(
            Finding("description-quality", "block",
                    "description must be >= 30 chars")
        )

    # Personal-name guard
    if PERSONAL_RX.search(name):
        findings.append(
            Finding("no-personal-workspaces", "block",
                    f"name '{name}' looks personal")
        )

    # Production extras
    if env == "prd":
        if sl not in ("Confidential", "Highly Confidential"):
            findings.append(
                Finding("prod-extra-controls", "block",
                        "prd workspaces require Confidential or higher sensitivity")
            )
        if len(groups) < 2:
            findings.append(
                Finding("prod-extra-controls", "block",
                        "prd workspaces require at least 2 Group owners")
            )

    # Optional live Entra group existence check
    if os.environ.get("LIVE_CHECKS", "false").lower() == "true":
        try:
            from _fabric import graph_group_exists  # type: ignore
            for g in groups:
                if not graph_group_exists(g["identifier"]):
                    findings.append(
                        Finding("owner-groups-exist", "block",
                                f"group {g['identifier']} not found in Entra")
                    )
        except Exception as e:  # noqa: BLE001
            findings.append(Finding("owner-groups-exist", "warn", f"live check skipped: {e}"))

    return findings


# ---------- One-shot helper ----------
def validate_manifest(manifest: dict, policy: dict | None = None,
                      schema: dict | None = None) -> ValidationResult:
    """Run schema + rule checks. Returns a ValidationResult."""
    policy = policy if policy is not None else load_policy()
    schema = schema if schema is not None else load_schema()
    result = ValidationResult()
    result.findings.extend(validate_schema(manifest, schema))
    if not result.blocking:
        result.findings.extend(apply_rules(manifest, policy))
    return result
