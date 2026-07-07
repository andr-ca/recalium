"""Evaluation checks for Recalium assessment suite."""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class CheckResult:
    """Result of a single evaluation check."""
    name: str  # Name of the check (e.g., "ingest", "extraction")
    passed: bool  # True if all thresholds met
    metrics: Dict[str, Any]  # Key metric measurements
    details: str  # Human-readable summary
    skipped: bool = False  # True if check was skipped (stack down, no key, etc.)
    skip_reason: str = ""  # Reason for skip if applicable


__all__ = ["CheckResult"]
