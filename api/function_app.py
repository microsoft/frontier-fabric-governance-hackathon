"""Azure Functions (Python v2) HTTP backend for the M365 declarative agent.

Endpoints (mounted under /api):
  POST /validate  — schema + MEO rule check, no side effects
  POST /submit    — validate, then open a PR via GitHub App
  GET  /policy    — read-only listing of approvedDomains/Areas/Subjects/etc.
                    so the agent can show real-time choices to the user
  GET  /healthz   — liveness probe

Validation reuses scripts/rules_engine.py (same logic as the PR check) so
there is no chance of drift between the agent's pre-flight check and the
PR validation that gates the merge.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import azure.functions as func
import yaml

# Make scripts/ importable so we share the rule engine with the CLI.
# In production (azd deploy), prepackage hook copies rules_engine.py into
# this directory, so the local import works without the path tweak.
HERE = Path(__file__).resolve().parent
if not (HERE / "rules_engine.py").exists():
    sys.path.insert(0, str(HERE.parent / "scripts"))

from rules_engine import (  # noqa: E402  (import after sys.path tweak)
    apply_rules,
    load_policy,
    load_schema,
    validate_schema,
)

# AuthLevel.ANONYMOUS so the M365 declarative agent (plugin auth.type=None)
# can call us. The agent has no way to attach a Function host key. To harden,
# enable Easy Auth (Entra ID) on the Function App and switch the plugin to
# ApiKeyPluginVault or OAuthPluginVault.
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# -- helpers --------------------------------------------------------------
def _json_response(payload: dict[str, Any], status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(payload),
        status_code=status,
        mimetype="application/json",
    )


def _read_manifest(req: func.HttpRequest) -> dict[str, Any]:
    try:
        return req.get_json()
    except ValueError:
        # Allow YAML body too, since the agent may send it that way
        body = req.get_body().decode("utf-8")
        return yaml.safe_load(body) or {}


def _branch_for(name: str) -> str:
    safe = re.sub(r"[^a-z0-9-]", "-", name.lower())[:60]
    return f"workspace/{safe}-{int(time.time())}"


# -- /healthz -------------------------------------------------------------
@app.route(route="healthz", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def healthz(req: func.HttpRequest) -> func.HttpResponse:
    return _json_response({"status": "ok"})


# -- /policy --------------------------------------------------------------
@app.route(route="policy", methods=["GET"])
def policy(req: func.HttpRequest) -> func.HttpResponse:
    """Expose only the lists the agent needs to render choices.

    Never expose the entire policy YAML — keep tenant-internal rule weights
    out of the agent context.
    """
    p = load_policy()
    return _json_response({
        "approvedCountries": p.get("approvedCountries", []),
        "approvedAreas": p.get("approvedAreas", []),
        "approvedSubjects": p.get("approvedSubjects", []),
        "approvedDomains": p.get("approvedDomains", []),
        "approvedSensitivityLabels": p.get("approvedSensitivityLabels", []),
        "approvedCostCenters": p.get("approvedCostCenters", []),
        "environments": ["poc", "dev", "sit", "uat", "stg", "prd"],
        "dataProductTypes": ["brz", "slv", "gld", "ndf"],
        "approvedCapacities": [
            {"name": k, "region": v.get("region"),
             "allowedEnvironments": v.get("allowedEnvironments", [])}
            for k, v in p.get("approvedCapacities", {}).items()
        ],
    })


# -- /validate ------------------------------------------------------------
@app.route(route="validate", methods=["POST"])
def validate(req: func.HttpRequest) -> func.HttpResponse:
    manifest = _read_manifest(req)
    schema = load_schema()
    policy_doc = load_policy()
    findings = validate_schema(manifest, schema)
    if not any(f.severity == "block" for f in findings):
        findings.extend(apply_rules(manifest, policy_doc))
    blocking = [f for f in findings if f.severity == "block"]
    return _json_response({
        "passed": not blocking,
        "findings": [f.to_dict() for f in findings],
        "blockingCount": len(blocking),
        "warningCount": sum(1 for f in findings if f.severity == "warn"),
    })


# -- /submit --------------------------------------------------------------
@app.route(route="submit", methods=["POST"])
def submit(req: func.HttpRequest) -> func.HttpResponse:
    manifest = _read_manifest(req)
    schema = load_schema()
    policy_doc = load_policy()

    findings = validate_schema(manifest, schema)
    if not any(f.severity == "block" for f in findings):
        findings.extend(apply_rules(manifest, policy_doc))
    blocking = [f for f in findings if f.severity == "block"]
    if blocking:
        return _json_response({
            "passed": False,
            "submitted": False,
            "findings": [f.to_dict() for f in findings],
            "message": "Validation failed. PR was NOT created.",
        }, status=400)

    name = manifest["name"]
    file_content = yaml.safe_dump(manifest, sort_keys=False)
    file_path = f"workspaces/{name}.yaml"
    branch = _branch_for(name)

    requester = req.headers.get("x-ms-client-principal-name", "agent")
    pr_title = f"chore(workspace): request {name}"
    pr_body = (
        f"Submitted via the **Fabric Workspace Provisioner** M365 agent.\n\n"
        f"Requester: `{requester}`\n"
        f"Environment: `{manifest.get('environment')}` | "
        f"Capacity: `{manifest.get('capacity')}` | "
        f"Domain: `{manifest.get('domain')}`\n\n"
        f"All MEO governance rules passed pre-flight checks. "
        f"PR validation will re-run as the source of truth."
    )

    # Local mode: skip GitHub call so devs can run `func start` without secrets
    if os.environ.get("DRY_RUN", "false").lower() == "true":
        return _json_response({
            "passed": True, "submitted": False, "dryRun": True,
            "wouldCreate": {"path": file_path, "branch": branch,
                            "title": pr_title}, "findings": [],
        })

    try:
        from shared.github_app import create_pull_request  # imported lazily
        pr = create_pull_request(
            file_path=file_path, file_content=file_content, branch=branch,
            pr_title=pr_title, pr_body=pr_body,
            commit_message=f"Add workspace request {name}",
        )
        return _json_response({
            "passed": True, "submitted": True,
            "pullRequestUrl": pr.get("html_url"),
            "pullRequestNumber": pr.get("number"),
            "branch": branch,
            "findings": [f.to_dict() for f in findings],
        })
    except Exception as e:  # noqa: BLE001
        return _json_response({
            "passed": True, "submitted": False,
            "error": f"GitHub API error: {e}",
            "findings": [f.to_dict() for f in findings],
        }, status=502)
