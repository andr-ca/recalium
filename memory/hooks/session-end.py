"""
Stop / session-end hook — extracts the finished conversation and flushes it.

Reads the VS Code Copilot session JSONL, extracts user+assistant turns,
writes a temp context file, and spawns flush.py in the background so the
hook returns immediately.

VS Code hook input (stdin):
  { "hook_event_name": "Stop",
    "session_id": "...",
    "transcript_path": "/absolute/path/to/session.jsonl",
    "stop_hook_active": true | false,
    "timestamp": "..." }

VS Code hook output (stdout):
  { } — empty object (background flush; output is not used by Copilot)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Recursion guard — prevents hooks calling hooks
if os.environ.get("COPILOT_INVOKED_BY"):
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
FLUSH_SCRIPT = ROOT / "scripts" / "flush.py"

MIN_TURNS = 1  # minimum user turns before triggering flush


def parse_vscode_jsonl(path: Path) -> str:
    """
    Parse a VS Code Copilot session JSONL file and extract conversation text.

    VS Code JSONL format:
      kind=0  initial snapshot: v.requests = []
      kind=1  single key-path patch
      kind=2  full replacement of requests array

    For each request in the final requests array:
      user_text  = request["message"]["text"]
      asst_text  = " ".join(item["value"] for item in request["response"]
                            if item.get("kind") is None and item.get("value"))
    """
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
            # Initial snapshot
            requests = value.get("requests", [])
        elif kind == 2:
            # Full replacement patch — key is the path, value is the new content
            # VS Code encodes this as {"kind":2, "op":..., "path":["requests"], "v":[...]}
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

    # Count user turns
    turn_count = conversation.count("\nHuman: ") + (1 if conversation.startswith("Human: ") else 0)
    if turn_count < MIN_TURNS:
        print("{}")
        return

    # Write context to a temp file so flush.py can read it after hook returns
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

    # Spawn flush.py as a detached background process
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
