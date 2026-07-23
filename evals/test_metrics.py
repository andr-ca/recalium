"""Unit tests for the eval metric engine (GPT5.6 #12).

Run: python -m pytest evals/test_metrics.py -q  (from the repo root)
"""
from evals.metrics import (
    span_fidelity,
    extraction_recall_and_precision,
    ndcg_at_k,
)


def test_span_fidelity_missing_span_is_failure():
    facts = [
        {"source_span": "hello world", "raw_source": "say hello world now"},
        {"source_span": None, "raw_source": "no span here"},
    ]
    assert span_fidelity(facts) == 0.5


def test_span_fidelity_hallucinated_span_is_failure():
    facts = [{"source_span": "not present", "raw_source": "totally different text"}]
    assert span_fidelity(facts) == 0.0


def test_span_fidelity_all_verbatim():
    facts = [{"source_span": "abc", "raw_source": "xabcx"}]
    assert span_fidelity(facts) == 1.0


def test_duplicate_predictions_are_false_positives():
    golden = [{"text": "Python async functions use async def"}]
    extracted = [
        {"text": "Python async functions use async def"},
        {"text": "Python async functions use async def"},
        {"text": "Python async functions use async def"},
    ]
    recall, precision = extraction_recall_and_precision(extracted, golden)
    assert recall == 1.0
    assert abs(precision - (1 / 3)) < 1e-9


def test_one_to_one_matching_two_golden_two_extracted():
    golden = [{"text": "cats are mammals"}, {"text": "dogs are loyal animals"}]
    extracted = [{"text": "cats are mammals"}, {"text": "dogs are loyal animals"}]
    recall, precision = extraction_recall_and_precision(extracted, golden)
    assert recall == 1.0
    assert precision == 1.0


def test_empty_extracted_is_zero():
    assert extraction_recall_and_precision([], [{"text": "a fact here"}]) == (0.0, 0.0)


def test_ndcg_full_qrels_penalizes_omitted_relevant():
    returned = [1.0]  # one relevant doc returned at rank 1
    assert ndcg_at_k(returned, k=10) == 1.0  # legacy (no qrels) -> perfect
    ndcg = ndcg_at_k(returned, k=10, total_relevant=3)  # but 3 relevant exist
    assert 0.0 < ndcg < 1.0


# ── Eval overall-status determination (GPT5.6 #3) ──────────────────────────


def _check(name, passed, skipped=False):
    from evals.checks import CheckResult

    return CheckResult(
        name=name, passed=passed, metrics={}, details="", skipped=skipped,
        skip_reason=("skip" if skipped else ""),
    )


def test_status_all_executed_pass_is_pass():
    from evals.runner import determine_overall_status

    checks = [_check("a", True), _check("b", True)]
    passed, skipped = determine_overall_status(checks, strict=False)
    assert passed is True and skipped == []


def test_status_any_executed_failure_is_fail():
    from evals.runner import determine_overall_status

    checks = [_check("a", True), _check("b", False)]
    passed, _ = determine_overall_status(checks, strict=False)
    assert passed is False


def test_status_all_skipped_never_passes():
    from evals.runner import determine_overall_status

    checks = [_check("a", False, skipped=True), _check("b", False, skipped=True)]
    passed, skipped = determine_overall_status(checks, strict=False)
    assert passed is False
    assert len(skipped) == 2


def test_status_non_strict_is_fail_open_on_skips():
    """Default (dev) mode passes if executed checks pass, even with skips."""
    from evals.runner import determine_overall_status

    checks = [_check("a", True), _check("b", False, skipped=True)]
    passed, _ = determine_overall_status(checks, strict=False)
    assert passed is True


def test_status_strict_fails_on_any_skip():
    """Release mode refuses to pass when any check was skipped or errored."""
    from evals.runner import determine_overall_status

    checks = [_check("a", True), _check("b", False, skipped=True)]
    passed, skipped = determine_overall_status(checks, strict=True)
    assert passed is False
    assert len(skipped) == 1


def test_status_strict_fails_on_partial_skip_from_n_runs_aggregation():
    """A --n-runs aggregated check that skipped in only SOME runs reports
    skipped=False (real data exists) but a non-empty skip_reason (evals.aggregate's
    partial-skip signal). Strict mode must still fail on it, not just on fully
    skipped checks (Copilot review, PR #34)."""
    from evals.checks import CheckResult
    from evals.runner import determine_overall_status

    partially_skipped = CheckResult(
        name="extraction", passed=True, metrics={"recall": 0.7}, details="",
        skipped=False, skip_reason="1/3 runs skipped/errored this check",
    )
    checks = [_check("a", True), partially_skipped]

    passed, flagged = determine_overall_status(checks, strict=True)
    assert passed is False
    assert partially_skipped in flagged

    # Non-strict mode still fail-opens on it (real data + it passed on its own terms).
    passed_non_strict, _ = determine_overall_status(checks, strict=False)
    assert passed_non_strict is True


# ── Diverse scale corpus generator (GPT5.6 #20) ────────────────────────────


def test_generate_corpus_size_and_shape():
    from evals.datasets.generate_corpus import generate_corpus

    corpus = generate_corpus(120, seed=1)
    assert corpus["size"] == 120
    assert len(corpus["conversations"]) == 120
    for conv in corpus["conversations"]:
        assert conv["query"] == conv["token"]
        assert conv["token"] in conv["text"]  # the unique token is retrievable


def test_generate_corpus_is_deterministic():
    from evals.datasets.generate_corpus import generate_corpus

    a = generate_corpus(50, seed=7)
    b = generate_corpus(50, seed=7)
    assert a == b


def test_generate_corpus_tokens_are_unique():
    from evals.datasets.generate_corpus import generate_corpus

    convs = generate_corpus(200, seed=2)["conversations"]
    tokens = [c["token"] for c in convs]
    assert len(set(tokens)) == len(tokens)  # every conversation is separable


def test_generate_corpus_is_topically_diverse():
    from evals.datasets.generate_corpus import generate_corpus

    convs = generate_corpus(60, seed=3)["conversations"]
    # A tiny tuned fixture is the problem being fixed — require real breadth.
    assert len({c["topic"] for c in convs}) >= 10


def test_generate_corpus_rejects_negative_size():
    import pytest

    from evals.datasets.generate_corpus import generate_corpus

    with pytest.raises(ValueError):
        generate_corpus(-1)


def test_scale_check_is_importable():
    """Structural guard: the scale check and its runner wiring import cleanly."""
    from evals.checks.eval_scale import run_check  # noqa: F401
    from evals.runner import run_scale_check  # noqa: F401
