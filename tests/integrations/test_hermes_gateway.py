"""Tests for side-by-side process supervision (mocked child process)."""

import sys

import pytest

from openjarvis.integrations.hermes_gateway import HermesGateway, SideBySideProcess

SLEEPER = [sys.executable, "-c", "import time; time.sleep(30)"]


def test_start_stop_lifecycle():
    proc = SideBySideProcess(SLEEPER, name="test-sleeper")
    assert not proc.is_alive()
    pid = proc.start()
    assert pid and proc.is_alive()
    assert proc.pid == pid
    assert proc.stop() is True
    assert not proc.is_alive()


def test_stop_is_idempotent():
    proc = SideBySideProcess(SLEEPER, name="test-sleeper")
    assert proc.stop() is True
    proc.start()
    assert proc.stop() is True
    assert proc.stop() is True


def test_double_start_refused():
    proc = SideBySideProcess(SLEEPER, name="test-sleeper")
    proc.start()
    try:
        with pytest.raises(RuntimeError):
            proc.start()
    finally:
        proc.stop()


def test_context_manager_stops_child():
    with SideBySideProcess(SLEEPER, name="test-sleeper") as proc:
        assert proc.is_alive()
    assert not proc.is_alive()


def test_empty_command_rejected():
    with pytest.raises(ValueError):
        SideBySideProcess([])


def test_hermes_gateway_defaults_to_documented_entrypoint():
    gateway = HermesGateway()
    assert gateway.name == "hermes-gateway"
    # Private attribute check: default argv is `hermes gateway`.
    assert gateway._command == ["hermes", "gateway"]
