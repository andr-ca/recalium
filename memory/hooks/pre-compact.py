"""
PreCompact hook — flush before context window is compacted.

Identical to session-end except it fires mid-conversation (before Copilot
trims context), so the threshold is higher to avoid noisy half-done flushes.

VS Code hook input (stdin):
  { "hook_event_name": "PreCompact",
    "session_id": "...",
    "transcript_path": "/absolute/path/to/session.jsonl",
    "trigger": "manual" | "auto",
    "custom_instructions": "...",
    "timestamp": "..." }
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Recursion guard
if os.environ.get("COPILOT_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
FLUSH_SCRIPT = ROOT / "scripts" / "flush.py"

MIN_TURNS = 5  # only flush if there's enough context to be worth it


def parse_vscode_jsonl(path: Path) -> str:
    """Identical JSONL parser to session-end.py."""
    requests: list = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        kind = entry.get("kind") if isinstance(entry.get("kind"), int) else None
        value = entry.get("v", {})

        if kind == 0:
            requests = value.get("requests", [])
        elif kind == 2:
            path_key = entry.get("path", [])
            if isinstance(path_key, list) and path_key and path_key[0] == "requests":
                requests = entry.get("v", requests)
            elif isinstance(path_key, str) and path_key == "requests":
                requests = entry.get("v", requests)

    if not requests:
        return ""

    turns: list[str] = []
    for req in requests:
        if not isinstance(req, dict):
            continue

        user_text = (req.get("message") or {}).get("text", "").strip()
        if not user_text:
            continue

        response_items = req.get("response") or []
        asst_parts = [
            item["value"]
            for item in response_items
            if isinstance(item, dict)
            and item.get("kind") is None
            and item.get("value")
        ]
        asst_text = " ".join(asst_parts).strip()

        turns.append(f"Human: {user_text}")
        if asst_text:
            turns.append(f"Assistant: {asst_text}")

    return "\n\n".join(turns)


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        print("{}")
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    session_id: str = data.get("session_id", "unknown")
    transcript_path_str: str = data.get("transcript_path", "")

    if not transcript_path_str:
        print("{}")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        print("{}")
        return

    conversation = parse_vscode_jsonl(transcript_path)

    turn_count = conversation.count("\nHuman: ") + (1 if conversation.startswith("Human: ") else 0)
    if turn_count < MIN_TURNS:
        print("{}")
        return

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        prefix=f"session-flush-{session_id}-",
        dir=ROOT / "scripts",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(conversation)
        context_file = tmp.name

    env = os.environ.copy()
    env["COPILOT_INVOKED_BY"] = "memory-hook"

    subprocess.Popen(
        [
            "uv",
            "run",
            "--directory",
            str(ROOT),
            "python",
            str(FLUSH_SCRIPT),
            context_file,
            session_id,
        ],
        start_new_session=True,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("{}")


if __name__ == "__main__":
    main()
