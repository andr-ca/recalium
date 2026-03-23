"""Ingest parsers: auto-detect format and normalize to canonical representation.

Supported formats (D-18):
- paste_text: plain text (not JSON, not Markdown-with-headers)
- paste_markdown: Markdown text (# headers detected)
- chatgpt_json: ChatGPT export format {"conversations": [...]}
- claude_json: Claude export format [{"uuid": ..., "chat_messages": [...]}]
- generic_json: any other JSON (list or dict)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass
class ParsedIngest:
    """Result of parsing a raw ingest payload."""
    source_type: str
    raw_content: str
    content_hash: str
    conversation_count: int
    source_name: str | None
    metadata: dict | None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_markdown(text: str) -> bool:
    """Heuristic: text is Markdown if it has ATX headers or fenced code blocks."""
    lines = text.splitlines()
    for line in lines[:50]:
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("```"):
            return True
    return False


def _count_chatgpt_conversations(data: dict) -> int:
    conversations = data.get("conversations", [])
    if isinstance(conversations, list):
        return len(conversations)
    return 1


def _count_claude_conversations(data: list) -> int:
    return len(data) if isinstance(data, list) else 1


def detect_and_parse(
    content: str,
    filename: str | None = None,
    source_name: str | None = None,
) -> ParsedIngest:
    """Auto-detect format and parse content into ParsedIngest."""
    content = content.strip()
    raw_content = content
    content_hash = _sha256(content)

    parsed_json = None
    try:
        parsed_json = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        pass

    if parsed_json is not None:
        # Guard: empty JSON array has nothing to ingest
        if isinstance(parsed_json, list) and len(parsed_json) == 0:
            raise ValueError("JSON array is empty — nothing to ingest")

        if isinstance(parsed_json, dict) and "conversations" in parsed_json:
            count = _count_chatgpt_conversations(parsed_json)
            return ParsedIngest(
                source_type="chatgpt_json",
                raw_content=raw_content,
                content_hash=content_hash,
                conversation_count=count,
                source_name=source_name or (filename if filename else "ChatGPT Export"),
                metadata={"conversation_count": count},
            )

        if (
            isinstance(parsed_json, list)
            and len(parsed_json) > 0
            and isinstance(parsed_json[0], dict)
            and "uuid" in parsed_json[0]
            and "chat_messages" in parsed_json[0]
        ):
            count = _count_claude_conversations(parsed_json)
            return ParsedIngest(
                source_type="claude_json",
                raw_content=raw_content,
                content_hash=content_hash,
                conversation_count=count,
                source_name=source_name or (filename if filename else "Claude Export"),
                metadata={"conversation_count": count},
            )

        count = len(parsed_json) if isinstance(parsed_json, list) else 1
        return ParsedIngest(
            source_type="generic_json",
            raw_content=raw_content,
            content_hash=content_hash,
            conversation_count=count,
            source_name=source_name or (filename if filename else "JSON Import"),
            metadata={"json_type": type(parsed_json).__name__},
        )

    if _is_markdown(content):
        return ParsedIngest(
            source_type="paste_markdown",
            raw_content=raw_content,
            content_hash=content_hash,
            conversation_count=1,
            source_name=source_name or "Markdown Paste",
            metadata=None,
        )

    return ParsedIngest(
        source_type="paste_text",
        raw_content=raw_content,
        content_hash=content_hash,
        conversation_count=1,
        source_name=source_name or "Text Paste",
        metadata=None,
    )
