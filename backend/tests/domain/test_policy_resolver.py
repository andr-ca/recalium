"""Effective-policy resolver tests — GPT5.6 #6.

The resolver combines the content sensitivity gate with the caller-declared
processing intent, defaulting to stricter: a ``local_only`` mode or a sensitive
hint forbids external processing even when the gate allowed the content.
"""
from __future__ import annotations

from app.domain.policy.resolver import (
    ALLOWED_PROCESSING_MODES,
    ALLOWED_SENSITIVITY_HINTS,
    is_valid_processing_mode,
    is_valid_sensitivity_hint,
    normalize_processing_mode,
    normalize_sensitivity_hint,
    resolve_effective_policy,
)


def test_gate_allows_and_no_intent_allows_external():
    p = resolve_effective_policy(
        gate_allows=True,
        data_class="general",
        processing_mode=None,
        sensitivity_hint=None,
    )
    assert p.allow_external is True
    assert p.processing_mode == "deferred"
    assert p.sensitivity_hint is None


def test_local_only_mode_forbids_external_even_if_gate_allows():
    p = resolve_effective_policy(
        gate_allows=True,
        data_class="general",
        processing_mode="local_only",
        sensitivity_hint=None,
    )
    assert p.allow_external is False
    assert "processing_mode=local_only" in p.reason


def test_sensitive_hint_forbids_external_even_if_gate_allows():
    p = resolve_effective_policy(
        gate_allows=True,
        data_class="general",
        processing_mode="deferred",
        sensitivity_hint="sensitive",
    )
    assert p.allow_external is False
    assert "sensitivity_hint=sensitive" in p.reason


def test_gate_block_forbids_external_regardless_of_intent():
    p = resolve_effective_policy(
        gate_allows=False,
        data_class="personal_profile",
        processing_mode="immediate",
        sensitivity_hint="general",
    )
    assert p.allow_external is False
    assert "gate_blocked" in p.reason


def test_deferred_default_follows_gate():
    allowed = resolve_effective_policy(
        gate_allows=True,
        data_class="general",
        processing_mode="deferred",
        sensitivity_hint="general",
    )
    assert allowed.allow_external is True


def test_validation_accepts_known_and_empty():
    assert is_valid_processing_mode(None)
    assert is_valid_processing_mode("deferred")
    assert is_valid_processing_mode("LOCAL_ONLY")  # case-insensitive
    assert not is_valid_processing_mode("turbo")
    assert is_valid_sensitivity_hint(None)
    assert is_valid_sensitivity_hint("sensitive")
    assert not is_valid_sensitivity_hint("ultra")


def test_normalizers():
    assert normalize_processing_mode("  Deferred ") == "deferred"
    assert normalize_processing_mode("") == "deferred"
    assert normalize_processing_mode(None) == "deferred"
    assert normalize_sensitivity_hint("  SENSITIVE ") == "sensitive"
    assert normalize_sensitivity_hint("") is None


def test_allowed_sets_are_documented():
    assert "local_only" in ALLOWED_PROCESSING_MODES
    assert "sensitive" in ALLOWED_SENSITIVITY_HINTS
