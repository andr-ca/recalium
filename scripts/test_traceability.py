"""Unit tests for the traceability generator (GPT5.6 #16)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from traceability import (  # noqa: E402
    MANUAL_VERIFICATION,
    Requirement,
    coverage_gaps,
    parse_requirements,
    render_matrix,
)

SAMPLE = """
## Ingestion
- [x] **INGT-01**: User can import via paste
- [ ] **INGT-99**: Not done yet
- [x] **BKUP-04**: Durability via volumes
Some prose mentioning PIPE-01 that is not a checkbox line.
"""


def test_parse_requirements_extracts_id_text_and_status():
    reqs = parse_requirements(SAMPLE)
    ids = {r.id: r for r in reqs}
    assert set(ids) == {"INGT-01", "INGT-99", "BKUP-04"}
    assert ids["INGT-01"].claimed_done is True
    assert ids["INGT-99"].claimed_done is False
    assert ids["INGT-01"].text == "User can import via paste"
    assert ids["INGT-01"].category == "INGT"


def test_coverage_gaps_flags_done_without_tests():
    done_untested = Requirement(id="INGT-01", text="x", claimed_done=True)
    open_item = Requirement(id="INGT-99", text="y", claimed_done=False)
    covered = Requirement(id="PIPE-01", text="z", claimed_done=True, tests=["t.py"])
    gaps = coverage_gaps([done_untested, open_item, covered])
    assert [g.id for g in gaps] == ["INGT-01"]


def test_coverage_gaps_excludes_manual_verification():
    manual_id = next(iter(MANUAL_VERIFICATION))
    r = Requirement(id=manual_id, text="infra", claimed_done=True)
    assert coverage_gaps([r]) == []


def test_render_matrix_smoke():
    reqs = parse_requirements(SAMPLE)
    reqs[0].tests = ["backend/tests/test_ingest.py"]
    out = render_matrix(reqs)
    assert "# Requirements Traceability Matrix" in out
    assert "INGT-01" in out
    assert "backend/tests/test_ingest.py" in out
