#!/usr/bin/env python3
"""
sync-agents.py — Sync agents and skills between VS Code user profile and project .github directory.

Canonical names are read once from .github/agents/*.agent.md (files without the prj- prefix).

Directions:
    push   Copy user-profile agents/skills → .github/{agents,skills}/, adding 'prj-' prefix.
                     Internal cross-references (agents:, handoffs agent:, backtick names in body) are
                     rewritten to use the prefixed names.
    pull   Copy .github/agents/prj-* and .github/skills/prj-* → user profile, removing prefix.
                     If no prefixed project copy exists, pull falls back to the non-prefixed canonical
                     project file/directory. Internal cross-references are rewritten to remove the prefix.

Usage:
  python sync-agents.py push [options]
  python sync-agents.py pull [options]

Options:
  --project-dir DIR       Project root (default: current directory)
  --user-agents-dir DIR   User-level agents dir
                          (default Linux: ~/.config/Code/User/prompts)
                          (default macOS: ~/Library/Application Support/Code/User/prompts)
  --user-skills-dir DIR   User-level skills dir (default: ~/.agents/skills)
  --only-agents           Sync agents only
  --only-skills           Sync skills only
  --dry-run               Show what would happen without making changes
"""

from __future__ import annotations

import argparse
import platform
import re
import shutil
import sys
from pathlib import Path

PREFIX = "prj-"
CANONICAL_AGENTS_FILE = ".github/agents/canonical-agents.txt"
CANONICAL_SKILLS_FILE = ".github/skills/canonical-skills.txt"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent_stem(filename: str) -> str:
    """'developer.agent.md' → 'developer'."""
    if filename.endswith(".agent.md"):
        return filename[: -len(".agent.md")]
    return filename


def _default_user_agents_dir() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User" / "prompts"
    return Path.home() / ".config" / "Code" / "User" / "prompts"


def _default_user_skills_dir(explicit: Path | None) -> Path:
    candidates = [
        Path.home() / ".agents" / "skills",
        Path.home() / ".copilot" / "skills",
        Path.home() / ".claude" / "skills",
    ]
    if explicit and explicit.exists():
        return explicit
    for c in candidates:
        if c.exists():
            return c
    return explicit or candidates[0]


# ---------------------------------------------------------------------------
# Frontmatter split / join
# ---------------------------------------------------------------------------


def _split_frontmatter(content: str) -> tuple[str, str]:
    """
    Returns (frontmatter_yaml, body_with_leading_newline).
    If there is no valid frontmatter, returns ('', content).
    """
    if not content.startswith("---"):
        return ("", content)
    rest = content[3:]
    m = re.search(r"^---[ \t]*$", rest, re.MULTILINE)
    if not m:
        return ("", content)
    frontmatter = rest[: m.start()].strip()
    body = rest[m.end() :]  # keeps leading newlines
    return (frontmatter, body)


def _join_frontmatter(frontmatter: str, body: str) -> str:
    return f"---\n{frontmatter}\n---{body}"


# ---------------------------------------------------------------------------
# Frontmatter field rewriters
# ---------------------------------------------------------------------------


def _rewrite_name(fm: str, base_name: str, add_prefix: bool) -> str:
    """Rewrite the 'name:' scalar field."""
    if add_prefix:
        old, new = base_name, f"{PREFIX}{base_name}"
    else:
        old, new = f"{PREFIX}{base_name}", base_name

    return re.sub(
        r"(?m)^(name:\s*)" + re.escape(old) + r"(\s*)$",
        r"\g<1>" + new + r"\2",
        fm,
    )


def _rewrite_agents_array(fm: str, canonical: set[str], add_prefix: bool) -> str:
    """Rewrite the 'agents:' YAML inline-array field."""

    def _replace_name(nm: re.Match) -> str:
        q, name = nm.group(1), nm.group(2)
        if add_prefix:
            if name in canonical and not name.startswith(PREFIX):
                return f"{q}{PREFIX}{name}{q}"
        else:
            if name.startswith(PREFIX) and name[len(PREFIX) :] in canonical:
                return f"{q}{name[len(PREFIX):]}{q}"
        return nm.group(0)

    def _process_agents_line(line_match: re.Match) -> str:
        return re.sub(r"(['\"])([^'\"]+)\1", _replace_name, line_match.group(0))

    return re.sub(r"(?m)^agents:.*$", _process_agents_line, fm)


