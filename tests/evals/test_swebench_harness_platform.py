"""Cross-platform tests for the SWE-bench hard-timeout helper.

Covers: fast commands return normally, a hung child raises
``TimeoutExpired`` after a real tree kill, and the Windows branch wires
the shared ``kill_process_tree`` helper (simulated with a fake Popen,
since the suite runs on Linux).
"""

from __future__ import annotations

import subprocess
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

import openjarvis.evals.scorers.swebench_harness as harness
from openjarvis.evals.scorers.swebench_harness import _run_subprocess_hard_timeout


def test_fast_command_returns(tmp_path) -> None:
    result = _run_subprocess_hard_timeout(
        [sys.executable, "-c", "print('ok')"],
        timeout_s=30,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0
    assert "ok" in result.stdout


def test_hung_child_times_out_and_is_killed(tmp_path) -> None:
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _run_subprocess_hard_timeout(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            timeout_s=1,
            cwd=str(tmp_path),
        )
    # Real tree kill: the drain must return promptly, not hang on the
    # (now dead) child's pipes.
    assert time.monotonic() - start < 30


def test_windows_branch_calls_shared_tree_kill(tmp_path) -> None:
    proc = MagicMock()
    proc.communicate.side_effect = [
        subprocess.TimeoutExpired(cmd="x", timeout=1),
        ("", ""),
    ]
    proc.pid = 4321
    with (
        patch.object(harness.sys, "platform", "win32"),
        patch.object(harness, "kill_process_tree") as kill,
        patch.object(harness.subprocess, "Popen", return_value=proc) as popen,
    ):
        with pytest.raises(subprocess.TimeoutExpired):
            _run_subprocess_hard_timeout(
                ["swebench", "run"], timeout_s=1, cwd=str(tmp_path)
            )
    kill.assert_called_once_with(4321, grace_seconds=10.0)
    spawn_kwargs = popen.call_args.kwargs
    assert "start_new_session" not in spawn_kwargs
    assert "creationflags" in spawn_kwargs


def test_posix_branch_uses_start_new_session(tmp_path) -> None:
    proc = MagicMock()
    proc.communicate.return_value = ("out", "")
    proc.returncode = 0
    with patch.object(harness.subprocess, "Popen", return_value=proc) as popen:
        result = _run_subprocess_hard_timeout(
            ["echo", "hi"], timeout_s=10, cwd=str(tmp_path)
        )
    assert result.returncode == 0
    assert popen.call_args.kwargs.get("start_new_session") is True
