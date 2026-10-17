"""Cross-platform tests for the hybrid runner cell lock.

POSIX keeps the original ``flock`` behaviour; the Windows branch uses an
``msvcrt`` byte-range lock (simulated here with a fake ``msvcrt`` module
because the suite runs on Linux).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import openjarvis.agents.hybrid.runner as runner_mod
from openjarvis.agents.hybrid.runner import _cell_lock


class _FakeMsvcrt:
    """Region-lock model: one global lock, like real ``msvcrt`` byte-range
    locking on a single file (a second handle contends with the first)."""

    LK_NBLCK = 1
    LK_UNLCK = 2

    def __init__(self) -> None:
        self.held = False
        self.calls: list[tuple[int, int, int]] = []

    def locking(self, fd: int, mode: int, nbytes: int) -> None:
        self.calls.append((fd, mode, nbytes))
        if mode == self.LK_NBLCK:
            if self.held:
                raise OSError(33, "Lock violation")
            self.held = True
        elif mode == self.LK_UNLCK:
            self.held = False


@pytest.fixture()
def fake_msvcrt(monkeypatch):
    fake = _FakeMsvcrt()
    module = types.ModuleType("msvcrt")
    module.LK_NBLCK = _FakeMsvcrt.LK_NBLCK
    module.LK_UNLCK = _FakeMsvcrt.LK_UNLCK
    module.locking = fake.locking
    monkeypatch.setitem(sys.modules, "msvcrt", module)
    monkeypatch.setattr(runner_mod.sys, "platform", "win32")
    return fake


def test_posix_lock_contention_refuses_second_runner(tmp_path: Path) -> None:
    with _cell_lock(tmp_path, "cell-a"):
        with pytest.raises(SystemExit, match="another runner is already"):
            with _cell_lock(tmp_path, "cell-a"):
                pass
    # Released: re-acquirable.
    with _cell_lock(tmp_path, "cell-a"):
        pass


def test_windows_lock_acquire_and_release(
    tmp_path: Path, fake_msvcrt: _FakeMsvcrt
) -> None:
    with _cell_lock(tmp_path, "cell-w"):
        assert fake_msvcrt.calls and fake_msvcrt.calls[0][1] == _FakeMsvcrt.LK_NBLCK
    assert fake_msvcrt.calls[-1][1] == _FakeMsvcrt.LK_UNLCK
    assert not (tmp_path / ".lock").exists()


def test_windows_lock_contention_refuses_second_runner(
    tmp_path: Path, fake_msvcrt: _FakeMsvcrt
) -> None:
    with _cell_lock(tmp_path, "cell-w"):
        with pytest.raises(SystemExit, match="another runner is already"):
            with _cell_lock(tmp_path, "cell-w"):
                pass
