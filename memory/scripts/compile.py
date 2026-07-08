"""
Compile daily conversation logs into structured knowledge articles.

This is the "LLM compiler" — it reads daily logs (source) and produces
organised knowledge articles (the output).

Instead of using a tool-use loop (like the original Claude Agent SDK version)
it sends one structured prompt and parses the JSON response to write files
directly.

Usage:
    uv run python scripts/compile.py                     # compile new/changed logs only
    uv run python scripts/compile.py --all               # force recompile everything
    uv run python scripts/compile.py --file daily/YYYY-MM-DD.md
    uv run python scripts/compile.py --dry-run           # show what would be compiled
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from config import (
    AGENTS_FILE,
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    DAILY_DIR,
    KNOWLEDGE_DIR,
    MODEL_COMPILE,
    now_iso,
)
from utils import (
    file_hash,
    list_raw_files,
    list_wiki_articles,
    load_state,
    read_wiki_index,
    save_state,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def compile_daily_log(log_path: Path, state: dict) -> None:
    """Compile a single daily log into knowledge articles."""
    from copilot_client import chat

    log_content = log_path.read_text(encoding="utf-8")
    schema = AGENTS_FILE.read_text(encoding="utf-8") if AGENTS_FILE.exists() else ""
    wiki_index = read_wiki_index()

    # Read existing articles for context
    existing_articles_context = ""
    existing: dict[str, str] = {}
    for article_path in list_wiki_articles():
        rel = article_path.relative_to(KNOWLEDGE_DIR)
        existing[str(rel)] = article_path.read_text(encoding="utf-8")

    if existing:
        parts = []
        for rel_path, content in existing.items():
            parts.append(f"### {rel_path}\n```markdown\n{content}\n```")
        existing_articles_context = "\n\n".join(parts)

    timestamp = now_iso()

    prompt = f"""You are a knowledge compiler. Read the daily conversation log below and
extract knowledge into structured wiki articles. Respond with a single JSON object.

## Schema (AGENTS.md)

{schema}

## Current Wiki Index

{wiki_index}

## Existing Wiki Articles

{existing_articles_context if existing_articles_context else "(No existing articles yet)"}

## Daily Log to Compile

**File:** {log_path.name}

{log_content}

## Your Task

Read the daily log and compile it into wiki articles following the schema exactly.

### Rules:

1. Extract 3-7 distinct concepts worth their own article.
2. Create concept articles in `knowledge/concepts/` — one per concept.
   - Use the exact article format from AGENTS.md (YAML frontmatter + sections).
   - Include `sources:` in frontmatter pointing to the daily log file.
   - Use `[[concepts/slug]]` wikilinks to link to related concepts.
   - Write in encyclopedia style — neutral, comprehensive.
3. Create connection articles in `knowledge/connections/` if the log reveals
   non-obvious relationships between 2+ existing concepts.
4. Update existing articles if the log adds new information.
5. Return a log entry for `knowledge/log.md`.

### Response format (JSON only, no markdown fences):

{{
  "articles": [
    {{
      "path": "knowledge/concepts/my-concept.md",
      "action": "create" | "update",
      "content": "<full markdown content including frontmatter>"
    }}
  ],
  "index_rows": [
    "| [[concepts/slug]] | One-line summary | {log_path.name} | {timestamp[:10]} |"
  ],
  "log_entry": "## [{timestamp}] compile | {log_path.name}\\n- Source: daily/{log_path.name}\\n- Articles: ..."
}}

If nothing in the log is worth compiling respond with:
{{"articles": [], "index_rows": [], "log_entry": "## [{timestamp}] compile | {log_path.name}\\n- Nothing worth compiling."}}
"""

    print(f"  Calling Copilot API (model: {MODEL_COMPILE})…", flush=True)
    raw = chat(MODEL_COMPILE, prompt, max_tokens=4096)

    # Strip any markdown code fences the model may add
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.rstrip())

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  Warning: could not parse JSON response ({exc}); skipping.", flush=True)
        return

    articles = result.get("articles", [])
    index_rows = result.get("index_rows", [])
    log_entry = result.get("log_entry", "")

    # Write / update articles
    for article in articles:
        path = ROOT_DIR / article["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        content = article.get("content", "")
        if article.get("action") == "update" and path.exists():
            existing_text = path.read_text(encoding="utf-8")
            # Simple merge: replace if content provided, otherwise skip
            if content:
                path.write_text(content, encoding="utf-8")
                print(f"    Updated: {article['path']}", flush=True)
        elif content:
            path.write_text(content, encoding="utf-8")
            print(f"    Created: {article['path']}", flush=True)

    # Update index.md
    if index_rows:
        index_path = KNOWLEDGE_DIR / "index.md"
        if not index_path.exists():
            KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                "# Knowledge Base Index\n\n"
                "| Article | Summary | Source | Date |\n"
                "|---------|---------|--------|------|\n",
                encoding="utf-8",
            )
        with open(index_path, "a", encoding="utf-8") as f:
            for row in index_rows:
                f.write(row + "\n")

    # Append to log.md
    if log_entry:
        log_md = KNOWLEDGE_DIR / "log.md"
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        with open(log_md, "a", encoding="utf-8") as f:
            f.write("\n" + log_entry + "\n")

    # Update compile state
    rel_path = log_path.name
    state.setdefault("ingested", {})[rel_path] = {
        "hash": file_hash(log_path),
        "compiled_at": now_iso(),
    }
    state["last_compile"] = now_iso()
    save_state(state)

    print(f"  Done. {len(articles)} article(s) written.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile daily logs into knowledge articles")
    parser.add_argument("--all", action="store_true", help="Force recompile all logs")
    parser.add_argument("--file", type=str, help="Compile a specific daily log file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    args = parser.parse_args()

    state = load_state()

    if args.file:
        target = Path(args.file)
        if not target.is_absolute():
            target = DAILY_DIR / target.name
        if not target.exists():
            target = ROOT_DIR / args.file
        if not target.exists():
            print(f"Error: {args.file} not found")
            return 1
        to_compile = [target]
    else:
        all_logs = list_raw_files()
        if args.all:
            to_compile = all_logs
        else:
            to_compile = []
            for log_path in all_logs:
                rel = log_path.name
                prev = state.get("ingested", {}).get(rel, {})
                if not prev or prev.get("hash") != file_hash(log_path):
                    to_compile.append(log_path)

    if not to_compile:
        print("Nothing to compile — all daily logs are up to date.")
        return 0

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Files to compile ({len(to_compile)}):")
    for f in to_compile:
        print(f"  - {f.name}")

    if args.dry_run:
        return 0

    for i, log_path in enumerate(to_compile, 1):
        print(f"\n[{i}/{len(to_compile)}] Compiling {log_path.name}…")
        compile_daily_log(log_path, state)

    articles = list_wiki_articles()
    print(f"\nCompilation complete. Knowledge base: {len(articles)} articles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
