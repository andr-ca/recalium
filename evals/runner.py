#!/usr/bin/env python3
"""Recalium evaluation suite runner.

CLI entry point for running all evaluation checks against a live Recalium stack.

Usage:
    python evals/runner.py --base-url http://localhost:8000 --output-dir evals/results

Or via make:
    make eval
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add repo root to path so evals can be imported from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from evals.checks import CheckResult
from evals.checks.eval_ingest import run_check as run_ingest_check
from evals.checks.eval_extraction import run_check as run_extraction_check
from evals.checks.eval_retrieval import run_check as run_retrieval_check
from evals.checks.eval_sensitivity import run_check as run_sensitivity_check
from evals.checks.eval_mcp import run_check as run_mcp_check
from evals.report import ReportWriter


async def load_golden_dataset(golden_path: str = "evals/datasets/golden.json") -> Dict[str, Any]:
    """Load golden labels from JSON file."""
    try:
        with open(golden_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Golden dataset not found at {golden_path}")
        sys.exit(1)


async def load_thresholds(thresholds_path: str = "evals/thresholds.json") -> Dict[str, Any]:
    """Load threshold configuration from JSON file."""
    try:
        with open(thresholds_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Thresholds file not found at {thresholds_path}")
        sys.exit(1)


async def health_check(client: httpx.AsyncClient, base_url: str) -> bool:
    """Check if Recalium stack is up and responding."""
    try:
        response = await client.get(f"{base_url}/api/health", timeout=5.0)
        return response.status_code == 200
    except Exception as e:
        return False


async def run_all_checks(
    client: httpx.AsyncClient,
    golden: Dict[str, Any],
    settings: Dict[str, Any],
) -> List[CheckResult]:
    """Run all evaluation checks."""
    print("Running evaluation checks...")
    checks: List[CheckResult] = []

    # Define checks to run
    check_functions = [
        ("ingest", run_ingest_check),
        ("extraction", run_extraction_check),
        ("retrieval", run_retrieval_check),
        ("sensitivity", run_sensitivity_check),
        ("mcp", run_mcp_check),
    ]

    for check_name, check_fn in check_functions:
        print(f"  Running {check_name} check...", end=" ", flush=True)
        try:
            result = await check_fn(client, golden, settings)
            checks.append(result)

            if result.skipped:
                print(f"SKIPPED ({result.skip_reason})")
            elif result.passed:
                print("✓ PASSED")
            else:
                print("✗ FAILED")

        except Exception as e:
            print(f"ERROR: {e}")
            # Create error check result
            checks.append(CheckResult(
                name=check_name,
                passed=False,
                metrics={},
                details=f"Check failed with error: {e}",
                skipped=True,
                skip_reason=f"Exception: {e}",
            ))

    return checks


def determine_overall_status(
    checks: List[CheckResult],
    *,
    strict: bool,
) -> tuple[bool, List[CheckResult]]:
    """Compute (overall_passed, skipped_checks) for a run (GPT5.6 #3).

    A run with no executed (non-skipped) checks never passes — an all-skipped or
    all-errored suite cannot report success. In strict (release) mode, ANY skipped or
    errored check fails the run, so a green eval can never hide omitted coverage.
    """
    non_skipped = [c for c in checks if not c.skipped]
    skipped = [c for c in checks if c.skipped]
    overall_passed = bool(non_skipped) and all(c.passed for c in non_skipped)
    if strict and skipped:
        overall_passed = False
    return overall_passed, skipped


async def main():
    """Main entry point for eval runner."""
    parser = argparse.ArgumentParser(
        description="Recalium evaluation suite runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evals/runner.py --base-url http://localhost:8000
  python evals/runner.py --base-url http://localhost:8000 --output-dir ./results
  make eval  # Via Makefile target
        """,
    )

    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of Recalium API (default: http://localhost:8000)",
    )

    # Defaults resolve relative to this file so the runner works from any CWD
    evals_root = Path(__file__).resolve().parent

    parser.add_argument(
        "--output-dir",
        default=str(evals_root / "results"),
        help="Output directory for reports (default: evals/results)",
    )

    parser.add_argument(
        "--golden",
        default=str(evals_root / "datasets" / "golden.json"),
        help="Path to golden dataset (default: evals/datasets/golden.json)",
    )

    parser.add_argument(
        "--thresholds",
        default=str(evals_root / "thresholds.json"),
        help="Path to thresholds config (default: evals/thresholds.json)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Release mode: fail on ANY skipped or errored check (no fail-open).",
    )

    args = parser.parse_args()

    print(f"Recalium Evaluation Suite")
    print(f"========================\n")

    # Load configuration
    print(f"Loading configuration...")
    golden = await load_golden_dataset(args.golden)
    thresholds = await load_thresholds(args.thresholds)

    settings = {
        "base_url": args.base_url,
        "output_dir": args.output_dir,
    }

    # Health check
    print(f"Checking stack health at {args.base_url}...", end=" ", flush=True)
    async with httpx.AsyncClient() as client:
        is_healthy = await health_check(client, args.base_url)

        if not is_healthy:
            print("✗ DOWN")
            print(f"\nError: Recalium stack is not responding at {args.base_url}")
            print(f"Please start the stack: docker compose up -d")
            sys.exit(1)

        print("✓ OK\n")

        # Run all checks
        checks = await run_all_checks(client, golden, settings)

    # Determine overall status (GPT5.6 #3): no executed checks never passes, and
    # strict/release mode fails on any skipped or errored check.
    overall_passed, skipped_checks = determine_overall_status(checks, strict=args.strict)
    if args.strict and skipped_checks:
        print("STRICT: failing because checks were skipped or errored:")
        for c in skipped_checks:
            print(f"  - {c.name}: {c.skip_reason}")

    print(f"\n")

    # Generate reports
    print(f"Generating reports...")
    report_writer = ReportWriter(args.output_dir)
    report_paths = report_writer.write_reports(checks, thresholds, overall_passed)

    print(f"  Markdown: {report_paths['markdown_path']}")
    print(f"  JSON: {report_paths['json_path']}")

    # Summary
    print(f"\n")
    print(f"Evaluation Summary")
    print(f"=================")
    print(f"Overall Status: {'✓ PASSED' if overall_passed else '✗ FAILED'}")
    print(f"Checks: {len([c for c in checks if c.passed])}/{len([c for c in checks if not c.skipped])} passed")
    print(f"Skipped: {len([c for c in checks if c.skipped])} (with reasons)")

    # Exit code
    exit_code = 0 if overall_passed else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEval suite interrupted by user")
        sys.exit(1)
