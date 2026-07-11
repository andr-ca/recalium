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
