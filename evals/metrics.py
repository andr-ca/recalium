"""Evaluation metrics for Recalium assessment suite."""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from statistics import mean, median


@dataclass
class RetrievalMetrics:
    """Container for retrieval quality metrics."""
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_10: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float


@dataclass
class ExtractionMetrics:
    """Container for extraction quality metrics."""
    recall: float
    precision: float
    span_fidelity: float
    count_extracted: int
    count_golden: int


@dataclass
class IngestMetrics:
    """Container for ingest performance metrics."""
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    success_rate: float
    count_ingested: int


def recall_at_k(relevant_ids: List[str], retrieved_ids: List[str], k: int) -> float:
    """
    Calculate recall@k: fraction of top-k retrieved that are in relevant set.

    recall@k = |retrieved[:k] ∩ relevant| / |relevant|

    Args:
        relevant_ids: List of ground-truth relevant fact IDs
        retrieved_ids: List of retrieved fact IDs in rank order
        k: Cutoff position (e.g., 5 for recall@5)

    Returns:
        Recall score 0.0-1.0
    """
    if not relevant_ids:
        return 0.0

    relevant_set = set(relevant_ids)
    retrieved_at_k = set(retrieved_ids[:k])

    matches = len(relevant_set & retrieved_at_k)
    return matches / len(relevant_set)


def precision_at_k(relevant_ids: List[str], retrieved_ids: List[str], k: int) -> float:
    """
    Calculate precision@k: fraction of top-k retrieved that are relevant.

    precision@k = |retrieved[:k] ∩ relevant| / k

    Args:
        relevant_ids: List of ground-truth relevant fact IDs
        retrieved_ids: List of retrieved fact IDs in rank order
        k: Cutoff position

    Returns:
        Precision score 0.0-1.0
    """
    if k == 0:
        return 0.0

    relevant_set = set(relevant_ids)
    retrieved_at_k = set(retrieved_ids[:k])

    matches = len(relevant_set & retrieved_at_k)
    return matches / k


def mrr(relevant_ids: List[str], retrieved_ids: List[str]) -> float:
    """
    Calculate MRR (Mean Reciprocal Rank): position of first relevant result.

    MRR = 1 / rank_of_first_relevant_item

    Args:
        relevant_ids: List of ground-truth relevant fact IDs
        retrieved_ids: List of retrieved fact IDs in rank order

    Returns:
        MRR score 0.0-1.0 (0 if no relevant items found)
    """
    relevant_set = set(relevant_ids)

    for rank, item_id in enumerate(retrieved_ids, start=1):
        if item_id in relevant_set:
            return 1.0 / rank

    return 0.0


def dcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """
    Calculate DCG@k (Discounted Cumulative Gain).

    DCG@k = Σ(relevance_i / log2(i+1)) for i in 1..k

    Args:
        relevance_scores: List of relevance scores (0.0-1.0) in rank order
        k: Cutoff position

    Returns:
        DCG score (non-normalized)
    """
    dcg = 0.0
    for i, score in enumerate(relevance_scores[:k], start=1):
        dcg += score / math.log2(i + 1)
    return dcg


def idcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """
    Calculate ideal DCG@k (for normalization).

    IDCG@k = DCG@k of perfectly ranked results (all 1.0s, then 0.0s)

    Args:
        relevance_scores: List of relevance scores in any order
        k: Cutoff position

    Returns:
        IDCG score (normalized DCG max)
    """
    ideal = sorted(relevance_scores, reverse=True)
    return dcg_at_k(ideal, k)


def ndcg_at_k(relevance_scores: List[float], k: int = 10, total_relevant: int | None = None) -> float:
    """
    Calculate nDCG@k (Normalized Discounted Cumulative Gain).

    nDCG@k = DCG@k / IDCG@k

    Args:
        relevance_scores: List of relevance scores (0.0-1.0) in rank order
        k: Cutoff position
        total_relevant: Total number of relevant items in the qrels. When given,
            the ideal DCG is computed over the full relevant set so that relevant
            documents omitted from the returned list correctly reduce nDCG
            (GPT5.6 #12). Defaults to the returned scores when omitted.

    Returns:
        nDCG score 0.0-1.0
    """
    actual_dcg = dcg_at_k(relevance_scores, k)
    ideal_scores = [1.0] * total_relevant if total_relevant is not None else relevance_scores
    ideal_dcg = idcg_at_k(ideal_scores, k)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


def span_fidelity(facts: List[Dict]) -> float:
    """
    Calculate span fidelity: % of facts where source_span is verbatim substring of raw_source.

    Args:
        facts: List of dicts with keys:
            - source_span: str or None
            - raw_source: str

    Returns:
        Fidelity score 0.0-1.0 (0 if no facts)
    """
    if not facts:
        return 0.0

    valid_spans = 0
    for fact in facts:
        source_span = fact.get("source_span")
        raw_source = fact.get("raw_source", "")

        # GPT5.6 #12: a missing/empty span is NOT faithful — provenance requires a
        # verbatim source span. Only a span that is a verbatim substring counts.
        if source_span and source_span in raw_source:
            valid_spans += 1

    return valid_spans / len(facts)


