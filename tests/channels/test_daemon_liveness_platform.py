"""Cross-platform tests for daemon liveness helpers.

The old ``os.kill(pid, 0)`` probe killed the probed process on Windows
(``os.kill`` maps any signal to ``TerminateProcess`` there). The daemons
now use ``process_alive`` / ``terminate_process``; these tests pin that
wiring for both the Slack and iMessage daemons.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openjarvis.channels import imessage_daemon, slack_daemon


@pytest.mark.parametrize("module", [slack_daemon, imessage_daemon])
def test_is_running_uses_process_alive(module, tmp_path: Path, monkeypatch) -> None:
    pid_file = tmp_path / "daemon.pid"
    pid_file.write_text("4321")
    monkeypatch.setattr(module, "_PID_FILE", str(pid_file))
    with patch.object(module, "process_alive", return_value=True) as alive:
        assert module.is_running() is True
    alive.assert_called_once_with(4321)
    assert pid_file.exists()


@pytest.mark.parametrize("module", [slack_daemon, imessage_daemon])
def test_is_running_false_removes_stale_pid_file(
    module, tmp_path: Path, monkeypatch
) -> None:
    pid_file = tmp_path / "daemon.pid"
    pid_file.write_text("4321")
    monkeypatch.setattr(module, "_PID_FILE", str(pid_file))
    with patch.object(module, "process_alive", return_value=False):
        assert module.is_running() is False
    assert not pid_file.exists()


@pytest.mark.parametrize("module", [slack_daemon, imessage_daemon])
def test_stop_daemon_uses_terminate_process(
    module, tmp_path: Path, monkeypatch
) -> None:
    pid_file = tmp_path / "daemon.pid"
    pid_file.write_text("4321")
    monkeypatch.setattr(module, "_PID_FILE", str(pid_file))
    with patch.object(module, "terminate_process") as term:
        assert module.stop_daemon() is True
    term.assert_called_once_with(4321)
    assert not pid_file.exists()


@pytest.mark.parametrize("module", [slack_daemon, imessage_daemon])
def test_is_running_missing_pid_file(module, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "_PID_FILE", str(tmp_path / "nope.pid"))
    assert module.is_running() is False


def test_slack_spawn_uses_detached_spawn_kwargs(monkeypatch) -> None:
    # start_slack_daemon imports subprocess + detached_spawn_kwargs
    # locally, so patch the sources, not module attributes.
    fake_proc = MagicMock()
    fake_proc.pid = 777
    with (
        patch("subprocess.Popen", return_value=fake_proc) as popen,
        patch(
            "openjarvis.core.platform.detached_spawn_kwargs",
            return_value={"start_new_session": True},
        ) as spawn_kwargs,
    ):
        assert slack_daemon.start_slack_daemon("bot", "app", "model") == 777
    spawn_kwargs.assert_called_once_with()
    assert popen.call_args.kwargs.get("start_new_session") is True
