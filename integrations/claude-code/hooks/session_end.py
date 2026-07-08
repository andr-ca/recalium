#!/usr/bin/env python3
"""
Claude Code SessionEnd/Stop hook.
Extracts and archives the session transcript.
Uses background subprocess for ingestion (non-blocking).
Idempotency via marker file at ~/.recalium/ingested/{session_id}.
"""

import json
import os
import sys
import subprocess
from pathlib import Path

# Add parent dir to path to import recalium_client
sys.path.insert(0, str(Path(__file__).parent.parent))

from recalium_client import RecaliumClient


def extract_transcript(transcript_path):
    """
    Extract conversation from Claude Code transcript JSONL.
    Format: {"type": "user|assistant", "message": {"content": ...}}
    """
    transcript = []

    try:
        if not Path(transcript_path).exists():
            return ""

        with open(transcript_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("type", "")
                message = entry.get("message", {})

                if entry_type == "user":
                    content = message.get("content", "")
                    if content:
                        transcript.append(f"User: {content}")

                elif entry_type == "assistant":
                    content = message.get("content", [])
                    text_parts = []

                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                    elif isinstance(content, str):
                        text_parts.append(content)

                    if text_parts:
                        full_text = " ".join(text_parts)
                        transcript.append(f"Assistant: {full_text}")

    except Exception:
        pass

    return "\n\n".join(transcript)


def is_ingested(session_id):
    """Check if session has already been ingested (marker file exists)."""
    marker_dir = Path.home() / ".recalium" / "ingested"
    marker_file = marker_dir / session_id

    return marker_file.exists()


def mark_ingested(session_id):
    """Create marker file to prevent duplicate ingestion."""
    marker_dir = Path.home() / ".recalium" / "ingested"

    try:
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker_file = marker_dir / session_id
        marker_file.touch()
    except Exception:
        pass


def ingest_in_background(content, source_name, session_id):
    """
    Spawn background subprocess to ingest content.
    Subprocess sets RECALIUM_HOOK_ACTIVE and creates marker file.
    """
    ingest_script = f"""
import json
import os
import sys
from pathlib import Path

# Set recursion guard
os.environ["RECALIUM_HOOK_ACTIVE"] = "1"

# Add parent dir to path
sys.path.insert(0, {repr(str(Path(__file__).parent.parent))})

from recalium_client import RecaliumClient

try:
    client = RecaliumClient()
    result = client.ingest({repr(content)}, {repr(source_name)})

    # Create marker file after successful ingest
    if result and result.get("status") == "accepted":
        marker_dir = Path.home() / ".recalium" / "ingested"
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / {repr(session_id)}).touch()
except Exception:
    pass
"""

    try:
        subprocess.Popen(
            [sys.executable, "-c", ingest_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main():
    """Process SessionEnd hook."""
    # Recursion guard
    if os.environ.get("RECALIUM_HOOK_ACTIVE"):
        return {}

    try:
        # Read stdin
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return {}

    # Extract fields. Claude Code hook JSON is snake_case:
    # session_id, transcript_path, cwd (there is no sessionId/transcriptPath/workspacePath).
    session_id = hook_input.get("session_id", "")
    transcript_path = hook_input.get("transcript_path", "")
    workspace_path = hook_input.get("cwd", "")

    if not session_id or not transcript_path:
        return {}

    # Check idempotency
    if is_ingested(session_id):
        return {}

    # Extract transcript
    content = extract_transcript(transcript_path)
    if not content or len(content.strip()) < 50:
        return {}

    # Derive source name
    source_name = "Claude Code"
    if workspace_path:
        source_name = f"Claude Code — {Path(workspace_path).name}"

    # Spawn background ingest process
    ingest_in_background(content, source_name, session_id)

    # Return immediately (don't wait for background process)
    return {}


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
