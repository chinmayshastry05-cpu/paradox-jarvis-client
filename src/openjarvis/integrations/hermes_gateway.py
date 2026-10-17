"""Side-by-side process supervision (Phase 2).

Hermes Agent runs as a *separate* process (e.g. ``hermes gateway``) — it
is never imported into Jarvis. This module only supervises that process
lifecycle: start, liveness, stop (terminate → wait → kill fallback).
It assumes NO protocol with the child: no stdin commands, no invented
RPC/HTTP endpoints. Output goes to DEVNULL so an unbounded child cannot
block on a full pipe; operators read the child's own logs.

Security: ``shell=False`` always; child env is scrubbed (see
:func:`openjarvis.integrations.external_plugin.scrubbed_env`).
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional, Sequence

from openjarvis.integrations.external_plugin import scrubbed_env

logger = logging.getLogger(__name__)


class SideBySideProcess:
    """Supervise one external long-running process."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        name: str = "side-by-side",
        stop_timeout_seconds: float = 5.0,
    ) -> None:
        if not command:
            raise ValueError("command must be a non-empty argv list")
        self._command = [str(c) for c in command]
        self._name = name
        self._stop_timeout = stop_timeout_seconds
        self._proc: Optional[subprocess.Popen[bytes]] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self._proc is not None else None

    def start(self) -> int:
        """Start the child. Raises RuntimeError if already running."""
        if self.is_alive():
            raise RuntimeError(f"{self._name} is already running (pid {self.pid})")
        self._proc = subprocess.Popen(
            self._command,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=scrubbed_env(),
        )
        logger.info("Started side-by-side process %s (pid %s)", self._name, self.pid)
        return self._proc.pid

    def is_alive(self) -> bool:
        """True iff the child is currently running."""
        return self._proc is not None and self._proc.poll() is None

    def stop(self) -> bool:
        """Stop the child: SIGTERM, wait, then SIGKILL fallback.

        Returns True if the child is no longer running afterwards.
        Safe to call when not running.
        """
        proc = self._proc
        if proc is None:
            return True
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=self._stop_timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=self._stop_timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Stop of %s failed: %s", self._name, exc)
        finally:
            self._proc = None
        return True

    def __enter__(self) -> "SideBySideProcess":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()


class HermesGateway(SideBySideProcess):
    """Supervise a Hermes Agent gateway as a side-by-side process.

    Default argv is Hermes' documented ``hermes gateway`` entrypoint.
    The gateway is NOT configured or verified here: the operator owns
    the Hermes install, its config, and its credentials. Jarvis only
    manages the process lifecycle.
    """

    def __init__(
        self,
        command: Sequence[str] = ("hermes", "gateway"),
        *,
        stop_timeout_seconds: float = 5.0,
    ) -> None:
        super().__init__(
            command, name="hermes-gateway", stop_timeout_seconds=stop_timeout_seconds
        )


__all__ = ["HermesGateway", "SideBySideProcess"]
