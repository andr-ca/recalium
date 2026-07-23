"""N-run aggregation for the eval suite (mean + stdev across repeated runs).

A single eval run against a local model (or any non-deterministic provider)
is one noisy sample. This module combines several independent runs of the
same check suite into one aggregated CheckResult per check, so a gate
decision reflects a sustained measurement rather than a lucky/unlucky draw.
"""

import statistics
from typing import Any, Dict, List

from evals.checks import CheckResult


def aggregate_check_results(all_runs: List[List[CheckResult]]) -> List[CheckResult]:
    """Aggregate N runs of the same check suite into one result per check.

    Args:
        all_runs: one List[CheckResult] per run, in the same check order.

    Returns:
        One aggregated CheckResult per check name. For each numeric metric,
        the aggregated value is the mean across runs that weren't skipped,
        with a parallel "<metric>_stdev" key (0.0 when only one sample).
        A check is aggregated `passed` only if every non-skipped run passed
        (a gate must be sustained, not just hit once); it is `skipped` only
        if every run skipped it.
    """
    if not all_runs:
        return []

    by_name: Dict[str, List[CheckResult]] = {}
    order: List[str] = []
    for run in all_runs:
        for check in run:
            if check.name not in by_name:
                by_name[check.name] = []
                order.append(check.name)
            by_name[check.name].append(check)

    aggregated: List[CheckResult] = []
    for name in order:
        results = by_name[name]
        non_skipped = [r for r in results if not r.skipped]

        if not non_skipped:
            aggregated.append(CheckResult(
                name=name,
                passed=False,
                metrics={},
                details=f"All {len(results)} run(s) skipped.",
                skipped=True,
                skip_reason=results[0].skip_reason,
            ))
            continue

        metrics = _aggregate_metrics(non_skipped)
        passed = all(r.passed for r in non_skipped)
        n = len(non_skipped)
        skipped_count = len(results) - n
        details = (
            f"Aggregated over {n} run(s)"
            + (f" ({skipped_count} skipped)" if skipped_count else "")
            + f": {non_skipped[-1].details}"
        )

        aggregated.append(CheckResult(
            name=name,
            passed=passed,
            metrics=metrics,
            details=details,
            skipped=False,
            skip_reason="",
        ))

    return aggregated


def _aggregate_metrics(results: List[CheckResult]) -> Dict[str, Any]:
    """Mean + stdev per numeric metric key; non-numeric keys pass through from the last run."""
    keys: List[str] = []
    for r in results:
        for key in r.metrics:
            if key not in keys:
                keys.append(key)

    aggregated: Dict[str, Any] = {}
    for key in keys:
        values = [r.metrics[key] for r in results if key in r.metrics]
        numeric = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]

        if len(numeric) == len(values) and numeric:
            aggregated[key] = statistics.fmean(numeric)
            aggregated[f"{key}_stdev"] = statistics.stdev(numeric) if len(numeric) > 1 else 0.0
        else:
            # Non-numeric metric (or missing on some runs): keep the most recent value.
            aggregated[key] = values[-1] if values else None

    return aggregated
