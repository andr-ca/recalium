#!/usr/bin/env python3
"""
Claude Code SessionStart hook.
Retrieves relevant memory when a session starts.
"""

import json
import os
import sys
from pathlib import Path

# Add parent dir to path to import recalium_client
sys.path.insert(0, str(Path(__file__).parent.parent))

from recalium_client import RecaliumClient, source_label


def format_items(items, max_chars=2000):
    """Format retrieved items with source provenance."""
    if not items:
        return ""

    formatted = []
    total_chars = 0

    for item in items:
        source = source_label(item)
        captured = item.get("captured_at", "")
        content = item.get("content", "")

        entry = f"- [{source}] {content}"
        if captured:
            entry += f" (captured: {captured})"

        if total_chars + len(entry) > max_chars:
            break

        formatted.append(entry)
        total_chars += len(entry)

    return "\n".join(formatted)


def main():
    """Process SessionStart hook."""
    # Recursion guard
    if os.environ.get("RECALIUM_HOOK_ACTIVE"):
        return {}

    try:
        # Read stdin
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return {}

    # Set recursion guard
    os.environ["RECALIUM_HOOK_ACTIVE"] = "1"

    # Extract project dir for query. Claude Code hook JSON provides `cwd`
    # (there is no `workspacePath`); fall back to the process cwd.
    workspace_path = hook_input.get("cwd") or os.getcwd()
    query = "recent context"
    if workspace_path:
        query = Path(workspace_path).name or "recent context"

    # Retrieve memory
    client = RecaliumClient()
    result = client.retrieve(query, mode="hybrid", budget=1536, limit=3)

    if not result or "items" not in result:
        return {}

    items = result.get("items", [])
    if not items:
        return {}

    # Format output
    formatted = format_items(items)
    if not formatted:
        return {}

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": formatted,
        }
    }

    return output


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
