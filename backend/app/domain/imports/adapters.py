"""Import adapters — normalize ChatGPT and Claude conversation exports.

The upstream ingest path stored an entire multi-conversation export as a single
``raw_archive`` blob, so a 200-conversation export produced one summary and one
extraction pass over hundreds of conversations. These adapters decompose an
export into individual conversations so each one flows through the pipeline with
its own provenance (source system, conversation id, title, timestamps).

Supported inputs
----------------
* **ChatGPT** ``conversations.json`` — a top-level list (or ``{"conversations": [...]}``)
  of conversation objects. Real exports carry a ``mapping`` node graph; a simpler
  ``messages`` list is accepted as a fallback.
* **Claude** ``conversations.json`` — a top-level list (or ``{"conversations": [...]}``)
  of objects with ``chat_messages``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_CHATGPT_ROLE_MAP = {
    "user": "user",
    "assistant": "assistant",
    "system": "system",
    "tool": "tool",
}
_CLAUDE_ROLE_MAP = {"human": "user", "assistant": "assistant"}
_ROLE_LABEL = {
    "user": "User",
    "assistant": "Assistant",
    "system": "System",
    "tool": "Tool",
}


@dataclass
class NormalizedMessage:
    """A single turn in a normalized conversation."""

    role: str
    text: str
    created_at: str | None = None  # ISO-8601 when known


@dataclass
class NormalizedConversation:
    """A provider-agnostic conversation extracted from an export."""

    source_system: str  # "chatgpt" | "claude"
    title: str
    messages: list[NormalizedMessage] = field(default_factory=list)
    source_conversation_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @property
    def message_count(self) -> int:
        return len(self.messages)


def _epoch_to_iso(value: Any) -> str | None:
    """Convert a Unix epoch (int/float/str) to an ISO-8601 UTC string."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _coerce_iso(value: Any) -> str | None:
    """Best-effort timestamp coercion. Epoch numbers → ISO; strings kept as-is."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return _epoch_to_iso(value)
    if isinstance(value, str):
        return value
    return None


def _join_text_parts(parts: Any) -> str:
    """Flatten ChatGPT ``content.parts`` (strings and/or multimodal dicts)."""
    if parts is None:
        return ""
    if isinstance(parts, str):
        return parts
    if isinstance(parts, list):
        out: list[str] = []
        for part in parts:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                out.append(part["text"])
        return "\n".join(p for p in out if p)
    return ""


def _join_claude_content(content: Any) -> str:
    """Flatten a Claude ``content`` array of ``{"type": "text", "text": ...}`` blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[str] = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                out.append(block["text"])
            elif isinstance(block, str):
                out.append(block)
        return "\n".join(out)
    return ""


def detect_export_format(data: Any) -> str | None:
    """Return ``"chatgpt"``, ``"claude"``, or ``None`` for an unknown payload."""
    conversations: Any = None
    if isinstance(data, list):
        conversations = data
    elif isinstance(data, dict):
        conversations = data.get("conversations")

    if isinstance(conversations, list) and conversations:
        first = conversations[0]
        if isinstance(first, dict):
            if "chat_messages" in first:
                return "claude"
            if "mapping" in first or "create_time" in first or "messages" in first:
                return "chatgpt"
    return None


def _chatgpt_messages(conv: dict) -> list[NormalizedMessage]:
    """Extract ordered messages from a ChatGPT conversation (mapping graph or list)."""
    mapping = conv.get("mapping")
    collected: list[tuple[float, str, str]] = []
    if isinstance(mapping, dict):
        for node in mapping.values():
            msg = node.get("message") if isinstance(node, dict) else None
            if not isinstance(msg, dict):
                continue
            author = msg.get("author") if isinstance(msg.get("author"), dict) else {}
            role = author.get("role")
            content = msg.get("content") if isinstance(msg.get("content"), dict) else {}
            text = _join_text_parts(content.get("parts"))
            if not text.strip():
                continue
            try:
                order = float(msg.get("create_time") or 0.0)
            except (TypeError, ValueError):
                order = 0.0
            collected.append((order, role or "unknown", text))
        collected.sort(key=lambda item: item[0])
        return [
            NormalizedMessage(
                role=_CHATGPT_ROLE_MAP.get(role, role or "unknown"),
                text=text,
                created_at=_epoch_to_iso(order) if order else None,
            )
            for order, role, text in collected
        ]

    messages = conv.get("messages")
    out: list[NormalizedMessage] = []
    if isinstance(messages, list):
        for m in messages:
            if not isinstance(m, dict):
                continue
            role = m.get("role") or m.get("author") or "unknown"
            raw = m.get("content")
            text = raw if isinstance(raw, str) else _join_text_parts(
                raw.get("parts") if isinstance(raw, dict) else None
            )
            if text and text.strip():
                out.append(
                    NormalizedMessage(
                        role=_CHATGPT_ROLE_MAP.get(role, role or "unknown"),
                        text=text,
                        created_at=_coerce_iso(m.get("create_time")),
                    )
                )
    return out


