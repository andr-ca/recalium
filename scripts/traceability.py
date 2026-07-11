#!/usr/bin/env python3
"""Requirements traceability matrix generator (GPT5.6 #16).

Produces a single source of truth mapping every requirement ID in
``.planning/REQUIREMENTS.md`` to the tests that reference it, so a "done" claim
(``- [x]``) is backed by at least one test. The generated matrix
(``docs/operational/traceability-matrix.md``) is the one status authority; the
``--check`` mode is a CI gate that fails when a claimed-done requirement has no
referencing test.

Usage:
    python scripts/traceability.py            # print the matrix to stdout
    python scripts/traceability.py --write    # (re)write the matrix document
    python scripts/traceability.py --check    # exit 1 if a done requirement has no test
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_FILE = REPO_ROOT / ".planning" / "REQUIREMENTS.md"
SCAN_DIRS = [
    REPO_ROOT / "backend" / "tests",
    REPO_ROOT / "evals",
    REPO_ROOT / "frontend" / "src",
]
SCAN_SUFFIXES = {".py", ".ts", ".tsx"}
OUTPUT_FILE = REPO_ROOT / "docs" / "operational" / "traceability-matrix.md"

_REQ_LINE = re.compile(
    r"-\s*\[(?P<check>[ xX])\]\s*\*\*(?P<id>[A-Z]{2,6}-\d+)\*\*\s*:\s*(?P<text>.+)"
)
_ID_TOKEN = re.compile(r"\b([A-Z]{2,6}-\d+)\b")

# Requirements verified by non-automated means (infra/manual), with rationale.
# These are excluded from the --check gate but still shown in the matrix so the
# reason is explicit rather than silently missing.
MANUAL_VERIFICATION: dict[str, str] = {
    "BKUP-04": "Durability via Docker bind-mount volumes — verified by a restart/reboot drill, not unit tests.",
    "WEBUI-04": "Browser-support scope (Chromium only in v1) — verified manually, not via automated tests.",
}


@dataclass
class Requirement:
    """One requirement plus the tests that reference its ID."""

    id: str
    text: str
    claimed_done: bool
    tests: list[str] = field(default_factory=list)

    @property
    def covered(self) -> bool:
        return bool(self.tests)

    @property
    def category(self) -> str:
        return self.id.split("-", 1)[0]


def parse_requirements(text: str) -> list[Requirement]:
    """Extract requirements from REQUIREMENTS.md content."""
    reqs: list[Requirement] = []
    for line in text.splitlines():
        m = _REQ_LINE.match(line.strip())
        if m:
            reqs.append(
                Requirement(
                    id=m.group("id"),
                    text=m.group("text").strip(),
                    claimed_done=m.group("check").lower() == "x",
                )
            )
    return reqs


def find_references(ids: set[str], scan_dirs: list[Path]) -> dict[str, list[str]]:
    """Map each requirement id to the repo-relative files that reference it."""
    refs: dict[str, list[str]] = {i: [] for i in ids}
    for base in scan_dirs:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in SCAN_SUFFIXES or not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            found = {tok for tok in _ID_TOKEN.findall(content) if tok in ids}
            if not found:
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            for tok in found:
                if rel not in refs[tok]:
                    refs[tok].append(rel)
    return refs


def attach_references(reqs: list[Requirement], scan_dirs: list[Path]) -> list[Requirement]:
    """Populate each requirement's ``tests`` list from a scan."""
    refs = find_references({r.id for r in reqs}, scan_dirs)
    for req in reqs:
        req.tests = sorted(refs.get(req.id, []))
    return reqs


def coverage_gaps(reqs: list[Requirement]) -> list[Requirement]:
    """Requirements claimed done (``[x]``) but with no test and no manual note."""
    return [
        r
        for r in reqs
        if r.claimed_done and not r.covered and r.id not in MANUAL_VERIFICATION
    ]


def render_matrix(reqs: list[Requirement]) -> str:
    total = len(reqs)
    covered = sum(1 for r in reqs if r.covered)
    manual = [r for r in reqs if not r.covered and r.id in MANUAL_VERIFICATION]
    gaps = coverage_gaps(reqs)
    pct = (covered / total * 100) if total else 0.0

    lines = [
        "# Requirements Traceability Matrix",
        "",
        "> **Generated** by `scripts/traceability.py` — do not edit by hand. This is the",
        "> single status authority mapping each requirement to the tests that verify it.",
        "> Run `python scripts/traceability.py --check` in CI to fail on untested",
        "> claimed-done requirements.",
        "",
        f"- Requirements: **{total}**",
        f"- With \u2265 1 referencing test: **{covered}** ({pct:.0f}%)",
        f"- Verified manually (infra/scope): **{len(manual)}**",
        f"- Claimed done (`[x]`) but **no test / no manual note**: **{len(gaps)}**",
        "",
    ]
    if gaps:
        lines += ["## \u26a0\ufe0f Traceability gaps (claimed done, no test)", ""]
        for r in gaps:
            lines.append(f"- **{r.id}** — {r.text}")
        lines.append("")
    if manual:
        lines += ["## Manually verified (excluded from the --check gate)", ""]
        for r in manual:
            lines.append(f"- **{r.id}** — {MANUAL_VERIFICATION[r.id]}")
        lines.append("")

    by_cat: dict[str, list[Requirement]] = {}
    for r in reqs:
        by_cat.setdefault(r.category, []).append(r)

    lines += ["## Matrix", ""]
    for cat in sorted(by_cat):
        lines += [f"### {cat}", "", "| ID | Status | Tests | Requirement |", "| --- | --- | --- | --- |"]
        for r in by_cat[cat]:
            status = "\u2705 done" if r.claimed_done else "\u25cb open"
            if r.tests:
                test_cell = "<br>".join(f"`{t}`" for t in r.tests)
            elif r.id in MANUAL_VERIFICATION:
                test_cell = "_manual_"
            else:
                test_cell = "\u2014"
            text = r.text.replace("|", "\\|")
            lines.append(f"| {r.id} | {status} | {test_cell} | {text} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build() -> list[Requirement]:
    reqs = parse_requirements(REQUIREMENTS_FILE.read_text(encoding="utf-8"))
    return attach_references(reqs, SCAN_DIRS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the matrix document")
    parser.add_argument("--check", action="store_true", help="fail if a done requirement has no test")
    args = parser.parse_args(argv)

    reqs = build()
    matrix = render_matrix(reqs)

    if args.write:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(matrix, encoding="utf-8")
        print(f"Wrote {OUTPUT_FILE.relative_to(REPO_ROOT)}")
    else:
        print(matrix)

    if args.check:
        gaps = coverage_gaps(reqs)
        if gaps:
            print(
                f"\nTraceability check FAILED: {len(gaps)} claimed-done requirement(s) "
                "have no referencing test:",
                file=sys.stderr,
            )
            for r in gaps:
                print(f"  - {r.id}: {r.text}", file=sys.stderr)
            return 1
        print("\nTraceability check passed: every claimed-done requirement has a test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
