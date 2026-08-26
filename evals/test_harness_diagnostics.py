"""Tests for eval harness diagnostics and preflight (M2 trustworthiness)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from evals.harness_diagnostics import classify_zero_extraction


def test_classify_gate_blocked_when_all_controls_blocked():
    category, detail = classify_zero_extraction(
        control_archive_ids=["a1"],
        gate_events={"a1": {"blocked": True}},
        archive_rows=[],
    )
    assert category == "gate_blocked"
    assert "blocked=True" in detail


def test_classify_provider_failure_when_gate_allowed_but_no_facts():
    category, detail = classify_zero_extraction(
        control_archive_ids=["a1"],
        gate_events={"a1": {"blocked": False}},
        archive_rows=[
            {
                "id": "a1",
                "status_badge": "Failed",
                "job_error": "HTTPStatusError: 404 Not Found for url 'http://localhost:11434/api/chat'",
            },
        ],
    )
    assert category == "provider_pipeline_failure"
    assert "404" in detail or "Pipeline" in detail


def test_classify_provider_failure_when_gate_allowed_no_job_row():
    category, _ = classify_zero_extraction(
        control_archive_ids=["a1"],
        gate_events={"a1": {"blocked": False}},
        archive_rows=[],
    )
    assert category == "provider_pipeline_failure"


@pytest.mark.asyncio
async def test_sensitivity_vacuous_pass_blocked_when_zero_control_facts():
    """Sensitivity must not pass audit path when corpus has zero control facts."""
    from evals.checks.eval_sensitivity import run_check

    golden = {
        "conversations": [
            {
                "id": "conv-sensitive",
                "raw_text": "personal health note",
                "facts": [{"text": "secret", "sensitivity_level": "personal"}],
            },
        ],
    }
    settings = {
        "base_url": "http://localhost:8000",
        "ingested_archive_ids": {"conv-001": ["control-archive-1"]},
        "extraction_worked": False,
    }

    client = AsyncMock()

    async def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        if "/api/settings/keys" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "openai": {"configured": True},
                "anthropic": {"configured": False},
                "ollama": {"configured": False},
            }
        elif "/api/archive" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "items": [{"id": "sensitive-1", "status_badge": "Done"}],
            }
        elif "/api/facts" in url:
            resp.status_code = 200
            resp.json.return_value = {"facts": []}
        elif "/api/audit/events" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "items": [
                    {
                        "raw_archive_id": "sensitive-1",
                        "operation_metadata": {"blocked": True},
                    },
                    {
                        "raw_archive_id": "control-archive-1",
                        "operation_metadata": {"blocked": False},
                    },
                ],
            }
        else:
            resp.status_code = 404
            resp.json.return_value = {}
        return resp

    client.get = mock_get
    client.post = AsyncMock(
        return_value=MagicMock(status_code=202, json=lambda: {"archive_ids": ["sensitive-1"]}),
    )

    result = await run_check(client, golden, settings)
    assert result.skipped
    assert "inconclusive" in result.skip_reason.lower() or "zero facts" in result.skip_reason.lower()
    assert not result.passed


@pytest.mark.asyncio
async def test_preflight_fails_when_ollama_model_missing(monkeypatch):
    from evals.preflight import preflight_extraction_provider

    monkeypatch.setattr(
        "evals.preflight._expected_ollama_model",
        lambda: "missing-model",
    )

    client = AsyncMock()
    keys_resp = MagicMock()
    keys_resp.status_code = 200
    keys_resp.json.return_value = {
        "openai": {"configured": False},
        "anthropic": {"configured": False},
        "ollama": {
            "configured": True,
            "base_url": "http://172.23.0.1:11434",
            "validation_status": "valid",
        },
    }

    tags_resp = MagicMock()
    tags_resp.status_code = 200
    tags_resp.json.return_value = {"models": [{"name": "qwen3.8:27b"}]}

    async def mock_get(url, *args, **kwargs):
        if "settings/keys" in url:
            return keys_resp
        if "/api/tags" in url:
            return tags_resp
        raise AssertionError(f"unexpected url {url}")

    client.get = mock_get

    ok, msg = await preflight_extraction_provider(client, "http://localhost:8000")
    assert not ok
    assert "not installed" in msg.lower() or "llama3.2" in msg
