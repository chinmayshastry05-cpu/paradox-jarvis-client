"""Desktop GUI settings for Paradox Jarvis Ultra (Phase 6).

Appearance + behaviour preferences for the desktop app. These are
pure UI preferences — they NEVER disable the central confirmation gate,
never carry secrets, and unknown keys are rejected so a stale client
cannot silently smuggle in new behaviour. Persisted with the secure
atomic writer (owner-only permissions).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from openjarvis.core.config import DEFAULT_CONFIG_DIR
from openjarvis.security.file_utils import secure_write_json

THEMES = ("dark", "light", "system")
ACCENTS = ("violet", "cyan", "amber", "emerald", "rose")
DENSITIES = ("comfortable", "compact")
START_VIEWS = ("chat", "system-control", "settings")

DEFAULT_SETTINGS_PATH = DEFAULT_CONFIG_DIR / "desktop-settings.json"


@dataclass
class DesktopSettings:
    theme: str = "dark"
    accent: str = "violet"
    density: str = "comfortable"
    start_view: str = "chat"
    reduced_motion: bool = False
    # UI prompting only: the gate itself is always on and cannot be
    # turned off by any setting.
    confirm_before_consequential: bool = True

    def validate(self) -> None:
        if self.theme not in THEMES:
            raise ValueError(f"theme must be one of {THEMES}")
        if self.accent not in ACCENTS:
            raise ValueError(f"accent must be one of {ACCENTS}")
        if self.density not in DENSITIES:
            raise ValueError(f"density must be one of {DENSITIES}")
        if self.start_view not in START_VIEWS:
            raise ValueError(f"start_view must be one of {START_VIEWS}")
        if not isinstance(self.reduced_motion, bool):
            raise ValueError("reduced_motion must be a boolean")
        if not isinstance(self.confirm_before_consequential, bool):
            raise ValueError("confirm_before_consequential must be a boolean")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> "DesktopSettings":
        if not isinstance(data, dict):
            raise ValueError("desktop settings must be a JSON object")
        unknown = set(data) - set(
            field.name for field in cls.__dataclass_fields__.values()
        )
        if unknown:
            raise ValueError(f"unknown desktop settings: {sorted(unknown)}")
        settings = cls(**{k: v for k, v in data.items()})
        settings.validate()
        return settings


def load_settings(path: Optional[Path] = None) -> DesktopSettings:
    """Load settings; missing/corrupt file -> defaults (never crash the GUI)."""
    target = Path(path) if path is not None else DEFAULT_SETTINGS_PATH
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        return DesktopSettings()
    try:
        import json

        return DesktopSettings.from_dict(json.loads(raw))
    except (ValueError, TypeError):
        return DesktopSettings()


def save_settings(
    settings: DesktopSettings, path: Optional[Path] = None
) -> DesktopSettings:
    """Validate + atomically persist settings (owner-only permissions)."""
    settings.validate()
    target = Path(path) if path is not None else DEFAULT_SETTINGS_PATH
    secure_write_json(target, settings.to_dict())
    return settings


__all__ = [
    "ACCENTS",
    "DENSITIES",
    "START_VIEWS",
    "THEMES",
    "DesktopSettings",
    "load_settings",
    "save_settings",
]
