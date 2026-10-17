"""Tests for Phase 6 desktop settings (validation + persistence)."""

from __future__ import annotations

import pytest

from openjarvis.desktop.settings import (
    DesktopSettings,
    load_settings,
    save_settings,
)


def test_defaults_are_valid() -> None:
    settings = DesktopSettings()
    assert settings.theme == "dark"
    assert settings.confirm_before_consequential is True
    settings.validate()


def test_from_dict_rejects_unknown_keys() -> None:
    with pytest.raises(ValueError, match="unknown"):
        DesktopSettings.from_dict({"theme": "dark", "api_key": "x"})


def test_from_dict_rejects_bad_values() -> None:
    for bad in (
        {"theme": "neon"},
        {"accent": "rainbow"},
        {"density": "huge"},
        {"start_view": "terminal"},
        {"reduced_motion": "yes"},
    ):
        with pytest.raises(ValueError):
            DesktopSettings.from_dict(bad)


def test_from_dict_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        DesktopSettings.from_dict(["dark"])


def test_round_trip_persists_and_restores(tmp_path) -> None:
    path = tmp_path / "desktop-settings.json"
    saved = save_settings(
        DesktopSettings(theme="light", accent="amber", density="compact"),
        path,
    )
    assert saved.theme == "light"
    loaded = load_settings(path)
    assert (loaded.theme, loaded.accent, loaded.density) == (
        "light",
        "amber",
        "compact",
    )


def test_persisted_file_is_owner_only(tmp_path) -> None:
    import os
    import stat

    path = tmp_path / "desktop-settings.json"
    save_settings(DesktopSettings(), path)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600


def test_missing_file_returns_defaults(tmp_path) -> None:
    assert load_settings(tmp_path / "nope.json").theme == "dark"


def test_corrupt_file_returns_defaults(tmp_path) -> None:
    path = tmp_path / "desktop-settings.json"
    path.write_text("{not json")
    assert load_settings(path).theme == "dark"
