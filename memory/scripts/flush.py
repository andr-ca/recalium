"""
Memory flush agent — extracts important knowledge from conversation context.

Spawned by session-end.py or pre-compact.py as a background process.
Reads pre-extracted conversation context from a .md file, uses the Anthropic API
to decide what's worth saving, and appends the result to today's daily log.

Usage:
    uv run --directory memory python memory/scripts/flush.py <context_file.md> <session_id>
"""

from __future__ import annotations

# Recursion prevention: set this BEFORE any imports that might trigger Copilot
import os
os.environ["COPILOT_INVOKED_BY"] = "memory_flush"

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Load .env from project root (two levels up from scripts/)
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
SCRIPTS_DIR = ROOT / "scripts"
STATE_FILE = SCRIPTS_DIR / "last-flush.json"
LOG_FILE = SCRIPTS_DIR / "flush.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def load_flush_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_flush_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def append_to_daily_log(content: str, section: str = "Session") -> None:
    """Append content to today's daily log."""
    today = datetime.now(timezone.utc).astimezone()
    log_path = DAILY_DIR / f"{today.strftime('%Y-%m-%d')}.md"

    if not log_path.exists():
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"# Daily Log: {today.strftime('%Y-%m-%d')}\n\n## Sessions\n\n## Memory Maintenance\n\n",
            encoding="utf-8",
        )

    time_str = today.strftime("%H:%M")
    entry = f"### {section} ({time_str})\n\n{content}\n\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


def run_flush(context: str) -> str:
    """Use GitHub Copilot API to extract important knowledge from conversation context."""
    import sys
    sys.path.insert(0, str(SCRIPTS_DIR))
    from config import MODEL_FLUSH
    from copilot_client import chat

    prompt = f"""Review the conversation context below and respond with a concise summary of
important items that should be preserved in the daily log.
Do NOT include tool invocations, file reads, or routine code edits — only meaningful decisions, lessons, and insights.

Format your response as a structured daily log entry with these sections:

**Context:** [One line about what the user was working on]

**Key Exchanges:**
- [Important Q&A or discussions]

**Decisions Made:**
- [Any decisions with rationale]

**Lessons Learned:**
- [Gotchas, patterns, or insights discovered]

**Action Items:**
- [Follow-ups or TODOs mentioned]

Skip anything that is:
- Routine tool calls or file reads
- Content that is trivial or obvious
- Trivial back-and-forth or clarification exchanges

Only include sections that have actual content. If nothing is worth saving,
respond with exactly:
FLUSH_OK

## Conversation Context

{context}"""

    try:
        return chat(MODEL_FLUSH, prompt, max_tokens=2048)
    except Exception as e:
        import traceback
        logging.error("Copilot API error: %s\n%s", e, traceback.format_exc())
        return f"FLUSH_ERROR: {type(e).__name__}: {e}"


def maybe_trigger_compilation() -> None:
    """If it's past the compile hour and today's log hasn't been compiled, run compile.py."""
    from config import COMPILE_AFTER_HOUR

    now = datetime.now(timezone.utc).astimezone()
    if now.hour < COMPILE_AFTER_HOUR:
        return

    today_log = f"{now.strftime('%Y-%m-%d')}.md"
    compile_state_file = SCRIPTS_DIR / "state.json"
    if compile_state_file.exists():
        try:
            compile_state = json.loads(compile_state_file.read_text(encoding="utf-8"))
            ingested = compile_state.get("ingested", {})
            if today_log in ingested:
                from hashlib import sha256
                log_path = DAILY_DIR / today_log
                if log_path.exists():
                    current_hash = sha256(log_path.read_bytes()).hexdigest()[:16]
                    if ingested[today_log].get("hash") == current_hash:
                        return  # log unchanged since last compile
        except (json.JSONDecodeError, OSError):
            pass

    compile_script = SCRIPTS_DIR / "compile.py"
    if not compile_script.exists():
        return

    logging.info("End-of-day compilation triggered (after %d:00)", COMPILE_AFTER_HOUR)

    cmd = ["uv", "run", "--directory", str(ROOT), "python", str(compile_script)]

    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True

    try:
        log_handle = open(str(SCRIPTS_DIR / "compile.log"), "a")
        subprocess.Popen(cmd, stdout=log_handle, stderr=subprocess.STDOUT, cwd=str(ROOT), **kwargs)
    except Exception as e:
        logging.error("Failed to spawn compile.py: %s", e)


def main():
    if len(sys.argv) < 3:
        logging.error("Usage: %s <context_file.md> <session_id>", sys.argv[0])
        sys.exit(1)

    context_file = Path(sys.argv[1])
    session_id = sys.argv[2]

    logging.info("flush.py started for session %s, context: %s", session_id, context_file)

    if not context_file.exists():
        logging.error("Context file not found: %s", context_file)
        return

    # Deduplication: skip if same session was flushed within 60 seconds
    state = load_flush_state()
    if (
        state.get("session_id") == session_id
        and time.time() - state.get("timestamp", 0) < 60
    ):
        logging.info("Skipping duplicate flush for session %s", session_id)
        context_file.unlink(missing_ok=True)
        return

    context = context_file.read_text(encoding="utf-8").strip()
    if not context:
        logging.info("Context file is empty, skipping")
        context_file.unlink(missing_ok=True)
        return

    logging.info("Flushing session %s: %d chars", session_id, len(context))

    response = run_flush(context)

    if "FLUSH_OK" in response:
        logging.info("Result: FLUSH_OK")
        append_to_daily_log("FLUSH_OK - Nothing worth saving from this session", "Memory Flush")
    elif "FLUSH_ERROR" in response:
        logging.error("Result: %s", response)
        append_to_daily_log(response, "Memory Flush")
    else:
        logging.info("Result: saved to daily log (%d chars)", len(response))
        append_to_daily_log(response, "Session")

    save_flush_state({"session_id": session_id, "timestamp": time.time()})
    context_file.unlink(missing_ok=True)
    maybe_trigger_compilation()
    logging.info("Flush complete for session %s", session_id)


if __name__ == "__main__":
    main()
