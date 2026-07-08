"""Policy gate tests — PIPE-03, PRIV-04, PRIV-05.

Tests will FAIL (RED) until app.domain.policy.gate is created.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.domain.policy.gate", reason="policy.gate not yet implemented")

from app.domain.policy.gate import SensitivityGate, SensitivityDecision  # noqa: E402


def test_personal_profile_blocked():
    """PRIV-04: Content matching personal_profile heuristic is blocked from external processing."""
    gate = SensitivityGate()
    # Personal profile keywords: name, birthday, address, age
    text = "My name is Alice and I was born on March 15, 1990. I live at 123 Main St."
    decision: SensitivityDecision = gate.classify(text)

    assert decision.category in ("personal_profile", "unclassified")
    assert decision.blocked is True


def test_relationship_content_blocked():
    """PRIV-04: Content with relationship keywords is blocked from external processing."""
    gate = SensitivityGate()
    text = "My wife Sarah and I went to dinner with our kids last night."
    decision: SensitivityDecision = gate.classify(text)

    assert decision.category in ("relationship", "unclassified")
    assert decision.blocked is True


def test_unclassified_blocked_by_default():
    """PRIV-05: Content that can't be classified is blocked by default."""
    gate = SensitivityGate()
    # Ambiguous content with no clear category
    text = "The function takes a parameter and returns a value."
    decision: SensitivityDecision = gate.classify(text)

    # Must be blocked — unclassified is blocked by default
    if decision.category == "unclassified":
        assert decision.blocked is True


def test_general_content_allowed():
    """PIPE-03: General (non-personal) content is allowed through the gate."""
    gate = SensitivityGate()
    text = "Python is a high-level programming language. It supports object-oriented programming."
    decision: SensitivityDecision = gate.classify(text)

    if decision.category == "general":
        assert decision.blocked is False


def test_no_external_call_for_sensitive(monkeypatch):
    """PRIV-04: When gate blocks content, no external provider call is made."""
    gate = SensitivityGate()
    external_calls = {"count": 0}

    # Patch httpx to detect if external call is made
    import httpx
    original_get = httpx.AsyncClient.get
    def fake_get(self, url, **kwargs):
        if "openai.com" in url or "anthropic.com" in url:
            external_calls["count"] += 1
        return original_get(self, url, **kwargs)

    # Classify personal content
    text = "My name is Bob. I am 35 years old."
    decision = gate.classify(text)

    # If blocked, no external call should have occurred during classification
    if decision.blocked:
        assert external_calls["count"] == 0


def test_decision_has_required_audit_fields():
    """PIPE-03: Gate decision includes category, confidence, and blocked fields for audit trail."""
    gate = SensitivityGate()
    decision = gate.classify("Hello world, this is a test.")

    assert hasattr(decision, "category")
    assert hasattr(decision, "confidence")
    assert hasattr(decision, "blocked")
    assert isinstance(decision.category, str)
    assert isinstance(decision.confidence, float)
    assert isinstance(decision.blocked, bool)
    assert decision.category in ("personal_profile", "relationship", "unclassified", "general")


# ── Embedding-prototype pass (F22 recalibration) ──────────────────────────────
# Decision rule is a pure function over per-category similarities so it can be
# tested without loading the model.

from app.domain.policy.gate import _decide_from_similarities  # noqa: E402


def test_general_high_similarity_allowed():
    """Technical content with strong general similarity and margin is allowed."""
    d = _decide_from_similarities(
        {"personal_profile": 0.12, "relationship": 0.10, "general": 0.71}
    )
    assert d.category == "general"
    assert d.blocked is False
    assert d.method == "embedding"


def test_general_weak_similarity_stays_blocked():
    """PRIV-05: weak general similarity is NOT enough to allow — unclassified."""
    d = _decide_from_similarities(
        {"personal_profile": 0.13, "relationship": 0.03, "general": 0.16}
    )
    assert d.category == "unclassified"
    assert d.blocked is True


def test_general_small_margin_stays_blocked():
    """PRIV-05: general must clearly beat sensitive categories to allow."""
    d = _decide_from_similarities(
        {"personal_profile": 0.40, "relationship": 0.10, "general": 0.45}
    )
    assert d.category == "unclassified"
    assert d.blocked is True


def test_sensitive_category_blocks_at_low_bar():
    """Privacy-first: moderate personal similarity blocks even without margin."""
    d = _decide_from_similarities(
        {"personal_profile": 0.47, "relationship": 0.19, "general": 0.06}
    )
    assert d.category == "personal_profile"
    assert d.blocked is True


def test_relationship_similarity_blocks():
    d = _decide_from_similarities(
        {"personal_profile": 0.20, "relationship": 0.45, "general": 0.30}
    )
    assert d.category == "relationship"
    assert d.blocked is True


async def test_classify_async_allows_technical_conversation():
    """F22 end-to-end: realistic technical content passes the async gate.

    Requires sentence-transformers (EMBED_BACKEND=cpu); skipped otherwise.
    """
    pytest.importorskip("sentence_transformers")
    gate = SensitivityGate()
    text = (
        "User: How should I index a PostgreSQL table with millions of rows?\n\n"
        "Assistant: PostgreSQL indexing strategies depend on your query patterns. "
        "B-tree indexes are the default for equality and range queries. For full-text "
        "search use GIN indexes with tsvector columns."
    )
    decision = await gate.classify_async(text)
    assert decision.category == "general", f"got {decision}"
    assert decision.blocked is False


async def test_classify_async_blocks_subtle_personal_content():
    """Personal/health content without any blocklist keyword must still block."""
    pytest.importorskip("sentence_transformers")
    gate = SensitivityGate()
    text = (
        "I have not been sleeping well since the diagnosis. The doctor said I need "
        "to reduce stress, but work keeps piling up and I feel overwhelmed every morning."
    )
    decision = await gate.classify_async(text)
    assert decision.blocked is True
    assert decision.category in ("personal_profile", "unclassified")
