"""Cross-platform tests for Minions default paths."""

from __future__ import annotations

from unittest.mock import patch

from openjarvis.agents.hybrid.minions import _default_log_dir


def test_default_log_dir_uses_os_temp_dir(tmp_path) -> None:
    with patch(
        "openjarvis.agents.hybrid.minions.tempfile.gettempdir",
        return_value=str(tmp_path),
    ):
        assert _default_log_dir() == str(tmp_path / "minions_logs")


def test_default_log_dir_is_not_hardcoded_tmp() -> None:
    with patch(
        "openjarvis.agents.hybrid.minions.tempfile.gettempdir",
        return_value="/var/tmp/xyz",
    ):
        assert _default_log_dir() == "/var/tmp/xyz/minions_logs"
