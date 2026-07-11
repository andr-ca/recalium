"""Effective-policy resolver — enforce processing intent before external calls.

The sensitivity gate (``policy/gate.py``) classifies *content*. This resolver
combines that classification with the caller's declared **processing intent**
(``processing_mode`` / ``sensitivity_hint``, e.g. supplied by the MCP
``ingest_memory`` tool) into a single ``EffectivePolicy`` that the worker
consults before any external/BYOK provider call.

Security contract (GPT5.6 #6):
  * The resolver defaults to **stricter**: external processing is allowed only
    when the gate allows it *and* neither the mode nor the hint forbids it.
  * A ``local_only`` processing mode or a sensitive hint forces local-only
    processing even when the gate would have allowed the content.
  * The resolved decision (mode, hint, data class, provider, reason) is meant to
    be recorded in the audit trail by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass

# Accepted, validated values (used both here and at the MCP boundary).
ALLOWED_PROCESSING_MODES: frozenset[str] = frozenset({"deferred", "immediate", "local_only"})
# Accepted sensitivity hints — both non-sensitive labels and sensitive labels.
# Only the sensitive subset (``_SENSITIVE_HINTS``) forbids external processing.
ALLOWED_SENSITIVITY_HINTS: frozenset[str] = frozenset(
    {
        "general",
        "normal",
        "public",
        "low",
        "sensitive",
        "personal",
        "private",
        "confidential",
    }
)

# Values (incl. common synonyms) that force local-only processing.
_LOCAL_ONLY_MODES: frozenset[str] = frozenset(
    {"local_only", "local", "on_device", "no_external"}
)
_SENSITIVE_HINTS: frozenset[str] = frozenset(
    {"sensitive", "personal", "private", "confidential", "secret"}
)

_DEFAULT_PROCESSING_MODE = "deferred"


@dataclass(frozen=True)
class EffectivePolicy:
    """The resolved decision governing external processing of one item."""

    allow_external: bool
    processing_mode: str
    sensitivity_hint: str | None
    data_class: str
    reason: str


def normalize_processing_mode(value: str | None) -> str:
    """Lower/strip a processing mode; empty/None → the product default."""
    v = (value or "").strip().lower()
    return v or _DEFAULT_PROCESSING_MODE


def normalize_sensitivity_hint(value: str | None) -> str | None:
    """Lower/strip a sensitivity hint; empty/None → ``None`` (unknown)."""
    v = (value or "").strip().lower()
    return v or None


def is_valid_processing_mode(value: str | None) -> bool:
    """True if ``value`` is empty/None or an accepted processing mode."""
    if value is None or not value.strip():
        return True
    return value.strip().lower() in ALLOWED_PROCESSING_MODES


def is_valid_sensitivity_hint(value: str | None) -> bool:
    """True if ``value`` is empty/None or an accepted sensitivity hint."""
    if value is None or not value.strip():
        return True
    return value.strip().lower() in ALLOWED_SENSITIVITY_HINTS


def resolve_effective_policy(
    *,
    gate_allows: bool,
    data_class: str,
    processing_mode: str | None,
    sensitivity_hint: str | None,
) -> EffectivePolicy:
    """Resolve whether external processing is permitted for one item.

    Args:
        gate_allows: ``SensitivityDecision.is_allowed`` (content-based gate).
        data_class: the gate category (personal_profile/relationship/general/…).
        processing_mode: caller-declared mode (e.g. from MCP ingest metadata).
        sensitivity_hint: caller-declared hint.

    Returns:
        An ``EffectivePolicy`` whose ``allow_external`` is the AND of every
        signal — the strictest wins.
    """
    mode = normalize_processing_mode(processing_mode)
    hint = normalize_sensitivity_hint(sensitivity_hint)

    reasons: list[str] = [f"gate={data_class}"]
    allow = gate_allows
    if not gate_allows:
        reasons.append("gate_blocked")

    if mode in _LOCAL_ONLY_MODES:
        allow = False
        reasons.append(f"processing_mode={mode}")

    if hint in _SENSITIVE_HINTS:
        allow = False
        reasons.append(f"sensitivity_hint={hint}")

    return EffectivePolicy(
        allow_external=allow,
        processing_mode=mode,
        sensitivity_hint=hint,
        data_class=data_class,
        reason="; ".join(reasons),
    )
