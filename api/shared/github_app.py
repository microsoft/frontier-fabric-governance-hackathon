"""GitHub App authentication helper.

Mints a JWT signed with the GitHub App private key, exchanges it for an
installation access token, and exposes a small `create_pull_request` helper
used by the Azure Function `/submit` endpoint.

Why a GitHub App (not a PAT or user OAuth)?
- Per-installation scopes (only this repo) instead of full-user access.
- Short-lived installation tokens (1 hour) instead of long-lived PATs.
- Auditable: PRs are authored by the App, not an individual employee.

The private key (PEM) is loaded from Azure Key Vault via Managed Identity.
The app id and installation id come from App Settings.
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import jwt  # PyJWT
import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

GITHUB_API = "https://api.github.com"


@dataclass
class GitHubAppConfig:
    app_id: str
    installation_id: str
    owner: str
    repo: str
    base_branch: str
    private_key_pem: str

    @classmethod
    def from_env(cls) -> "GitHubAppConfig":
        kv_url = os.environ["KEY_VAULT_URL"]
        secret_name = os.environ.get("GITHUB_PRIVATE_KEY_SECRET", "github-app-private-key")
        client = SecretClient(vault_url=kv_url, credential=DefaultAzureCredential())
        pem = client.get_secret(secret_name).value or ""
        return cls(
            app_id=os.environ["GITHUB_APP_ID"],
            installation_id=os.environ["GITHUB_INSTALLATION_ID"],
            owner=os.environ["GITHUB_OWNER"],
            repo=os.environ["GITHUB_REPO"],
            base_branch=os.environ.get("GITHUB_BASE_BRANCH", "main"),
            private_key_pem=pem,
        )


def _mint_jwt(cfg: GitHubAppConfig) -> str:
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 9 * 60, "iss": cfg.app_id}
    return jwt.encode(payload, cfg.private_key_pem, algorithm="RS256")


def installation_token(cfg: GitHubAppConfig) -> str:
    app_jwt = _mint_jwt(cfg)
    r = requests.post(
        f"{GITHUB_API}/app/installations/{cfg.installation_id}/access_tokens",
        headers={"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["token"]


def _gh(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_default_sha(token: str, cfg: GitHubAppConfig) -> str:
    r = requests.get(
        f"{GITHUB_API}/repos/{cfg.owner}/{cfg.repo}/git/ref/heads/{cfg.base_branch}",
        headers=_gh(token), timeout=15,
    )
    r.raise_for_status()
    return r.json()["object"]["sha"]


def _create_branch(token: str, cfg: GitHubAppConfig, branch: str, sha: str) -> None:
    r = requests.post(
        f"{GITHUB_API}/repos/{cfg.owner}/{cfg.repo}/git/refs",
        headers=_gh(token),
        json={"ref": f"refs/heads/{branch}", "sha": sha},
        timeout=15,
    )
    if r.status_code not in (201, 422):  # 422 if branch already exists
        r.raise_for_status()


def _put_file(token: str, cfg: GitHubAppConfig, branch: str, path: str,
              content: str, message: str) -> None:
    body: dict[str, Any] = {
        "message": message,
        "branch": branch,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    # If the file already exists on the branch, we need its sha to update.
    head = requests.get(
        f"{GITHUB_API}/repos/{cfg.owner}/{cfg.repo}/contents/{path}",
        headers=_gh(token), params={"ref": branch}, timeout=15,
    )
    if head.status_code == 200:
        body["sha"] = head.json()["sha"]
    r = requests.put(
        f"{GITHUB_API}/repos/{cfg.owner}/{cfg.repo}/contents/{path}",
        headers=_gh(token), json=body, timeout=20,
    )
    r.raise_for_status()


def _open_pull_request(token: str, cfg: GitHubAppConfig, branch: str,
                       title: str, body: str) -> dict[str, Any]:
    r = requests.post(
        f"{GITHUB_API}/repos/{cfg.owner}/{cfg.repo}/pulls",
        headers=_gh(token),
        json={"title": title, "head": branch, "base": cfg.base_branch, "body": body},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def create_pull_request(
    *,
    file_path: str,
    file_content: str,
    branch: str,
    pr_title: str,
    pr_body: str,
    commit_message: str,
) -> dict[str, Any]:
    """End-to-end: branch from base, write file, open PR. Returns the PR JSON."""
    cfg = GitHubAppConfig.from_env()
    token = installation_token(cfg)
    base_sha = _get_default_sha(token, cfg)
    _create_branch(token, cfg, branch, base_sha)
    _put_file(token, cfg, branch, file_path, file_content, commit_message)
    return _open_pull_request(token, cfg, branch, pr_title, pr_body)
