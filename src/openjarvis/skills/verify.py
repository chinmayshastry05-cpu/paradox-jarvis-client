"""Skill content verification (Phase 2).

Closes the matrix gap "skill contents never executed/verified" at the
static level: parse the skill, check its frontmatter, its
``allowed-tools`` against known tool names, that files it references
exist, that it contains no symlinks (escape), and what its licence
statement is. This does NOT execute the skill — execution stays behind
the importer (scripts opt-in) and the external-plugin runner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from openjarvis.skills.license import detect_skill_license
from openjarvis.skills.tool_translator import TOOL_TRANSLATION

# Tool names a skill may legitimately reference: external (Claude Code)
# names plus their OpenJarvis translations.
KNOWN_TOOL_NAMES = frozenset(TOOL_TRANSLATION) | frozenset(TOOL_TRANSLATION.values())

# Subdir prefixes a skill body may reference.
_REFERENCE_PREFIXES = ("scripts/", "references/", "assets/", "templates/")


@dataclass
class SkillVerification:
    """Static verification outcome for one skill directory."""

    name: str
    passed: bool
    issues: List[str] = field(default_factory=list)
    license: str = ""
    license_status: str = ""
    unknown_tools: List[str] = field(default_factory=list)
    missing_references: List[str] = field(default_factory=list)


def _parse_skill_md(path: Path) -> tuple[Dict[str, object], str]:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}, raw
    rest = raw[3:].lstrip("\n")
    end = rest.find("\n---")
    if end == -1:
        return {}, raw
    try:
        fm = yaml.safe_load(rest[:end])
    except yaml.YAMLError:
        fm = {}
    return (fm if isinstance(fm, dict) else {}), rest[end + 4 :].lstrip("\n")


def _allowed_tools(frontmatter: Dict[str, object]) -> List[str]:
    raw = frontmatter.get("allowed-tools", frontmatter.get("allowed_tools"))
    if isinstance(raw, str):
        return [t.strip() for t in re.split(r"[,\s]+", raw) if t.strip()]
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return []


def verify_skill(
    skill_dir: Path,
    *,
    repo_root: Optional[Path] = None,
    known_tools: Optional[frozenset[str]] = None,
) -> SkillVerification:
    """Statically verify the skill in *skill_dir*."""
    skill_dir = Path(skill_dir)
    issues: List[str] = []
    known = known_tools if known_tools is not None else KNOWN_TOOL_NAMES

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return SkillVerification(
            name=skill_dir.name, passed=False, issues=["missing SKILL.md"]
        )
    try:
        frontmatter, body = _parse_skill_md(skill_md)
    except (OSError, UnicodeDecodeError) as exc:
        return SkillVerification(
            name=skill_dir.name,
            passed=False,
            issues=[f"SKILL.md unreadable: {exc}"],
        )

    name = str(frontmatter.get("name", "") or skill_dir.name)
    if not str(frontmatter.get("name", "")).strip():
        issues.append("frontmatter missing 'name'")
    if not str(frontmatter.get("description", "")).strip():
        issues.append("frontmatter missing 'description'")
    if not body.strip():
        issues.append("SKILL.md body is empty")

    unknown_tools = [t for t in _allowed_tools(frontmatter) if t not in known]
    if unknown_tools:
        issues.append(f"unknown allowed-tools: {', '.join(unknown_tools)}")

    missing: List[str] = []
    for token in re.findall(r"(?:scripts|references|assets|templates)/[\w./-]+", body):
        token = token.rstrip(".,;:")
        if not (skill_dir / token).exists():
            missing.append(token)
    if missing:
        issues.append(f"referenced files missing: {', '.join(missing)}")

    symlinks = [p for p in skill_dir.rglob("*") if p.is_symlink()]
    if symlinks:
        issues.append(f"skill contains symlinks: {len(symlinks)}")

    licence = detect_skill_license(skill_dir, frontmatter, repo_root=repo_root)
    if licence["status"] in ("missing", "unverified"):
        issues.append(f"licence {licence['status']} (source: {licence['source']})")

    return SkillVerification(
        name=name,
        passed=not issues,
        issues=issues,
        license=licence["license"],
        license_status=licence["status"],
        unknown_tools=unknown_tools,
        missing_references=missing,
    )


__all__ = ["KNOWN_TOOL_NAMES", "SkillVerification", "verify_skill"]
