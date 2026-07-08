#!/usr/bin/env python3
"""
Claude Code ↔ Recalium CLI.
Manual recall and remember commands for terminal use.

Usage:
  python3 cli.py recall "topic to search"
  python3 cli.py remember "text to remember"
  python3 cli.py remember @path/to/file.txt
"""

import argparse
import sys
from pathlib import Path

# Add current dir to path to import recalium_client
sys.path.insert(0, str(Path(__file__).parent))

from recalium_client import RecaliumClient


def format_result(item, index):
    """Format a single result for display."""
    source = item.get("source_name", "unknown")
    content = item.get("content", "")[:300]  # Truncate for readability
    score = item.get("score", "")

    score_str = ""
    if score:
        score_str = f" (score: {score:.2f})" if isinstance(score, float) else f" (score: {score})"

    return f"{index}. [{source}]{score_str}\n   {content}"


def recall(query):
    """Retrieve and display memory items."""
    print(f"Searching for: {query}\n")

    client = RecaliumClient()
    result = client.retrieve(query, mode="hybrid", limit=10)

    if not result:
        print("ERROR: Could not reach Recalium. Is it running at http://localhost:8000?")
        return 1

    items = result.get("items", [])
    if not items:
        print("No results found.")
        return 0

    degraded = result.get("degraded_mode", False)
    if degraded:
        print("[NOTE: Search degraded (semantic search unavailable)]")

    print(f"Found {len(items)} item(s):\n")

    for i, item in enumerate(items, 1):
        print(format_result(item, i))
        print()

    return 0


def remember(text):
    """Ingest content into memory."""
    # Check if text is a file reference
    if text.startswith("@"):
        file_path = Path(text[1:])
        if not file_path.exists():
            print(f"ERROR: File not found: {file_path}")
            return 1

        try:
            with open(file_path, "r") as f:
                content = f.read()
        except Exception as e:
            print(f"ERROR: Could not read file: {e}")
            return 1

        source_name = f"Claude Code — {file_path.name}"
    else:
        content = text
        source_name = "Claude Code — CLI"

    print(f"Ingesting {len(content)} characters...\n")

    client = RecaliumClient()
    result = client.ingest(content, source_name)

    if not result:
        print("ERROR: Could not reach Recalium. Is it running at http://localhost:8000?")
        return 1

    if result.get("status") == "accepted":
        item_count = result.get("item_count", 0)
        archive_ids = result.get("archive_ids", [])
        print(f"SUCCESS: Ingested {item_count} item(s)")
        if archive_ids:
            print(f"Archive IDs: {', '.join(archive_ids[:5])}")
        return 0
    else:
        error_msg = result.get("error", {}).get("message", "Unknown error")
        print(f"ERROR: {error_msg}")
        return 1


def main():
    """Main CLI handler."""
    parser = argparse.ArgumentParser(
        description="Claude Code ↔ Recalium integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 cli.py recall "topic to search"
  python3 cli.py remember "text to remember"
  python3 cli.py remember @path/to/file.txt""",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # recall command
    recall_parser = subparsers.add_parser("recall", help="Retrieve memory items")
    recall_parser.add_argument("query", help="Search query")

    # remember command
    remember_parser = subparsers.add_parser("remember", help="Store text in memory")
    remember_parser.add_argument(
        "text", help="Text to remember, or @path/to/file.txt to load from file"
    )

    args = parser.parse_args()

    if args.command == "recall":
        return recall(args.query)
    elif args.command == "remember":
        return remember(args.text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
