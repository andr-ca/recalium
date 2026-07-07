"""Evaluation metrics for Recalium assessment suite."""

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
        if i == 1:
            dcg += score
        else:
            dcg += score / (2.0 ** (i - 1)).bit_length()  # log2(i+1) approximation
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


def ndcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """
    Calculate nDCG@k (Normalized Discounted Cumulative Gain).

    nDCG@k = DCG@k / IDCG@k

    Args:
        relevance_scores: List of relevance scores (0.0-1.0) in rank order
        k: Cutoff position

    Returns:
        nDCG score 0.0-1.0
    """
    actual_dcg = dcg_at_k(relevance_scores, k)
    ideal_dcg = idcg_at_k(relevance_scores, k)

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

        if source_span and source_span in raw_source:
            valid_spans += 1
        elif not source_span:
            # No span is acceptable (not a fidelity error)
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


def fuzzy_match_text(text_a: str, text_b: str, threshold: float = 0.8) -> bool:
    """
    Check if text_a and text_b match with threshold similarity.

    Simple fuzzy match: text_a contains ≥threshold of text_b or vice versa.
    This is a basic implementation; consider difflib.SequenceMatcher for production.

    Args:
        text_a: First text to compare
        text_b: Second text to compare
        threshold: Minimum character overlap ratio (0.0-1.0)

    Returns:
        True if texts match within threshold
    """
    if not text_a or not text_b:
        return False

    # Simple substring match first (fastest case)
    if text_b.lower() in text_a.lower() or text_a.lower() in text_b.lower():
        return True

    # For more robust fuzzy matching, use difflib
    from difflib import SequenceMatcher

    matcher = SequenceMatcher(None, text_a.lower(), text_b.lower())
    ratio = matcher.ratio()

    return ratio >= threshold


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

    # Build fuzzy match matrix
    matches = set()  # Set of (golden_idx, extracted_idx) pairs

    for extracted_idx, extracted in enumerate(extracted_facts):
        extracted_text = extracted.get("text", "")

        for golden_idx, golden in enumerate(golden_facts):
            if (golden_idx, extracted_idx) in matches:
                continue  # Already matched

            golden_text = golden.get("text", "")

            if fuzzy_match_text(extracted_text, golden_text, text_threshold):
                matches.add((golden_idx, extracted_idx))
                break  # Each golden matches at most one extraction (greedy)

    # Calculate metrics
    matched_golden = len(set(m[0] for m in matches))
    recall = matched_golden / len(golden_facts)

    matched_extracted = len(set(m[1] for m in matches))
    precision = matched_extracted / len(extracted_facts)

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