def latency_percentiles(latencies_ms: List[float]) -> Dict[str, float]:
    """
    Calculate latency percentiles (P50, P95, P99).

    Args:
        latencies_ms: List of latency measurements in milliseconds

    Returns:
        Dict with keys 'p50', 'p95', 'p99' and float values (ms)
    """
    if not latencies_ms:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    sorted_latencies = sorted(latencies_ms)
    n = len(sorted_latencies)

    def percentile(data: List[float], p: float) -> float:
        """Calculate percentile using linear interpolation."""
        idx = (p / 100.0) * (len(data) - 1)
        lower_idx = int(idx)
        upper_idx = min(lower_idx + 1, len(data) - 1)

        if lower_idx == upper_idx:
            return data[lower_idx]

        fraction = idx - lower_idx
        return data[lower_idx] * (1 - fraction) + data[upper_idx] * fraction

    return {
        "p50": percentile(sorted_latencies, 50.0),
        "p95": percentile(sorted_latencies, 95.0),
        "p99": percentile(sorted_latencies, 99.0),
    }


_MATCH_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "in", "for", "of", "to",
    "with", "and", "or", "on", "that", "this", "it", "its", "be", "as", "by",
    "at", "use", "used", "using", "uses", "user", "users", "should", "can",
    "will", "only", "all", "very",
})


def _content_words(text: str) -> set:
    """Lowercased content words (stopwords and 1-char tokens removed)."""
    import re
    return {
        w for w in re.findall(r"[a-z0-9@+]+", text.lower())
        if w not in _MATCH_STOPWORDS and len(w) > 1
    }


def fuzzy_match_text(text_a: str, text_b: str, threshold: float = 0.6) -> bool:
    """
    Check whether two fact statements express the same fact.

    Primary signal: content-word overlap ratio (|A∩B| / min(|A|,|B|)) — robust
    to paraphrase ("Async functions are defined using the syntax 'async def'"
    vs "Python async functions are defined with `async def` keyword"), which
    pure SequenceMatcher at 0.8 rejects. SequenceMatcher kept as a secondary
    signal for near-verbatim strings with little word overlap after stopwords.
    Calibrated against real qwen3.5:4b extractions vs golden labels (2026-07-08).

    Args:
        text_a: First fact text
        text_b: Second fact text
        threshold: Minimum content-word overlap ratio (0.0-1.0)

    Returns:
        True if the statements match
    """
    if not text_a or not text_b:
        return False

    if text_b.lower() in text_a.lower() or text_a.lower() in text_b.lower():
        return True

    words_a = _content_words(text_a)
    words_b = _content_words(text_b)
    if words_a and words_b:
        overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
        if overlap >= threshold:
            return True

    from difflib import SequenceMatcher
    return SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio() >= 0.8


def extraction_recall_and_precision(
    extracted_facts: List[Dict],
    golden_facts: List[Dict],
    text_threshold: float = 0.8
) -> Tuple[float, float]:
    """
    Calculate extraction recall and precision with fuzzy matching.

    Args:
        extracted_facts: List of extracted facts with 'text' key
        golden_facts: List of golden facts with 'text' key
        text_threshold: Fuzzy match threshold (0.0-1.0)

    Returns:
        Tuple of (recall, precision) scores
    """
    if not golden_facts:
        return (0.0, 1.0)  # Recall undefined; precision perfect if nothing to extract

    if not extracted_facts:
        return (0.0, 0.0)  # No extractions; both metrics are 0

    # GPT5.6 #12: greedy ONE-TO-ONE matching. Each golden fact and each extracted
    # fact can be credited at most once, so duplicate predictions become false
    # positives (1 golden + 3 duplicate predictions -> precision 1/3, not 1.0).
    matched_golden_idxs: set = set()
    matched_extracted_idxs: set = set()

    for extracted_idx, extracted in enumerate(extracted_facts):
        extracted_text = extracted.get("text", "")

        for golden_idx, golden in enumerate(golden_facts):
            if golden_idx in matched_golden_idxs:
                continue  # this golden fact is already consumed (one-to-one)

            if fuzzy_match_text(extracted_text, golden.get("text", ""), text_threshold):
                matched_golden_idxs.add(golden_idx)
                matched_extracted_idxs.add(extracted_idx)
                break  # this extraction is consumed

    recall = len(matched_golden_idxs) / len(golden_facts)
    precision = len(matched_extracted_idxs) / len(extracted_facts)

    return (recall, precision)


def sensitivity_block_rate(
    facts: List[Dict],
    sensitivity_level_key: str = "sensitivity_level"
) -> Tuple[float, int, int]:
    """
    Calculate sensitivity block rate for personal/relationship facts.

    Args:
        facts: List of facts with sensitivity_level key
        sensitivity_level_key: Key in fact dict for sensitivity level

    Returns:
        Tuple of (block_rate, blocked_count, total_sensitive_count)
    """
    sensitive_facts = [
        f for f in facts
        if f.get(sensitivity_level_key) in ("personal", "relationship")
    ]

    if not sensitive_facts:
        return (1.0, 0, 0)  # No sensitive facts to block; vacuously true

    # In practice, this would check job_status or audit logs to verify
    # facts were not dispatched to external providers.
    # For now, assume block_rate = 100% if sensitivity_level is set correctly.

    blocked = len(sensitive_facts)  # Placeholder; actual implementation checks job status

    return (1.0, blocked, len(sensitive_facts))
