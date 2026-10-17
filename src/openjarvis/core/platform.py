"""Cross-platform helpers: OS detection, detached spawn, shell, tree kill.

Single home for the ``sys.platform`` / ``os.name`` branches that used to be
scattered (and inconsistent) across the daemon, GUI, sandbox, eval, and
agent code. Everything here is stdlib-only so importing it is cheap.

Security posture is unchanged: :func:`kill_process_tree` never weakens
the kill — POSIX still escalates SIGTERM → SIGKILL on the whole process
group, Windows still uses ``taskkill /T`` then ``taskkill /F /T`` (whole
tree). Callers must only pass PIDs of children they spawned with
:func:`detached_spawn_kwargs` (own session / process group), so the
group kill cannot hit an unrelated process group.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from openjarvis.core.utils import process_alive, terminate_process

__all__ = [
    "bash_argv",
    "detached_spawn_kwargs",
    "is_linux",
    "is_macos",
    "is_posix",
    "is_windows",
    "is_wsl",
    "kill_process_tree",
    "platform_id",
]


def is_windows() -> bool:
    """True on native Windows (``sys.platform == "win32"``)."""
    return sys.platform == "win32"


def is_macos() -> bool:
    """True on macOS (``sys.platform == "darwin"``)."""
    return sys.platform == "darwin"


def is_linux() -> bool:
    """True on a Linux kernel — including WSL2 (WSL2 *is* Linux)."""
    return sys.platform.startswith("linux")


def is_posix() -> bool:
    """True wherever ``os.name == "posix"`` (Linux, macOS, WSL2)."""
    return os.name == "posix"


def _proc_version_contains_wsl() -> bool:
    """True iff ``/proc/version`` mentions a Microsoft/WSL kernel."""
    try:
        text = Path("/proc/version").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    lowered = text.lower()
    return "microsoft" in lowered or "wsl" in lowered


def is_wsl() -> bool:
    """True inside WSL (1 or 2).

    WSL sets ``WSL_DISTRO_NAME`` / ``WSL_INTEROP``; the kernel version
    string also contains ``microsoft`` / ``wsl``. Either signal counts,
    so a scrubbed environment still detects via the kernel string.
    """
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    return _proc_version_contains_wsl()


def platform_id() -> str:
    """One of ``"windows"`` / ``"darwin"`` / ``"wsl"`` / ``"linux"`` / ``"unknown"``.

    ``"darwin"`` (not ``"macos"``) matches the analytics event vocabulary
    in ``openjarvis.analytics.events``. WSL2 reports as ``"wsl"``, not
    ``"linux"``, so callers that need Linux-kernel behaviour should use
    :func:`is_linux` / :func:`is_posix` instead of comparing this.
    """
    if is_windows():
        return "windows"
    if is_macos():
        return "darwin"
    if is_linux():
        return "wsl" if is_wsl() else "linux"
    return "unknown"


def detached_spawn_kwargs() -> Dict[str, Any]:
    """``subprocess.Popen`` kwargs that detach a child on every platform.

    POSIX: ``start_new_session=True`` (own session / process group, so
    :func:`kill_process_tree` can signal the whole tree via ``killpg``).
    Windows: ``CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`` — CPython's
    Windows ``_execute_child`` ignores ``start_new_session``, so without
    the creation flags the child would share the parent's console and a
    console close / logoff would kill it.
    """
    if is_windows():
        # CREATE_* only exist on Windows; getattr keeps this branch
        # importable/testable on POSIX (where it never runs).
        return {
            "creationflags": (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        }
    return {"start_new_session": True}


def bash_argv(command: str) -> List[str]:
    """Wrap *command* in a ``bash`` argv (``bash -lc <command>``).

    POSIX: ``bash`` when on PATH, else ``sh -c`` (no ``-l``: ``sh`` login
    semantics vary). Windows: ``bash`` from Git for Windows when on PATH;
    otherwise raise — silently running bash-oriented commands (SWE-bench
    agent loops, harness scripts) under PowerShell/cmd would misinterpret
    them, so fail loudly with the fix instead of running the wrong shell.
    """
    bash = shutil.which("bash")
    if bash is not None:
        return [bash, "-lc", command]
    if is_windows():
        raise RuntimeError(
            "bash is required but was not found on PATH. Install Git for "
            "Windows (which ships Git Bash) or run under WSL2, then retry."
        )
    sh = shutil.which("sh") or "sh"
    return [sh, "-c", command]


def kill_process_tree(pid: int | None, *, grace_seconds: float = 5.0) -> None:
    """Kill *pid* and its descendants; SIGTERM-then-SIGKILL on POSIX.

    POSIX assumes *pid* is a process-group leader (spawned with
    :func:`detached_spawn_kwargs` / ``start_new_session=True``), so
    ``killpg`` reaches backgrounded grandchildren that hold pipes open.
    Windows has no process groups / SIGKILL — ``terminate_process``
    (``taskkill /T`` then ``taskkill /F /T``) kills the whole tree.
    Best-effort: a dead or unkillable PID is silently a no-op, matching
    the previous ``killpg`` call sites.
    """
    if not pid or pid <= 0:
        return
    if is_windows():
        terminate_process(pid, grace_seconds=grace_seconds)
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return
    deadline = time.monotonic() + max(0.0, grace_seconds)
    while True:
        # Check liveness at least once even when grace is 0, so a
        # process already dead from SIGTERM never gets a pointless SIGKILL.
        if not process_alive(pid):
            return
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    sigkill = getattr(signal, "SIGKILL", None)
    if sigkill is not None:
        try:
            os.killpg(pid, sigkill)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    deadline = time.monotonic() + max(0.0, grace_seconds)
    while True:
        if not process_alive(pid):
            return
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
