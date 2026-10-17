"""Tests for the external-plugin runner (mocked subprocess)."""

import sys

from openjarvis.integrations.external_plugin import (
    PLUGIN_SPECS,
    run_plugin,
    scrubbed_env,
)

FAKE_CMD = [sys.executable, "-c", "print('hello-plugin')"]
YES = lambda prompt: True  # noqa: E731
NO = lambda prompt: False  # noqa: E731


def test_unknown_plugin_refused():
    result = run_plugin("nope", enabled=True, confirm=YES)
    assert not result.ok


def test_disabled_by_default():
    result = run_plugin("cua-driver", command=FAKE_CMD, confirm=YES)
    assert not result.ok
    assert "disabled" in result.error


def test_requires_confirmer():
    result = run_plugin("cua-driver", command=FAKE_CMD, enabled=True)
    assert not result.ok
    assert "confirmer" in result.error


def test_operator_decline_refused():
    result = run_plugin("cua-driver", command=FAKE_CMD, enabled=True, confirm=NO)
    assert not result.ok
    assert "declined" in result.error


def test_happy_path_runs_without_shell():
    result = run_plugin("cua-driver", command=FAKE_CMD, enabled=True, confirm=YES)
    assert result.ok
    assert result.returncode == 0
    assert result.stdout.strip() == "hello-plugin"


def test_geo_sleuth_needs_privacy_ack():
    result = run_plugin("geo-sleuth", command=FAKE_CMD, enabled=True, confirm=YES)
    assert not result.ok
    assert "privacy" in result.error
    result = run_plugin(
        "geo-sleuth", command=FAKE_CMD, enabled=True, confirm=YES, privacy_ack=True
    )
    assert result.ok


def test_long_running_plugin_redirected():
    result = run_plugin("hermes-gateway", enabled=True, confirm=YES)
    assert not result.ok
    assert "long-running" in result.error


def test_missing_command_refused():
    result = run_plugin("cua-driver", enabled=True, confirm=YES)
    assert not result.ok
    assert "no command" in result.error


def test_failing_command_reported():
    result = run_plugin(
        "cua-driver",
        command=[sys.executable, "-c", "import sys; sys.exit(3)"],
        enabled=True,
        confirm=YES,
    )
    assert not result.ok
    assert result.returncode == 3


def test_timeout_reported():
    result = run_plugin(
        "cua-driver",
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        enabled=True,
        confirm=YES,
        timeout_seconds=0.2,
    )
    assert not result.ok
    assert "timed out" in result.error


def test_output_is_redacted():
    # A GitHub-style token in plugin output must not come back raw.
    result = run_plugin(
        "cua-driver",
        command=[sys.executable, "-c", "print('ghp_' + 'A' * 36)"],
        enabled=True,
        confirm=YES,
    )
    assert result.ok
    assert "ghp_" + "A" * 36 not in result.stdout


def test_env_scrubbed(monkeypatch):
    monkeypatch.setenv("MY_SECRET_TOKEN", "should-not-leak")
    env = scrubbed_env()
    assert "MY_SECRET_TOKEN" not in env
    assert "PATH" in env or "HOME" in env


def test_specs_cover_matrix_plugins():
    assert {
        "hermes-gateway",
        "cua-driver",
        "claude-code-router",
        "oh-my-hermes",
        "geo-sleuth",
        "hermes-gadget-sdk",
    } <= set(PLUGIN_SPECS)
