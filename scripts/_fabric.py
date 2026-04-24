"""Thin Fabric REST client using azure-identity (DefaultAzureCredential).

Auth: in GitHub Actions we use the azure/login@v2 OIDC step to populate
AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_FEDERATED_TOKEN_FILE, which
DefaultAzureCredential picks up automatically.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests
from azure.identity import DefaultAzureCredential

FABRIC_BASE = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

_credential: Optional[DefaultAzureCredential] = None


def _cred() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return _credential


def token(scope: str = FABRIC_SCOPE) -> str:
    return _cred().get_token(scope).token


def _request(method: str, url: str, *, scope: str = FABRIC_SCOPE,
             json: Any = None, params: dict | None = None,
             expect: tuple[int, ...] = (200, 201, 202, 204),
             retries: int = 5) -> requests.Response:
    headers = {"Authorization": f"Bearer {token(scope)}", "Content-Type": "application/json"}
    backoff = 2.0
    for attempt in range(retries):
        r = requests.request(method, url, headers=headers, json=json, params=params, timeout=60)
        if r.status_code in expect:
            return r
        if r.status_code in (429, 502, 503, 504):
            wait = float(r.headers.get("Retry-After", backoff))
            time.sleep(wait)
            backoff *= 2
            continue
        # 401/403 etc — surface immediately
        raise RuntimeError(f"{method} {url} -> {r.status_code}: {r.text}")
    raise RuntimeError(f"{method} {url} exhausted retries; last status {r.status_code}: {r.text}")


# ---------- Workspaces ----------
def list_workspaces() -> list[dict]:
    out, url = [], f"{FABRIC_BASE}/workspaces"
    while url:
        r = _request("GET", url)
        body = r.json()
        out.extend(body.get("value", []))
        url = body.get("continuationUri")
    return out


def get_workspace_by_name(name: str) -> dict | None:
    for w in list_workspaces():
        if w.get("displayName") == name:
            return w
    return None


def create_workspace(display_name: str, description: str, capacity_id: str | None = None) -> dict:
    body = {"displayName": display_name, "description": description}
    if capacity_id:
        body["capacityId"] = capacity_id
    r = _request("POST", f"{FABRIC_BASE}/workspaces", json=body, expect=(201, 200))
    return r.json()


def update_workspace(workspace_id: str, *, description: str | None = None) -> None:
    body = {}
    if description is not None:
        body["description"] = description
    if not body:
        return
    _request("PATCH", f"{FABRIC_BASE}/workspaces/{workspace_id}", json=body)


def assign_to_capacity(workspace_id: str, capacity_id: str) -> None:
    _request("POST", f"{FABRIC_BASE}/workspaces/{workspace_id}/assignToCapacity",
             json={"capacityId": capacity_id})


def list_role_assignments(workspace_id: str) -> list[dict]:
    out, url = [], f"{FABRIC_BASE}/workspaces/{workspace_id}/roleAssignments"
    while url:
        r = _request("GET", url)
        body = r.json()
        out.extend(body.get("value", []))
        url = body.get("continuationUri")
    return out


def add_role_assignment(workspace_id: str, principal_id: str, principal_type: str, role: str) -> None:
    """principal_type: User | Group | ServicePrincipal ; role: Admin|Member|Contributor|Viewer"""
    body = {"principal": {"id": principal_id, "type": principal_type}, "role": role}
    _request("POST", f"{FABRIC_BASE}/workspaces/{workspace_id}/roleAssignments",
             json=body, expect=(201, 200))


# ---------- Capacities ----------
def list_capacities() -> list[dict]:
    out, url = [], f"{FABRIC_BASE}/capacities"
    while url:
        r = _request("GET", url)
        body = r.json()
        out.extend(body.get("value", []))
        url = body.get("continuationUri")
    return out


def find_capacity_id_by_display_name(display_name: str) -> str | None:
    for c in list_capacities():
        if c.get("displayName") == display_name:
            return c.get("id")
    return None


# ---------- Graph (group existence) ----------
def graph_group_exists(object_id: str) -> bool:
    headers = {"Authorization": f"Bearer {token(GRAPH_SCOPE)}"}
    r = requests.get(f"https://graph.microsoft.com/v1.0/groups/{object_id}",
                     headers=headers, timeout=30)
    return r.status_code == 200


def graph_resolve_upn(upn: str) -> str | None:
    headers = {"Authorization": f"Bearer {token(GRAPH_SCOPE)}"}
    r = requests.get(f"https://graph.microsoft.com/v1.0/users/{upn}",
                     headers=headers, timeout=30)
    if r.status_code == 200:
        return r.json().get("id")
    return None
