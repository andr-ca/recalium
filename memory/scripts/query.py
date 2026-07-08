"""
Query the knowledge base using index-guided retrieval (no RAG).

The LLM reads the index, selects relevant articles, and synthesises an answer.
No vector database, no embeddings — just structured markdown and an index.

Usage:
    uv run python scripts/query.py "How should I handle auth redirects?"
    uv run python scripts/query.py "What patterns do I use for API design?" --file-back
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from config import KNOWLEDGE_DIR, MODEL_QUERY, QA_DIR, now_iso
from utils import list_wiki_articles, load_state, read_all_wiki_content, save_state, slugify

ROOT_DIR = Path(__file__).resolve().parent.parent


def run_query(question: str, file_back: bool = False) -> str:
    """Query the knowledge base and optionally file the answer back."""
    from copilot_client import chat

    wiki_content = read_all_wiki_content()
    timestamp = now_iso()

    file_back_instructions = ""
    if file_back:
        slug = slugify(question)[:60]
        file_back_instructions = f"""

## File Back Instructions

After answering, append a JSON block at the very end of your response (after a separator line `<!-- JSON -->`):

```json
{{
  "file_back": true,
  "qa_path": "knowledge/qa/{slug}.md",
  "qa_content": "<full Q&A article content including frontmatter>",
  "index_row": "| [[qa/{slug}]] | <one-line summary> | {timestamp[:10]} | {timestamp[:10]} |",
  "log_entry": "## [{timestamp}] query (filed) | {question[:60]}\\n- Question: {question}\\n- Filed to: [[qa/{slug}]]"
}}
```
"""

    prompt = f"""You are a knowledge base query engine. Answer the user's question by consulting
the knowledge base below.

## How to Answer

1. Read the INDEX section first — it lists every article with a one-line summary.
2. Identify 3-10 articles that are relevant to the question.
3. Read those articles carefully (they are included below).
4. Synthesise a clear, thorough answer.
5. Cite your sources using [[wikilinks]] (e.g. [[concepts/supabase-auth]]).
6. If the knowledge base does not contain relevant information, say so honestly.

## Knowledge Base

{wiki_content}

## Question

{question}
{file_back_instructions}"""

    raw = chat(MODEL_QUERY, prompt, max_tokens=2048)

    if file_back and "<!-- JSON -->" in raw:
        answer_part, json_part = raw.rsplit("<!-- JSON -->", 1)
        answer = answer_part.strip()
        json_part = json_part.strip()

        # Strip fences
        json_part = re.sub(r"^```[a-z]*\n?", "", json_part)
        json_part = re.sub(r"\n?```$", "", json_part.rstrip())

        try:
            data = json.loads(json_part)
            _file_back_result(data)
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            print(f"Warning: could not file answer back ({exc})", file=sys.stderr)
    else:
        answer = raw

    # Update state
    state = load_state()
    state["query_count"] = state.get("query_count", 0) + 1
    save_state(state)

    return answer


def _file_back_result(data: dict) -> None:
    """Write Q&A article and update index / log from the model's JSON payload."""
    qa_path = ROOT_DIR / data["qa_path"]
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(data["qa_content"], encoding="utf-8")
    print(f"  Filed to: {data['qa_path']}", flush=True)

    index_path = KNOWLEDGE_DIR / "index.md"
    if index_path.exists():
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(data["index_row"] + "\n")

    log_md = KNOWLEDGE_DIR / "log.md"
    with open(log_md, "a", encoding="utf-8") as f:
        f.write("\n" + data["log_entry"] + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the personal knowledge base")
    parser.add_argument("question", help="The question to ask")
    parser.add_argument(
        "--file-back",
        action="store_true",
        help="File the answer back into the knowledge base as a Q&A article",
    )
    args = parser.parse_args()

    print(f"Question: {args.question}")
    print(f"File back: {'yes' if args.file_back else 'no'}")
    print("-" * 60)

    answer = run_query(args.question, file_back=args.file_back)
    print(answer)

    if args.file_back:
        print("\n" + "-" * 60)
        qa_count = len(list(QA_DIR.glob("*.md"))) if QA_DIR.exists() else 0
        print(f"Answer filed to knowledge/qa/ ({qa_count} Q&A articles total)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