def _rewrite_handoffs_agent(fm: str, canonical: set[str], add_prefix: bool) -> str:
    """Rewrite agent: "name" inside the handoffs inline value."""

    def _make_replacer(q: str):
        def _r(m: re.Match) -> str:
            name = m.group(1)
            if add_prefix:
                if name in canonical and not name.startswith(PREFIX):
                    return f"agent: {q}{PREFIX}{name}{q}"
            else:
                if name.startswith(PREFIX) and name[len(PREFIX) :] in canonical:
                    return f"agent: {q}{name[len(PREFIX):]}{q}"
            return m.group(0)

        return _r

    # \bagent\b: … prevents matching 'agents:'
    fm = re.sub(r'\bagent\b:\s+"([^"]+)"', _make_replacer('"'), fm)
    fm = re.sub(r"\bagent\b:\s+'([^']+)'", _make_replacer("'"), fm)
    return fm


def _rewrite_body_backticks(body: str, canonical: set[str], add_prefix: bool) -> str:
    """Rewrite `agent-name` back-tick references in the body."""

    def _r(m: re.Match) -> str:
        name = m.group(1)
        if add_prefix:
            if name in canonical and not name.startswith(PREFIX):
                return f"`{PREFIX}{name}`"
        else:
            if name.startswith(PREFIX) and name[len(PREFIX) :] in canonical:
                return f"`{name[len(PREFIX):]}`"
        return m.group(0)

    return re.sub(r"`([^`\n]+)`", _r, body)


def _transform_agent(content: str, base_name: str, canonical: set[str], add_prefix: bool) -> str:
    """Apply all rewrite rules to an agent file's content."""
    fm, body = _split_frontmatter(content)
    if not fm and not body:
        return content

    if fm:
        fm = _rewrite_name(fm, base_name, add_prefix)
        fm = _rewrite_agents_array(fm, canonical, add_prefix)
        fm = _rewrite_handoffs_agent(fm, canonical, add_prefix)
        body = _rewrite_body_backticks(body, canonical, add_prefix)
        return _join_frontmatter(fm, body)

    # No frontmatter — just rewrite body
    return _rewrite_body_backticks(content, canonical, add_prefix)


# ---------------------------------------------------------------------------
# Canonical name manifest helpers
# ---------------------------------------------------------------------------


def _load_canonical_manifest(manifest: Path) -> set[str] | None:
    """Return the persisted canonical set, or None if the manifest doesn't exist."""
    if not manifest.exists():
        return None
    names = {line.strip() for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()}
    return names or None


def _save_canonical_manifest(manifest: Path, names: set[str], dry_run: bool) -> None:
    if dry_run:
        return
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(sorted(names)) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Agent sync
# ---------------------------------------------------------------------------


def _canonical_agent_names(project_agents_dir: Path, manifest: Path, dry_run: bool) -> set[str]:
    """Return canonical agent names, reading from manifest if it exists.

    On first run (manifest absent) the names are discovered from non-prefixed
    *.agent.md files in project_agents_dir and the manifest is written so the
    set stays stable on subsequent runs even after the originals are removed.
    """
    saved = _load_canonical_manifest(manifest)
    if saved is not None:
        return saved

    # First-time discovery
    if not project_agents_dir.exists():
        return set()
    discovered = {
        _agent_stem(f.name)
        for f in project_agents_dir.glob("*.agent.md")
        if not _agent_stem(f.name).startswith(PREFIX)
    }
    if discovered:
        _save_canonical_manifest(manifest, discovered, dry_run)
        action = "(dry-run, not written)" if dry_run else "written"
        print(f"  MANIFEST {manifest}  [{action}]")
    return discovered


