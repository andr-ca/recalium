#!/usr/bin/env python3
"""
Claude Code UserPromptSubmit hook.
Injects relevant memory based on the user's prompt.
"""

import json
import os
import sys
from pathlib import Path

# Add parent dir to path to import recalium_client
sys.path.insert(0, str(Path(__file__).parent.parent))

from recalium_client import RecaliumClient


def format_items(items, max_chars=1500):
    """Format retrieved items with source provenance."""
    if not items:
        return ""

    formatted = []
    total_chars = 0

    for item in items:
        source = item.get("source_name", "unknown")
        content = item.get("content", "")[:200]  # Truncate per item

        entry = f"• [{source}] {content}"

        if total_chars + len(entry) > max_chars:
            break

        formatted.append(entry)
        total_chars += len(entry)

    return "\n".join(formatted)


def main():
    """Process UserPromptSubmit hook."""
    # Recursion guard
    if os.environ.get("RECALIUM_HOOK_ACTIVE"):
        return {}

    try:
        # Read stdin
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return {}

    # Extract prompt
    prompt = hook_input.get("prompt", "").strip()

    # Skip trivially short prompts
    if len(prompt) < 15:
        return {}

    # Set recursion guard
    os.environ["RECALIUM_HOOK_ACTIVE"] = "1"

    # Retrieve memory based on prompt
    client = RecaliumClient()
    result = client.retrieve(prompt, mode="hybrid", budget=1024, limit=3)

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
            "hookEventName": "UserPromptSubmit",
            "additionalContext": formatted,
        }
    }

    return output


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
