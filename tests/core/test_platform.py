"""Tests for cross-platform helpers in ``openjarvis.core.platform``.

Platform differences are simulated by patching ``sys.platform`` /
``os.name`` / env vars, matching the existing convention in
``tests/cli/test_daemon_cmd.py`` (patch ``<module>.sys.platform``).
Nothing here runs on a real Windows/macOS host.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

import openjarvis.core.platform as plat
from openjarvis.core.platform import (
    bash_argv,
    detached_spawn_kwargs,
    is_linux,
    is_macos,
    is_posix,
    is_windows,
    is_wsl,
    kill_process_tree,
    platform_id,
)


def _set_platform(monkeypatch, *, platform: str, os_name: str) -> None:
    monkeypatch.setattr(plat.sys, "platform", platform)
    monkeypatch.setattr(plat.os, "name", os_name)


class TestOsDetection:
    def test_windows(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="win32", os_name="nt")
        assert is_windows() is True
        assert is_macos() is False
        assert is_linux() is False
        assert is_posix() is False
        assert platform_id() == "windows"

    def test_macos(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="darwin", os_name="posix")
        assert is_windows() is False
        assert is_macos() is True
        assert is_linux() is False
        assert is_posix() is True
        assert platform_id() == "darwin"

    def test_linux(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.delenv("WSL_INTEROP", raising=False)
        with patch.object(plat, "_proc_version_contains_wsl", return_value=False):
            assert is_linux() is True
            assert is_wsl() is False
            assert platform_id() == "linux"

    def test_unknown_platform(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="freebsd13", os_name="posix")
        assert platform_id() == "unknown"


class TestIsWsl:
    def test_wsl_distro_env(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        assert is_wsl() is True
        assert platform_id() == "wsl"

    def test_wsl_interop_env(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.setenv("WSL_INTEROP", "/run/WSL/123_interop")
        assert is_wsl() is True

    def test_proc_version_kernel_string(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.delenv("WSL_INTEROP", raising=False)
        with patch.object(plat, "_proc_version_contains_wsl", return_value=True):
            assert is_wsl() is True

    def test_no_wsl_signal(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.delenv("WSL_INTEROP", raising=False)
        with patch.object(plat, "_proc_version_contains_wsl", return_value=False):
            assert is_wsl() is False


class TestDetachedSpawnKwargs:
    def test_windows_uses_creationflags(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="win32", os_name="nt")
        kwargs = detached_spawn_kwargs()
        assert kwargs["creationflags"] == (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        assert "start_new_session" not in kwargs

    def test_posix_uses_start_new_session(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        assert detached_spawn_kwargs() == {"start_new_session": True}

    def test_macos_uses_start_new_session(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="darwin", os_name="posix")
        assert detached_spawn_kwargs() == {"start_new_session": True}


class TestBashArgv:
    def test_posix_prefers_bash(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        with patch.object(plat.shutil, "which", return_value="/usr/bin/bash"):
            assert bash_argv("echo hi") == ["/usr/bin/bash", "-lc", "echo hi"]

    def test_posix_falls_back_to_sh(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")

        def _which(name: str):
            return "/bin/sh" if name == "sh" else None

        with patch.object(plat.shutil, "which", side_effect=_which):
            assert bash_argv("echo hi") == ["/bin/sh", "-c", "echo hi"]

    def test_windows_uses_git_bash_when_present(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="win32", os_name="nt")
        with patch.object(
            plat.shutil, "which", return_value=r"C:\Program Files\Git\bin\bash.exe"
        ):
            assert bash_argv("echo hi") == [
                r"C:\Program Files\Git\bin\bash.exe",
                "-lc",
                "echo hi",
            ]

    def test_windows_without_bash_raises_instead_of_wrong_shell(
        self, monkeypatch
    ) -> None:
        _set_platform(monkeypatch, platform="win32", os_name="nt")
        with patch.object(plat.shutil, "which", return_value=None):
            with pytest.raises(RuntimeError, match="bash is required"):
                bash_argv("echo hi")


class TestKillProcessTree:
    def test_noop_on_bad_pid(self, monkeypatch) -> None:
        with (
            patch.object(plat, "terminate_process") as term,
            patch.object(plat.os, "killpg") as killpg,
        ):
            kill_process_tree(None)
            kill_process_tree(0)
            kill_process_tree(-5)
        term.assert_not_called()
        killpg.assert_not_called()

    def test_windows_delegates_to_taskkill_helper(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="win32", os_name="nt")
        with patch.object(plat, "terminate_process") as term:
            kill_process_tree(4321, grace_seconds=2.5)
        term.assert_called_once_with(4321, grace_seconds=2.5)

    def test_posix_sigterm_suffices_no_sigkill(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        with (
            patch.object(plat.os, "killpg") as killpg,
            patch.object(plat, "process_alive", return_value=False),
        ):
            kill_process_tree(1234, grace_seconds=0)
        import signal

        killpg.assert_called_once_with(1234, signal.SIGTERM)

    def test_posix_escalates_to_sigkill_when_term_ignored(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        import signal

        with (
            patch.object(plat.os, "killpg") as killpg,
            patch.object(plat, "process_alive", return_value=True),
        ):
            kill_process_tree(1234, grace_seconds=0)
        assert killpg.call_args_list == [
            ((1234, signal.SIGTERM),),
            ((1234, signal.SIGKILL),),
        ]

    def test_posix_dead_pid_is_noop(self, monkeypatch) -> None:
        _set_platform(monkeypatch, platform="linux", os_name="posix")
        with (
            patch.object(plat.os, "killpg", side_effect=ProcessLookupError) as killpg,
            patch.object(plat, "process_alive") as alive,
        ):
            kill_process_tree(999999, grace_seconds=0)
        killpg.assert_called_once()
        alive.assert_not_called()


class TestKillProcessTreeRealProcess:
    def test_real_sleep_is_killed(self) -> None:
        import sys

        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            **detached_spawn_kwargs(),
        )
        try:
            kill_process_tree(proc.pid, grace_seconds=2.0)
            proc.wait(timeout=10)
            # SIGTERM (15) to the process group.
            assert proc.returncode == -15
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

    def test_real_process_group_grandchild_does_not_wedge_kill(self) -> None:
        import sys

        # Child backgrounds a grandchild; group kill must reap the leader
        # promptly instead of wedging on the surviving grandchild.
        proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import subprocess, sys, time; "
                "subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(60)']); "
                "time.sleep(60)",
            ],
            **detached_spawn_kwargs(),
        )
        try:
            kill_process_tree(proc.pid, grace_seconds=2.0)
            proc.wait(timeout=10)
            assert proc.returncode is not None
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
