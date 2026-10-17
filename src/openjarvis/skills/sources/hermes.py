"""HermesResolver — resolves skills from NousResearch/hermes-agent.

Layout:
    skills/<category>/<skill-name>/SKILL.md
    skills/<category>/DESCRIPTION.md  (skipped)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List

import yaml

from openjarvis.core.paths import get_config_dir
from openjarvis.skills.license import detect_skill_license
from openjarvis.skills.sources.base import ResolvedSkill, SourceResolver

LOGGER = logging.getLogger(__name__)

HERMES_REPO_URL = "https://github.com/NousResearch/hermes-agent.git"


class HermesResolver(SourceResolver):
    """Resolves skills from the Hermes Agent repository."""

    name = "hermes"

    def __init__(self, cache_root: Path | None = None) -> None:
        if cache_root is None:
            cache_root = get_config_dir() / "skill-cache" / "hermes"
        self._cache_root = Path(cache_root)

    def cache_dir(self) -> Path:
        return self._cache_root

    def sync(self) -> None:
        self._sync_git_cache(HERMES_REPO_URL)

    def list_skills(self) -> List[ResolvedSkill]:
        """Walk skills/<category>/<skill>/SKILL.md."""
        skills_root = self._cache_root / "skills"
        if not skills_root.exists():
            return []

        results: List[ResolvedSkill] = []
        commit = self._read_commit()

        for category_dir in sorted(skills_root.iterdir()):
            if not category_dir.is_dir():
                continue
            category = category_dir.name
            for skill_dir in sorted(category_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue  # skip DESCRIPTION.md and other files
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue

                # Read minimal frontmatter for the preview
                frontmatter = self._read_frontmatter(skill_md)
                name = str(frontmatter.get("name", skill_dir.name))
                description = str(frontmatter.get("description", ""))
                # Per-skill licence: frontmatter > skill-dir LICENSE >
                # repo-root LICENSE. "missing"/"unverified" is recorded,
                # never assumed.
                licence = detect_skill_license(
                    skill_dir, frontmatter, repo_root=self._cache_root
                )
                results.append(
                    ResolvedSkill(
                        name=name,
                        source=self.name,
                        path=skill_dir,
                        category=category,
                        description=description,
                        commit=commit,
                        sidecar_data={
                            "license": licence["license"],
                            "license_status": licence["status"],
                            "license_source": licence["source"],
                        },
                    )
                )

        return results

    def _read_frontmatter(self, skill_md: Path) -> dict:
        """Return the SKILL.md frontmatter dict ({} if absent/invalid)."""
        try:
            raw = skill_md.read_text(encoding="utf-8")
        except Exception:
            return {}
        if not raw.startswith("---"):
            return {}
        rest = raw[3:].lstrip("\n")
        end = rest.find("\n---")
        if end == -1:
            return {}
        try:
            fm = yaml.safe_load(rest[:end])
        except yaml.YAMLError:
            return {}
        return fm if isinstance(fm, dict) else {}

    def _read_commit(self) -> str:
        """Return the current HEAD SHA of the cached repo, or empty string."""
        if not (self._cache_root / ".git").exists():
            return ""
        try:
            result = subprocess.run(
                ["git", "-C", str(self._cache_root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""


__all__ = ["HermesResolver", "HERMES_REPO_URL"]
