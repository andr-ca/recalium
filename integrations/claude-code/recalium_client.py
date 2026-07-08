#!/usr/bin/env python3
"""
Recalium HTTP client for Claude Code integration.
Stdlib-only; fail-soft error handling; config via .env only.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import socket
from pathlib import Path
from typing import Optional


def load_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Load env var from OS environment or .env file.
    Search for .env in: cwd, parent dirs, repo root.
    """
    # Check OS environment first
    if var_name in os.environ:
        return os.environ[var_name]

    # Search for .env file
    search_paths = [
        Path.cwd(),
        Path.cwd().parent,
        Path.cwd().parent.parent,
        Path.cwd().parent.parent.parent,
    ]

    for search_dir in search_paths:
        env_file = search_dir / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, value = line.split("=", 1)
                            if key.strip() == var_name:
                                return value.strip()
            except Exception:
                pass

    return default


def source_label(item: dict) -> str:
    """Human-readable provenance label for a retrieved item.

    The /api/retrieve response items expose `source_system` and `type`
    (there is no `source_name` field), so build the label from those.
    """
    parts = [p for p in (item.get("source_system"), item.get("type")) if p]
    return " · ".join(str(p) for p in parts) if parts else "memory"


class RecaliumClient:
    """HTTP client for Recalium API with fail-soft error handling."""

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        timeout_s: Optional[float] = None,
    ):
        """
        Initialize client.

        Args:
            url: Recalium base URL (default: http://localhost:8000)
            token: Optional bearer token
            timeout_s: Request timeout in seconds (default: 5)
        """
        self.url = url or load_env("RECALIUM_URL", "http://localhost:8000")
        self.token = token or load_env("RECALIUM_TOKEN")

        timeout_str = timeout_s or load_env("RECALIUM_TIMEOUT_S", "5")
        try:
            self.timeout_s = float(timeout_str)
        except (ValueError, TypeError):
            self.timeout_s = 5.0

    def _make_request(self, path: str, data: dict) -> Optional[dict]:
        """
        Make POST request to Recalium API.
        Returns response dict or None on any error (fail-soft).
        """
        try:
            url = f"{self.url}{path}"
            body = json.dumps(data).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            # Add bearer token if present
            if self.token:
                req.add_header("Authorization", f"Bearer {self.token}")

            with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                return response_data

        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout) as e:
            # Log to stderr for debugging, but don't raise
            print(f"Recalium request failed: {path} — {type(e).__name__}", file=sys.stderr)
            return None
        except (json.JSONDecodeError, OSError) as e:
            print(f"Recalium request error: {type(e).__name__}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Unexpected error in Recalium request: {type(e).__name__}", file=sys.stderr)
            return None

    def retrieve(
        self,
        query: str,
        mode: str = "hybrid",
        budget: int = 4096,
        limit: int = 10,
        filters: Optional[dict] = None,
        actor: str = "claude-code",
    ) -> Optional[dict]:
        """
        Retrieve memory items from Recalium.

        Returns response dict with 'items' key or None on error.
        """
        request_data = {
            "query": query,
            "mode": mode,
            "budget": budget,
            "limit": limit,
            "actor": actor,
        }
        if filters:
            request_data["filters"] = filters

        return self._make_request("/api/retrieve", request_data)

    def ingest(self, content: str, source_name: str) -> Optional[dict]:
        """
        Ingest content into Recalium.

        Returns response dict or None on error.
        """
        request_data = {
            "mode": "text",
            "content": content,
            "source_name": source_name,
        }

        return self._make_request("/api/ingest", request_data)