def push_agents(
    user_agents_dir: Path,
    project_agents_dir: Path,
    canonical: set[str],
    dry_run: bool,
) -> None:
    print(f"\n[AGENTS push]  {user_agents_dir}  →  {project_agents_dir}")

    for name in sorted(canonical):
        src = user_agents_dir / f"{name}.agent.md"
        dst = project_agents_dir / f"{PREFIX}{name}.agent.md"

        if not src.exists():
            print(f"  SKIP   {name}: not found in user agents dir")
            continue

        content = src.read_text(encoding="utf-8")
        new_content = _transform_agent(content, name, canonical, add_prefix=True)

        if dry_run:
            print(f"  DRY    {src.name} → {dst.name}")
        else:
            project_agents_dir.mkdir(parents=True, exist_ok=True)
            dst.write_text(new_content, encoding="utf-8")
            print(f"  WRITE  {src.name} → {dst.name}")


def pull_agents(
    project_agents_dir: Path,
    user_agents_dir: Path,
    canonical: set[str],
    dry_run: bool,
) -> None:
    print(f"\n[AGENTS pull]  {project_agents_dir}  →  {user_agents_dir}")

    for name in sorted(canonical):
        prefixed_src = project_agents_dir / f"{PREFIX}{name}.agent.md"
        canonical_src = project_agents_dir / f"{name}.agent.md"
        src = prefixed_src if prefixed_src.exists() else canonical_src
        dst = user_agents_dir / f"{name}.agent.md"

        if not src.exists():
            print(f"  SKIP   {name}: neither {prefixed_src.name} nor {canonical_src.name} found in project agents dir")
            continue

        content = src.read_text(encoding="utf-8")
        new_content = _transform_agent(content, name, canonical, add_prefix=False)

        if dry_run:
            print(f"  DRY    {src.name} → {dst.name}")
        else:
            user_agents_dir.mkdir(parents=True, exist_ok=True)
            dst.write_text(new_content, encoding="utf-8")
            print(f"  WRITE  {src.name} → {dst.name}")


# ---------------------------------------------------------------------------
# Skills sync
# ---------------------------------------------------------------------------


def _canonical_skill_names(project_skills_dir: Path, manifest: Path, dry_run: bool) -> set[str]:
    """Return canonical skill names, reading from manifest if it exists.

    On first run the names are discovered from non-prefixed skill subdirs
    and the manifest is written for stability on subsequent runs.
    """
    saved = _load_canonical_manifest(manifest)
    if saved is not None:
        return saved

    if not project_skills_dir.exists():
        return set()
    discovered = {
        d.name
        for d in project_skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists() and not d.name.startswith(PREFIX)
    }
    if discovered:
        _save_canonical_manifest(manifest, discovered, dry_run)
        action = "(dry-run, not written)" if dry_run else "written"
        print(f"  MANIFEST {manifest}  [{action}]")
    return discovered


def _rewrite_skill_name(content: str, base_name: str, add_prefix: bool) -> str:
    if add_prefix:
        old, new = base_name, f"{PREFIX}{base_name}"
    else:
        old, new = f"{PREFIX}{base_name}", base_name
    return re.sub(
        r"(?m)^(name:\s*)" + re.escape(old) + r"(\s*)$",
        r"\g<1>" + new + r"\2",
        content,
    )


def _copy_skill_dir(
    src: Path, dst: Path, base_name: str, add_prefix: bool, dry_run: bool
) -> None:
    if dry_run:
        print(f"  DRY    {src.name}/ → {dst.name}/")
        return

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    skill_md = dst / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        skill_md.write_text(_rewrite_skill_name(content, base_name, add_prefix), encoding="utf-8")

    print(f"  WRITE  {src.name}/ → {dst.name}/")


