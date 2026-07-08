"""Path constants and configuration for the personal knowledge base."""

from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT_DIR / "daily"
KNOWLEDGE_DIR = ROOT_DIR / "knowledge"
CONCEPTS_DIR = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR = KNOWLEDGE_DIR / "connections"
QA_DIR = KNOWLEDGE_DIR / "qa"
REPORTS_DIR = ROOT_DIR / "reports"
SCRIPTS_DIR = ROOT_DIR / "scripts"
HOOKS_DIR = ROOT_DIR / "hooks"
AGENTS_FILE = ROOT_DIR / "AGENTS.md"

INDEX_FILE = KNOWLEDGE_DIR / "index.md"
LOG_FILE = KNOWLEDGE_DIR / "log.md"
STATE_FILE = SCRIPTS_DIR / "state.json"

# ── Models ─────────────────────────────────────────────────────────────────
import os as _os

# GitHub Copilot model IDs (OpenAI-compatible endpoint)
MODEL_FLUSH = _os.environ.get("MEMORY_MODEL_FLUSH", "gpt-4o-mini")
MODEL_COMPILE = _os.environ.get("MEMORY_MODEL_COMPILE", "gpt-4o")
MODEL_QUERY = _os.environ.get("MEMORY_MODEL_QUERY", "gpt-4o-mini")
MODEL_LINT = _os.environ.get("MEMORY_MODEL_LINT", "gpt-4o-mini")

# ── Compile trigger hour (end-of-day auto-compile) ─────────────────────────
COMPILE_AFTER_HOUR = int(_os.environ.get("MEMORY_COMPILE_AFTER_HOUR", "18"))


def now_iso() -> str:
    """Current time in ISO 8601 format."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in ISO 8601 format."""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