def parse_chatgpt_export(data: Any) -> list[NormalizedConversation]:
    """Parse a ChatGPT export into normalized conversations (empty ones dropped)."""
    if isinstance(data, dict):
        conversations = data.get("conversations", [])
    elif isinstance(data, list):
        conversations = data
    else:
        conversations = []

    result: list[NormalizedConversation] = []
    for conv in conversations:
        if not isinstance(conv, dict):
            continue
        messages = _chatgpt_messages(conv)
        if not messages:
            continue
        conv_id = conv.get("conversation_id") or conv.get("id")
        title = str(conv.get("title") or "").strip() or "Untitled conversation"
        result.append(
            NormalizedConversation(
                source_system="chatgpt",
                title=title,
                messages=messages,
                source_conversation_id=str(conv_id) if conv_id else None,
                created_at=_epoch_to_iso(conv.get("create_time")),
                updated_at=_epoch_to_iso(conv.get("update_time")),
            )
        )
    return result


def parse_claude_export(data: Any) -> list[NormalizedConversation]:
    """Parse a Claude export into normalized conversations (empty ones dropped)."""
    if isinstance(data, dict):
        conversations = data.get("conversations", [])
    elif isinstance(data, list):
        conversations = data
    else:
        conversations = []

    result: list[NormalizedConversation] = []
    for conv in conversations:
        if not isinstance(conv, dict):
            continue
        messages: list[NormalizedMessage] = []
        for m in conv.get("chat_messages") or []:
            if not isinstance(m, dict):
                continue
            role = m.get("sender") or m.get("role") or "unknown"
            role = _CLAUDE_ROLE_MAP.get(role, role)
            text = m.get("text") or _join_claude_content(m.get("content"))
            if text and text.strip():
                messages.append(
                    NormalizedMessage(
                        role=role,
                        text=text,
                        created_at=_coerce_iso(m.get("created_at")),
                    )
                )
        if not messages:
            continue
        conv_id = conv.get("uuid")
        title = str(conv.get("name") or conv.get("title") or "").strip() or "Untitled conversation"
        result.append(
            NormalizedConversation(
                source_system="claude",
                title=title,
                messages=messages,
                source_conversation_id=str(conv_id) if conv_id else None,
                created_at=_coerce_iso(conv.get("created_at")),
                updated_at=_coerce_iso(conv.get("updated_at")),
            )
        )
    return result


def parse_export(data: Any) -> tuple[str | None, list[NormalizedConversation]]:
    """Detect the export format and return ``(format, conversations)``."""
    fmt = detect_export_format(data)
    if fmt == "chatgpt":
        return fmt, parse_chatgpt_export(data)
    if fmt == "claude":
        return fmt, parse_claude_export(data)
    return None, []


def render_conversation_text(conv: NormalizedConversation) -> str:
    """Render a conversation as a readable Markdown transcript for the pipeline."""
    lines = [f"# {conv.title}"]
    if conv.created_at:
        lines.append(f"_Started: {conv.created_at}_")
    lines.append("")
    for msg in conv.messages:
        label = _ROLE_LABEL.get(msg.role, msg.role.capitalize() if msg.role else "Unknown")
        lines.append(f"## {label}")
        lines.append(msg.text.strip())
        lines.append("")
    return "\n".join(lines).strip()