def push_skills(
    user_skills_dir: Path,
    project_skills_dir: Path,
    canonical: set[str],
    dry_run: bool,
) -> None:
    print(f"\n[SKILLS push]  {user_skills_dir}  →  {project_skills_dir}")

    if not canonical:
        print("  (no canonical skill names in project — skipping)")
        return

    for name in sorted(canonical):
        src = user_skills_dir / name
        dst = project_skills_dir / f"{PREFIX}{name}"

        if not src.exists():
            print(f"  SKIP   {name}: not found in user skills dir")
            continue

        _copy_skill_dir(src, dst, name, add_prefix=True, dry_run=dry_run)


def pull_skills(
    project_skills_dir: Path,
    user_skills_dir: Path,
    canonical: set[str],
    dry_run: bool,
) -> None:
    print(f"\n[SKILLS pull]  {project_skills_dir}  →  {user_skills_dir}")

    if not canonical:
        print("  (no canonical skill names in project — skipping)")
        return

    for name in sorted(canonical):
        prefixed_src = project_skills_dir / f"{PREFIX}{name}"
        canonical_src = project_skills_dir / name
        src = prefixed_src if prefixed_src.exists() else canonical_src
        dst = user_skills_dir / name

        if not src.exists():
            print(f"  SKIP   {name}: neither {prefixed_src.name}/ nor {canonical_src.name}/ found in project skills dir")
            continue

        _copy_skill_dir(src, dst, name, add_prefix=False, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "direction",
        choices=["push", "pull"],
        help="push: user profile → project (.github), pull: project → user profile",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        metavar="DIR",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--user-agents-dir",
        metavar="DIR",
        help="User-level agents directory (default: platform-specific Code/User/prompts)",
    )
    parser.add_argument(
        "--user-skills-dir",
        metavar="DIR",
        help="User-level skills directory (default: ~/.agents/skills)",
    )
    parser.add_argument("--only-agents", action="store_true", help="Sync agents only")
    parser.add_argument("--only-skills", action="store_true", help="Sync skills only")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing files",
    )

    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    project_agents_dir = project_dir / ".github" / "agents"
    project_skills_dir = project_dir / ".github" / "skills"
    agents_manifest = project_dir / CANONICAL_AGENTS_FILE
    skills_manifest = project_dir / CANONICAL_SKILLS_FILE

    if not project_agents_dir.exists():
        print(
            f"error: project agents directory not found: {project_agents_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    user_agents_dir = (
        Path(args.user_agents_dir).expanduser()
        if args.user_agents_dir
        else _default_user_agents_dir()
    )
    user_skills_dir = _default_user_skills_dir(
        Path(args.user_skills_dir).expanduser() if args.user_skills_dir else None
    )

    # ---- read or discover canonical names (persisted after first run) ----
    canonical_agents = _canonical_agent_names(project_agents_dir, agents_manifest, args.dry_run)
    canonical_skills = _canonical_skill_names(project_skills_dir, skills_manifest, args.dry_run)

    print(f"Project dir      : {project_dir}")
    print(f"User agents dir  : {user_agents_dir}")
    print(f"User skills dir  : {user_skills_dir}")
    print(
        f"Canonical agents ({len(canonical_agents)}): "
        + (", ".join(sorted(canonical_agents)) or "(none)")
    )
    print(
        f"Canonical skills ({len(canonical_skills)}): "
        + (", ".join(sorted(canonical_skills)) or "(none)")
    )

    if args.dry_run:
        print("\nDRY RUN — no files will be written")

    sync_agents = not args.only_skills
    sync_skills = not args.only_agents

    if args.direction == "push":
        if sync_agents:
            push_agents(user_agents_dir, project_agents_dir, canonical_agents, args.dry_run)
        if sync_skills:
            push_skills(user_skills_dir, project_skills_dir, canonical_skills, args.dry_run)
    else:  # pull
        if sync_agents:
            pull_agents(project_agents_dir, user_agents_dir, canonical_agents, args.dry_run)
        if sync_skills:
            pull_skills(project_skills_dir, user_skills_dir, canonical_skills, args.dry_run)


if __name__ == "__main__":
    main()
