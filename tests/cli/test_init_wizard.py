"""Tests for the first-run setup wizard extras in ``jarvis init``.

Covers: token whitespace stripping, Telegram/Kokoro config patching
(never writing secrets), desktop permission checks, the Kokoro
on/off switch, and NIM offered as a free engine choice.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from openjarvis.cli import cli
from openjarvis.cli._desktop_permissions import check_desktop_permissions
from openjarvis.cli.init_cmd import (
    _SUPPORTED_ENGINES,
    _patch_config_toml,
    strip_token,
)
from openjarvis.speech._tts_discovery import get_tts_backend


class TestStripToken:
    def test_strips_leading_trailing_and_interior_whitespace(self) -> None:
        assert strip_token("  123456:ABC-DEF  ") == "123456:ABC-DEF"
        # The stray-space copy that made a valid token fail auth.
        assert strip_token("123456:AB C-DEF") == "123456:ABC-DEF"

    def test_leaves_valid_token_unchanged(self) -> None:
        assert strip_token("123456:ABC-DEF1234ghIkl") == "123456:ABC-DEF1234ghIkl"


class TestPatchConfigToml:
    def test_writes_chat_id_and_kokoro_flag_never_token(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".openjarvis"
        config_path = config_dir / "config.toml"
        config_dir.mkdir()
        config_path.write_text('[engine]\ndefault = "ollama"\n', encoding="utf-8")
        with (
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_DIR", config_dir),
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_PATH", config_path),
        ):
            _patch_config_toml(telegram_chat_id="123456789", kokoro_enabled=False)
        content = config_path.read_text(encoding="utf-8")
        assert 'allowed_chat_ids = "123456789"' in content
        assert "tts_enabled = false" in content
        assert '[engine]\ndefault = "ollama"' in content
        # The token must never land in the config file.
        assert "123456:ABC" not in content

    def test_patch_is_a_noop_when_nothing_given(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".openjarvis"
        config_path = config_dir / "config.toml"
        config_dir.mkdir()
        original = '[engine]\ndefault = "ollama"\n'
        config_path.write_text(original, encoding="utf-8")
        with (
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_DIR", config_dir),
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_PATH", config_path),
        ):
            _patch_config_toml()
        assert config_path.read_text(encoding="utf-8") == original


class TestDesktopPermissions:
    def test_x11_session_with_xdotool_reports_ok(self) -> None:
        def which(name: str) -> str | None:
            return "/usr/bin/xdotool" if name == "xdotool" else None

        checks = check_desktop_permissions(env={"DISPLAY": ":0"}, which=which)
        by_name = {c.name: c for c in checks}
        assert by_name["display"].ok is True
        assert by_name["X11 automation"].ok is True

    def test_headless_session_warns_on_display(self) -> None:
        checks = check_desktop_permissions(env={}, which=lambda name: None)
        by_name = {c.name: c for c in checks}
        assert by_name["display"].ok is False
        assert by_name["screenshot"].ok is False

    def test_wayland_checks_wayland_tools(self) -> None:
        def which(name: str) -> str | None:
            return "/usr/bin/wtype" if name == "wtype" else None

        checks = check_desktop_permissions(
            env={"WAYLAND_DISPLAY": "wayland-1"}, which=which
        )
        by_name = {c.name: c for c in checks}
        assert by_name["display"].ok is True
        assert by_name["wayland automation"].ok is True


class TestKokoroSwitch:
    def test_disabled_tts_returns_no_backend(self) -> None:
        assert get_tts_backend("kokoro", enabled=False) is None

    def test_enabled_tts_still_probes(self) -> None:
        # No backend is healthy in a bare test env, so this is None too —
        # but through probing, not through the off switch.
        assert get_tts_backend("definitely-not-a-backend", enabled=True) is None


class TestWizardEngines:
    def test_nim_offered_after_ollama(self) -> None:
        assert _SUPPORTED_ENGINES[0] == "ollama"
        assert _SUPPORTED_ENGINES[1] == "nim"


class TestInitWizardEndToEnd:
    def test_init_with_skipped_extras_writes_kokoro_default(
        self, tmp_path: Path
    ) -> None:
        """Scripted Enter-through: Telegram skipped, Kokoro default on."""
        config_dir = tmp_path / ".openjarvis"
        config_path = config_dir / "config.toml"
        with (
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_DIR", config_dir),
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_PATH", config_path),
            mock.patch("openjarvis.cli.init_cmd.PrivacyScanner"),
        ):
            # Telegram token (Enter = skip), Kokoro confirm (Enter = on).
            result = CliRunner().invoke(
                cli,
                ["init", "--engine", "ollama", "--no-download", "--no-scan"],
                input="\n\n",
            )
        assert result.exception is None, result.output
        assert result.exit_code == 0, result.output
        content = config_path.read_text(encoding="utf-8")
        assert "tts_enabled = true" in content
        assert "allowed_chat_ids" not in content
        assert "Desktop permissions check:" in result.output

    def test_init_skips_when_config_exists(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".openjarvis"
        config_path = config_dir / "config.toml"
        config_dir.mkdir()
        config_path.write_text('[engine]\ndefault = "ollama"\n', encoding="utf-8")
        with (
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_DIR", config_dir),
            mock.patch("openjarvis.cli.init_cmd.DEFAULT_CONFIG_PATH", config_path),
            mock.patch("openjarvis.cli.init_cmd.PrivacyScanner"),
        ):
            result = CliRunner().invoke(cli, ["init", "--engine", "ollama"])
        assert result.exit_code == 1
        assert "already exists" in result.output
        assert config_path.read_text(encoding="utf-8") == (
            '[engine]\ndefault = "ollama"\n'
        )
