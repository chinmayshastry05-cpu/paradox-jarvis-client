"""Per-skill licence detection (Phase 2).

Closes the matrix gap "per-skill licences unchecked": every resolved
skill records where its licence statement came from and whether it
matched a known licence marker. A frontmatter ``license:`` value is
self-asserted (status ``declared``); a LICENSE file whose text matches
a known marker is ``verified``; anything else is ``unverified``;
no statement at all is ``missing``. Only ``verified`` counts as a
confirmed licence — the importer surfaces the rest as warnings.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

# SPDX-ish marker -> licence id. Matched against LICENSE file text or a
# frontmatter value (case-insensitive substring).
_LICENSE_MARKERS: Tuple[Tuple[str, str], ...] = (
    ("mit license", "MIT"),
    ("apache license", "Apache-2.0"),
    ("bsd 3-clause", "BSD-3-Clause"),
    ("bsd 2-clause", "BSD-2-Clause"),
    ("gnu affero general public license", "AGPL-3.0"),
    ("gnu general public license", "GPL"),
    ("mozilla public license", "MPL-2.0"),
    ("isc license", "ISC"),
    ("creative commons zero", "CC0-1.0"),
    ("the unlicense", "Unlicense"),
)

_LICENSE_FILE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md")


def _match_marker(text: str) -> Optional[str]:
    lowered = text.lower()
    for marker, licence in _LICENSE_MARKERS:
        if marker in lowered:
            return licence
    # Bare SPDX ids in a frontmatter value, e.g. "license: MIT".
    stripped = text.strip()
    if re.fullmatch(r"[A-Za-z0-9.+-]+", stripped or "") and stripped.upper() in {
        "MIT",
        "APACHE-2.0",
        "BSD-3-CLAUSE",
        "BSD-2-CLAUSE",
        "AGPL-3.0",
        "GPL-3.0",
        "GPL-2.0",
        "MPL-2.0",
        "ISC",
        "CC0-1.0",
        "UNLICENSE",
    }:
        return stripped.upper()
    return None


def _read_license_file(directory: Path) -> Optional[str]:
    for name in _LICENSE_FILE_NAMES:
        candidate = directory / name
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8", errors="replace")[:4096]
        except OSError:
            continue
    return None


def detect_skill_license(
    skill_dir: Path,
    frontmatter: Optional[Dict[str, object]] = None,
    *,
    repo_root: Optional[Path] = None,
) -> Dict[str, str]:
    """Detect a skill's licence. Returns license/status/source keys.

    Precedence: frontmatter ``license`` (declared) > skill-dir LICENSE
    file (verified/unverified) > repo-root LICENSE file (verified/
    unverified) > missing.
    """
    fm = frontmatter or {}
    declared = fm.get("license")
    if isinstance(declared, str) and declared.strip():
        matched = _match_marker(declared)
        return {
            "license": matched or declared.strip(),
            "status": "declared" if matched is None else "verified",
            "source": "frontmatter",
        }

    text = _read_license_file(Path(skill_dir))
    if text is not None:
        matched = _match_marker(text)
        return {
            "license": matched or "unknown",
            "status": "verified" if matched else "unverified",
            "source": "skill-dir",
        }

    if repo_root is not None:
        text = _read_license_file(Path(repo_root))
        if text is not None:
            matched = _match_marker(text)
            return {
                "license": matched or "unknown",
                "status": "verified" if matched else "unverified",
                "source": "repo-root",
            }

    return {"license": "", "status": "missing", "source": "none"}


__all__ = ["detect_skill_license"]
