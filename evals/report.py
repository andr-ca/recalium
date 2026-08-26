"""Evaluation report generation (markdown + JSON)."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from evals.checks import CheckResult


class ReportWriter:
    """Generates markdown and JSON reports from evaluation results."""

    def __init__(self, output_dir: str = "evals/results"):
        """Initialize report writer with output directory."""
        self.output_dir = output_dir
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.results_dir = Path(output_dir) / self.timestamp.replace(":", "-").split("Z")[0]
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def write_reports(
        self,
        checks: List[CheckResult],
        thresholds: Dict[str, Any],
        overall_passed: bool,
        raw_runs: List[List[CheckResult]] | None = None,
    ) -> Dict[str, str]:
        """
        Write markdown and JSON reports.

        Args:
            checks: List of CheckResult objects (aggregated, if n-runs > 1)
            thresholds: Thresholds dict (from thresholds.json)
            overall_passed: True if all checks passed thresholds
            raw_runs: optional per-run CheckResult lists (n-runs > 1 mode) —
                included in the JSON report under "raw_runs" for full
                transparency behind the aggregated mean/stdev metrics.

        Returns:
            Dict with keys 'markdown_path' and 'json_path'
        """
        # Generate markdown report
        markdown_path = self._write_markdown(checks, thresholds, overall_passed)

        # Generate JSON report
        json_path = self._write_json(checks, thresholds, overall_passed, raw_runs)

        return {
            "markdown_path": str(markdown_path),
            "json_path": str(json_path),
            "timestamp": self.timestamp,
        }

    def _write_markdown(
        self,
        checks: List[CheckResult],
        thresholds: Dict[str, Any],
        overall_passed: bool,
    ) -> Path:
        """Write markdown report."""
        md_path = self.results_dir / "report.md"

        with open(md_path, "w") as f:
            # Header
            f.write("# Recalium Evaluation Report\n\n")
            f.write(f"**Date:** {self.timestamp}\n\n")

            # Overall status
            status = "✓ PASSED" if overall_passed else "✗ FAILED"
            f.write(f"**Status:** {status}\n\n")

            # Summary table
            f.write("## Summary\n\n")
            f.write("| Check | Status | Skipped | Key Metrics |\n")
            f.write("|-------|--------|---------|-------------|\n")

            for check in checks:
                status_icon = "✓" if check.passed else "✗"
                skip_icon = "⊘" if check.skipped else ""

                # First 3 primary metrics — skip "_stdev" companions here so the
                # compact preview isn't crowded out by n-runs variance columns
                # (they're still shown in full in the detailed metrics table below).
                primary_metrics = [
                    (k, v) for k, v in check.metrics.items() if not k.endswith("_stdev")
                ]
                metrics_str = ", ".join(
                    f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                    for k, v in primary_metrics[:3]
                )

                f.write(f"| {check.name} | {status_icon} | {skip_icon} | {metrics_str} |\n")

            f.write("\n")

            # Detailed findings
            f.write("## Detailed Findings\n\n")

            for check in checks:
                f.write(f"### {check.name.upper()}\n\n")

                if check.skipped:
                    f.write(f"**Status:** Skipped\n\n")
                    f.write(f"**Reason:** {check.skip_reason}\n\n")
                else:
                    f.write(f"**Status:** {'PASSED' if check.passed else 'FAILED'}\n\n")
                    f.write(f"**Details:** {check.details}\n\n")

                    # Metrics table
                    if check.metrics:
                        f.write("**Metrics:**\n\n")
                        f.write("| Metric | Value |\n")
                        f.write("|--------|-------|\n")

                        for key, value in check.metrics.items():
                            if isinstance(value, float):
                                f.write(f"| {key} | {value:.4f} |\n")
                            else:
                                f.write(f"| {key} | {value} |\n")

                        f.write("\n")

            # Threshold comparison
            f.write("## Threshold Comparison\n\n")
            f.write("| Metric | Threshold | Operator | Status |\n")
            f.write("|--------|-----------|----------|--------|\n")

            threshold_values = thresholds.get("thresholds", {})
            for metric_name, threshold_info in threshold_values.items():
                threshold_val = threshold_info.get("value")
                operator = threshold_info.get("operator", ">=")
                # Find corresponding check metric
                check_metric = None
                for check in checks:
                    if metric_name in check.metrics:
                        check_metric = check.metrics[metric_name]
                        break

                if check_metric is not None:
                    if operator == ">=":
                        status_icon = "✓" if check_metric >= threshold_val else "✗"
                    elif operator == "<=":
                        status_icon = "✓" if check_metric <= threshold_val else "✗"
                    elif operator == "==":
                        status_icon = "✓" if check_metric == threshold_val else "✗"
                    else:
                        status_icon = "?"

                    f.write(f"| {metric_name} | {threshold_val} | {operator} | {status_icon} |\n")

            f.write("\n")

            # Recommendations
            f.write("## Recommendations\n\n")

            for check in checks:
                if not check.passed and not check.skipped:
                    if "recall" in check.metrics and check.metrics.get("recall", 1.0) < 0.6:
                        f.write(f"- **{check.name}:** Extraction recall < 0.6 may indicate:\n")
                        f.write(f"  - F3 (truncation on long conversations): test with long_conversation.json\n")
                        f.write(f"  - F4 (hallucinated spans filtering): verify span_fidelity metric\n")

                    if "latency_p95_ms" in check.metrics:
                        p95 = check.metrics.get("latency_p95_ms", 0)
                        if p95 > 2000:
                            f.write(f"- **{check.name}:** P95 latency {p95}ms exceeds 2s target.\n")
                            f.write(f"  - Check: database indexing, network latency, concurrent load\n")

            f.write("\n")

            # Footer
            f.write(f"*Report generated at {self.timestamp}*\n")

        return md_path

    def _write_json(
        self,
        checks: List[CheckResult],
        thresholds: Dict[str, Any],
        overall_passed: bool,
        raw_runs: List[List[CheckResult]] | None = None,
    ) -> Path:
        """Write JSON report."""
        json_path = self.results_dir / "results.json"

        def _serialize(check: CheckResult) -> Dict[str, Any]:
            return {
                "name": check.name,
                "passed": check.passed,
                "skipped": check.skipped,
                "skip_reason": check.skip_reason,
                "metrics": check.metrics,
                "details": check.details,
            }

        data = {
            "timestamp": self.timestamp,
            "overall_passed": overall_passed,
            "thresholds": thresholds.get("thresholds", {}),
            "checks": [_serialize(check) for check in checks],
        }

        if raw_runs:
            data["raw_runs"] = [
                [_serialize(check) for check in run] for run in raw_runs
            ]

        with open(json_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return json_path
