"""Unit tests for N-run aggregation (mean + stdev, sustained pass/fail).

Run: python -m pytest evals/test_aggregate.py -q  (from the repo root)
"""
from evals.aggregate import aggregate_check_results
from evals.checks import CheckResult


def _result(name, passed, metrics, skipped=False, skip_reason=""):
    return CheckResult(
        name=name,
        passed=passed,
        metrics=metrics,
        details=f"{name} details",
        skipped=skipped,
        skip_reason=skip_reason,
    )


def test_mean_and_stdev_computed_across_runs():
    runs = [
        [_result("extraction", True, {"recall": 0.6, "precision": 0.8})],
        [_result("extraction", True, {"recall": 0.8, "precision": 0.8})],
    ]
    aggregated = aggregate_check_results(runs)
    assert len(aggregated) == 1
    metrics = aggregated[0].metrics
    assert abs(metrics["recall"] - 0.7) < 1e-9
    assert metrics["recall_stdev"] > 0.0
    assert abs(metrics["precision"] - 0.8) < 1e-9
    assert metrics["precision_stdev"] == 0.0


def test_single_run_has_zero_stdev():
    runs = [[_result("ingest", True, {"latency_p95_ms": 40.0})]]
    aggregated = aggregate_check_results(runs)
    assert aggregated[0].metrics["latency_p95_ms_stdev"] == 0.0


def test_passed_requires_every_non_skipped_run_to_pass():
    runs = [
        [_result("extraction", True, {"recall": 0.65})],
        [_result("extraction", False, {"recall": 0.55})],
        [_result("extraction", True, {"recall": 0.70})],
    ]
    aggregated = aggregate_check_results(runs)
    assert aggregated[0].passed is False
    assert abs(aggregated[0].metrics["recall"] - 0.6333333333) < 1e-6


def test_all_runs_skipped_is_skipped():
    runs = [
        [_result("mcp", False, {}, skipped=True, skip_reason="no provider")],
        [_result("mcp", False, {}, skipped=True, skip_reason="no provider")],
    ]
    aggregated = aggregate_check_results(runs)
    assert aggregated[0].skipped is True
    assert aggregated[0].skip_reason == "no provider"


def test_some_runs_skipped_averages_only_non_skipped():
    runs = [
        [_result("sensitivity", True, {"leaked_fact_count": 0.0})],
        [_result("sensitivity", False, {}, skipped=True, skip_reason="flaky")],
    ]
    aggregated = aggregate_check_results(runs)
    assert aggregated[0].skipped is False
    assert aggregated[0].passed is True
    assert aggregated[0].metrics["leaked_fact_count"] == 0.0
    # Partial skip must leave a signal even though skipped=False, so strict
    # mode (which only checks .skipped) doesn't miss it (Copilot review, PR #34).
    assert aggregated[0].skip_reason != ""
    assert "flaky" in aggregated[0].skip_reason


def test_no_partial_skip_has_empty_skip_reason():
    runs = [
        [_result("sensitivity", True, {"leaked_fact_count": 0.0})],
        [_result("sensitivity", True, {"leaked_fact_count": 0.0})],
    ]
    aggregated = aggregate_check_results(runs)
    assert aggregated[0].skip_reason == ""


def test_preserves_check_order_from_first_run():
    runs = [
        [_result("ingest", True, {}), _result("extraction", True, {})],
        [_result("extraction", True, {}), _result("ingest", True, {})],
    ]
    aggregated = aggregate_check_results(runs)
    assert [c.name for c in aggregated] == ["ingest", "extraction"]


def test_empty_runs_returns_empty_list():
    assert aggregate_check_results([]) == []
