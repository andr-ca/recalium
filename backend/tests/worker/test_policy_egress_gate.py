"""External-egress policy gating in the pipeline (GPT5.6 #6).

Two guarantees:
  * Link-detection Pass B (which sends fact text to an external LLM) must not run
    when the resolved policy forbids external calls.
  * The policy-decision audit records the *provider* (openai|anthropic|ollama),
    not the model label.
"""
from __future__ import annotations

import hashlib
import types
import uuid

import pytest

pytest.importorskip("app.worker.dispatcher")

from app.worker.dispatcher import (  # noqa: E402
    _active_provider_label,
    _provider_name,
    _run_link_detection_job,
)


async def _seed_two_linkable_archives(session) -> uuid.UUID:
    """Two archives, each with an active fact + embedding, so Pass A yields a
    cross-archive semantic candidate for the first archive. Returns its id.
    """
    from app.domain.archive.models import RawArchiveItem
    from app.domain.derived_memory.models import Embedding, Fact

    ids = []
    for i in range(2):
        content = f"linkable content {i} {uuid.uuid4()}"
        archive = RawArchiveItem(
            id=uuid.uuid4(),
            source_type="test",
            raw_content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        )
        session.add(archive)
        await session.flush()
        session.add(
            Fact(
                id=uuid.uuid4(),
                raw_archive_id=archive.id,
                fact_text=f"Fact number {i} about Python performance.",
                source_span="Python performance",
                confidence_tier="high",
                derivation_method="llm_extraction",
                derivation_model="test-model",
            )
        )
        session.add(
            Embedding(
                id=uuid.uuid4(),
                raw_archive_id=archive.id,
                embedding=[0.1 * (i + 1)] * 384,
                embedding_model="all-MiniLM-L6-v2",
            )
        )
        ids.append(archive.id)
    await session.commit()
    return ids[0]


async def test_pass_b_skipped_when_external_disallowed(db_session, monkeypatch):
    """local_only / sensitive policy must block the external LLM link classifier."""
    archive_id = await _seed_two_linkable_archives(db_session)

    calls = {"n": 0}

    async def spy_classify(a: str, b: str):
        calls["n"] += 1
        return "unrelated"

    monkeypatch.setattr("app.worker.dispatcher._has_llm_provider", lambda: True)
    monkeypatch.setattr("app.worker.dispatcher._classify_link_pair", spy_classify)

    await _run_link_detection_job(db_session, archive_id, allow_external=False)
    assert calls["n"] == 0, "Pass B egressed to the LLM despite allow_external=False"


async def test_pass_b_runs_when_external_allowed(db_session, monkeypatch):
    """With external allowed and a provider present, Pass B is reached."""
    archive_id = await _seed_two_linkable_archives(db_session)

    calls = {"n": 0}

    async def spy_classify(a: str, b: str):
        calls["n"] += 1
        return "unrelated"

    monkeypatch.setattr("app.worker.dispatcher._has_llm_provider", lambda: True)
    monkeypatch.setattr("app.worker.dispatcher._classify_link_pair", spy_classify)

    await _run_link_detection_job(db_session, archive_id, allow_external=True)
    assert calls["n"] >= 1, "Pass B should classify at least one pair when allowed"


def test_active_provider_label_reports_provider_not_model(monkeypatch):
    """The policy audit's provider field is a provider name, not a model label."""
    fake = types.SimpleNamespace(
        extract_provider="openai",
        summarize_provider="openai",
        extract_model="gpt-4o-mini",
        openai_api_key="sk-test",
        anthropic_api_key=None,
        ollama_base_url=None,
        ollama_model="llama3.2",
    )
    monkeypatch.setattr("app.worker.dispatcher.get_settings", lambda: fake)

    assert _active_provider_label() == "openai"
    # _provider_name (used for fact.derivation_model) resolves to the MODEL label.
    assert _provider_name() == "gpt-4o-mini"


def test_active_provider_label_none_when_no_provider(monkeypatch):
    fake = types.SimpleNamespace(
        extract_provider="auto",
        summarize_provider="auto",
        extract_model="auto",
        openai_api_key=None,
        anthropic_api_key=None,
        ollama_base_url=None,
        ollama_model="llama3.2",
    )
    monkeypatch.setattr("app.worker.dispatcher.get_settings", lambda: fake)
    assert _active_provider_label() is None
