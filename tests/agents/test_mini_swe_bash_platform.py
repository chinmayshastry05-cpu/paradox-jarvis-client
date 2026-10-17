"""Cross-platform tests for the mini-SWE bash runner.

Covers: normal execution through the shared ``bash_argv`` helper,
timeout tree-kill, and the loud failure when bash is missing on Windows
(instead of silently running bash commands under the wrong shell).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import openjarvis.agents.hybrid.mini_swe_agent as mini_swe
from openjarvis.agents.hybrid.mini_swe_agent import _run_bash


def test_run_bash_echo(tmp_path: Path) -> None:
    result = _run_bash("echo hello", tmp_path, timeout=30)
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]
    assert result["timed_out"] is False


def test_run_bash_nonzero_exit(tmp_path: Path) -> None:
    result = _run_bash("exit 42", tmp_path, timeout=30)
    assert result["exit_code"] == 42
    assert result["timed_out"] is False


def test_run_bash_timeout_kills_tree(tmp_path: Path) -> None:
    result = _run_bash("sleep 30", tmp_path, timeout=1)
    assert result["timed_out"] is True
    assert result["exit_code"] == -1


def test_run_bash_uses_shared_bash_argv(tmp_path: Path) -> None:
    with patch.object(
        mini_swe, "bash_argv", return_value=["/usr/bin/bash", "-lc", "echo hi"]
    ) as argv:
        result = _run_bash("echo hi", tmp_path, timeout=30)
    argv.assert_called_once_with("echo hi")
    assert result["exit_code"] == 0


def test_run_bash_without_bash_on_windows_raises(tmp_path: Path) -> None:
    with patch.object(
        mini_swe, "bash_argv", side_effect=RuntimeError("bash is required")
    ):
        with pytest.raises(RuntimeError, match="bash is required"):
            _run_bash("echo hi", tmp_path, timeout=30)
