"""Preflight checks before running eval checks against a live stack."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Tuple

import httpx


async def preflight_extraction_provider(
    client: httpx.AsyncClient,
    base_url: str,
) -> Tuple[bool, str]:
    """
    Verify the server reports a configured extraction provider and Ollama (if used)
    is reachable with the configured model when eval can probe it.

    Returns (ok, message). On failure, message is suitable for stderr + exit.
    """
    try:
        keys_resp = await client.get(f"{base_url}/api/settings/keys", timeout=5.0)
        if keys_resp.status_code != 200:
            return False, f"GET /api/settings/keys returned {keys_resp.status_code}"
        keys = keys_resp.json()
    except Exception as exc:
        return False, f"Cannot read provider configuration: {exc}"

    providers = keys if isinstance(keys, dict) else {}
    configured = [
        name
        for name in ("openai", "anthropic", "ollama")
        if providers.get(name, {}).get("configured")
    ]
    if not configured:
        return (
            False,
            "No LLM provider configured on the server — set OPENAI_API_KEY, "
            "ANTHROPIC_API_KEY, or OLLAMA_BASE_URL in the app's .env",
        )

    ollama = providers.get("ollama", {})
    if ollama.get("configured"):
        base = (ollama.get("base_url") or "http://localhost:11434").rstrip("/")
        probe_url = _ollama_probe_url(base)
        model = _expected_ollama_model()
        try:
            tags_resp = await client.get(f"{probe_url}/api/tags", timeout=10.0)
            if tags_resp.status_code != 200:
                return (
                    False,
                    f"Ollama endpoint not reachable from eval host at {probe_url} "
                    f"(HTTP {tags_resp.status_code}). Fix OLLAMA_BASE_URL / model install.",
                )
            names = {m.get("name") for m in tags_resp.json().get("models", [])}
            if model not in names:
                return (
                    False,
                    f"Ollama model '{model}' is not installed (available: {sorted(names)[:5]}...). "
                    f"Run `ollama pull {model}` or set OLLAMA_MODEL to an installed model.",
                )
        except httpx.RequestError as exc:
            return (
                False,
                f"Cannot reach Ollama at {probe_url} from eval host: {exc}. "
                "If the app uses a Docker-only URL, ensure Ollama is reachable for extraction.",
            )

    return True, "Provider preflight OK"


def _ollama_probe_url(base_url: str) -> str:
    """Map container-internal Ollama URLs to localhost when probing from the host."""
    if base_url.startswith("http://172.") or base_url.startswith("http://192.168."):
        return "http://localhost:11434"
    return base_url.rstrip("/")


def _expected_ollama_model() -> str:
    """Read OLLAMA_MODEL from env / repo .env files (local eval).

    Order: process env → repo root .env (docker compose) → backend/.env (native dev).
    """
    if os.getenv("OLLAMA_MODEL"):
        return os.getenv("OLLAMA_MODEL", "")
    repo_root = Path(__file__).resolve().parents[1]
    for env_path in (repo_root / ".env", repo_root / "backend" / ".env"):
        if env_path.is_file():
            for line in env_path.read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith("OLLAMA_MODEL=") and not stripped.startswith("#"):
                    return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return "llama3.2"
