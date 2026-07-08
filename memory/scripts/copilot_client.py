"""Shared GitHub Copilot API client for all memory scripts.

GitHub Copilot exposes an OpenAI-compatible endpoint at https://api.githubcopilot.com.

Authentication uses OAuth device registration flow:
  1. Fetch a device code from GitHub and show a URL + user code
  2. Poll until the user authorises in the browser
  3. Exchange the OAuth token for a short-lived (~30 min) Copilot session token
  4. Cache credentials in ~/.config/recalium-memory/credentials.json

On subsequent calls the cached Copilot token is reused; it is transparently
refreshed when it expires.  If `gh` CLI is already authenticated its token is
used directly to skip the interactive device flow on first run.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

# GitHub OAuth app (device-flow client used by open-source Copilot integrations)
_GH_CLIENT_ID = "Iv1.b507a08c87ecfe98"
_GH_DEVICE_CODE_URL = "https://github.com/login/device/code"
_GH_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GH_COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
_COPILOT_BASE_URL = "https://api.githubcopilot.com"

_CREDS_PATH = Path.home() / ".config" / "recalium-memory" / "credentials.json"


# ── Credential helpers ────────────────────────────────────────────────────────

def _load_creds() -> dict:
    if _CREDS_PATH.exists():
        try:
            return json.loads(_CREDS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_creds(data: dict) -> None:
    _CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CREDS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _gh_post(url: str, data: dict) -> dict:
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _gh_get_token(oauth_token: str) -> dict:
    req = urllib.request.Request(_GH_COPILOT_TOKEN_URL)
    req.add_header("Authorization", f"token {oauth_token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


# ── OAuth device flow ─────────────────────────────────────────────────────────

def _device_flow() -> str:
    """Run GitHub device flow and return an OAuth token string."""
    print("\n── GitHub Copilot: device registration ──", flush=True)

    device_resp = _gh_post(_GH_DEVICE_CODE_URL, {
        "client_id": _GH_CLIENT_ID,
        "scope": "copilot",
    })

    device_code = device_resp["device_code"]
    user_code = device_resp["user_code"]
    verification_uri = device_resp["verification_uri"]
    interval = int(device_resp.get("interval", 5))
    expires_in = int(device_resp.get("expires_in", 900))

    print(f"\nOpen: {verification_uri}", flush=True)
    print(f"Code: {user_code}\n", flush=True)

    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)
        poll = _gh_post(_GH_OAUTH_TOKEN_URL, {
            "client_id": _GH_CLIENT_ID,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        error = poll.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error == "expired_token":
            raise RuntimeError("Device code expired — please restart and authorise faster")
        if error:
            raise RuntimeError(f"OAuth error: {error} — {poll.get('error_description', '')}")
        token = poll.get("access_token", "")
        if token:
            print("Authorised.", flush=True)
            return token

    raise RuntimeError("Device flow timed out")


def _gh_cli_token() -> str | None:
    """Return a GitHub OAuth token from `gh auth token` if available."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        token = result.stdout.strip()
        if token and not token.startswith("Error"):
            return token
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


# ── Session token management ──────────────────────────────────────────────────

def _is_copilot_token_valid(creds: dict) -> bool:
    exp = creds.get("copilot_token_expires_at", "")
    if not exp:
        return False
    try:
        expiry = datetime.fromisoformat(exp)
        # Refresh 60 seconds early to avoid edge-case expiry mid-request
        return datetime.now(timezone.utc) < expiry.replace(tzinfo=timezone.utc) - __import__("datetime").timedelta(seconds=60)
    except (ValueError, AttributeError):
        return False


def _get_oauth_token(creds: dict) -> str:
    """Return a valid GitHub OAuth token (device flow or gh CLI)."""
    saved = creds.get("oauth_token", "")
    if saved:
        return saved

    # Try gh CLI first — no user interaction required
    gh_token = _gh_cli_token()
    if gh_token:
        return gh_token

    # Interactive device flow
    return _device_flow()


def get_copilot_token() -> str:
    """Return a valid Copilot session token, refreshing as needed."""
    creds = _load_creds()

    if _is_copilot_token_valid(creds):
        return creds["copilot_token"]

    oauth_token = _get_oauth_token(creds)

    token_data = _gh_get_token(oauth_token)
    copilot_token = token_data.get("token", "")
    if not copilot_token:
        raise RuntimeError(
            f"Copilot token exchange failed: {token_data}. "
            "Make sure your GitHub account has an active Copilot subscription."
        )

    expires_at = token_data.get("expires_at", "")

    _save_creds({
        "oauth_token": oauth_token,
        "copilot_token": copilot_token,
        "copilot_token_expires_at": expires_at,
    })

    return copilot_token


# ── OpenAI-compatible client ──────────────────────────────────────────────────

def get_client():
    """Return a configured OpenAI client pointed at the GitHub Copilot API."""
    from openai import OpenAI

    token = get_copilot_token()

    return OpenAI(
        api_key=token,
        base_url=_COPILOT_BASE_URL,
        default_headers={
            "Copilot-Integration-Id": "vscode-chat",
            "editor-version": "vscode/1.90.0",
            "editor-plugin-version": "copilot-chat/0.20.0",
        },
    )


def chat(model: str, prompt: str, max_tokens: int = 2048) -> str:
    """Send a single-turn chat message and return the response text."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
