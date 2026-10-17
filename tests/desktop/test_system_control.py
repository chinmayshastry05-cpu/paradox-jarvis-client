"""Tests for Phase 6 desktop system control (mocked backend only)."""

from __future__ import annotations

import pytest

from openjarvis.desktop.system_control import (
    TOOL_NAME,
    DesktopUnavailableError,
    NoOpDesktopBackend,
    SystemControlError,
    SystemControlService,
    describe_actions,
)
from openjarvis.security.confirmation import ConfirmationGate


class FakeBackend:
    """In-memory desktop backend: records calls, returns canned data."""

    def __init__(self, root: str) -> None:
        self.root = root
        self.calls: list[tuple[str, tuple]] = []

    def list_windows(self):
        self.calls.append(("list_windows", ()))
        return [{"id": "w1", "title": "Chat — Jarvis", "focused": True}]

    def list_apps(self):
        self.calls.append(("list_apps", ()))
        return [{"id": "calculator", "label": "Calculator"}]

    def list_directory(self, path: str):
        self.calls.append(("list_directory", (path,)))
        return ["notes.txt", ".env", "report.pdf"]

    def focus_window(self, window_id: str):
        self.calls.append(("focus_window", (window_id,)))
        return {"window_id": window_id, "status": "focused"}

    def minimize_window(self, window_id: str):
        self.calls.append(("minimize_window", (window_id,)))
        return {"window_id": window_id, "status": "minimized"}

    def maximize_window(self, window_id: str):
        self.calls.append(("maximize_window", (window_id,)))
        return {"window_id": window_id, "status": "maximized"}

    def close_window(self, window_id: str):
        self.calls.append(("close_window", (window_id,)))
        return {"window_id": window_id, "status": "closed"}

    def launch_app(self, app_id: str):
        self.calls.append(("launch_app", (app_id,)))
        return {"app_id": app_id, "status": "launched"}

    def open_path(self, path: str):
        self.calls.append(("open_path", (path,)))
        return {"path": path, "status": "opened"}


@pytest.fixture
def service(tmp_path):
    backend = FakeBackend(str(tmp_path))
    return SystemControlService(
        backend=backend, gate=ConfirmationGate(), allowed_roots=[tmp_path]
    )


def _approve(service: SystemControlService, action: str, params: dict) -> None:
    service.gate.grant(TOOL_NAME, {"action": action, "params": params})


def test_describe_actions_marks_consequential() -> None:
    actions = {a["action"]: a for a in describe_actions()}
    assert actions["list_windows"]["consequential"] is False
    assert actions["list_directory"]["consequential"] is False
    assert actions["close_window"]["consequential"] is True
    assert actions["launch_app"]["consequential"] is True
    assert actions["open_path"]["consequential"] is True
    # No shell / arbitrary-command action may ever appear.
    assert "shell_exec" not in actions and "run_command" not in actions


def test_unknown_action_rejected(service) -> None:
    with pytest.raises(SystemControlError, match="unknown"):
        service.execute("shell_exec", {"command": "id"})


def test_unknown_params_rejected(service) -> None:
    with pytest.raises(SystemControlError, match="unknown params"):
        service.execute("list_windows", {"extra": 1})


def test_read_only_actions_need_no_approval(service) -> None:
    assert service.execute("list_windows", {})["windows"][0]["id"] == "w1"
    assert service.execute("list_apps", {})["apps"][0]["id"] == "calculator"


def test_list_directory_filters_sensitive_files(service, tmp_path) -> None:
    result = service.execute("list_directory", {"path": str(tmp_path)})
    assert result["entries"] == ["notes.txt", "report.pdf"]
    assert ".env" not in result["entries"]


def test_list_directory_outside_roots_rejected(service, tmp_path) -> None:
    with pytest.raises(SystemControlError, match="outside the allowed roots"):
        service.execute("list_directory", {"path": "/etc"})


def test_consequential_action_requires_approval(service) -> None:
    with pytest.raises(SystemControlError, match="approval required"):
        service.execute("focus_window", {"window_id": "w1"})
    assert service.backend.calls == []  # nothing dispatched before approval


def test_approval_bound_to_exact_params(service) -> None:
    _approve(service, "focus_window", {"window_id": "w1"})
    with pytest.raises(SystemControlError, match="approval required"):
        service.execute("focus_window", {"window_id": "w2"})  # tampered args
    assert service.execute("focus_window", {"window_id": "w1"})["status"] == "focused"


def test_approval_is_single_use(service) -> None:
    _approve(service, "minimize_window", {"window_id": "w1"})
    assert (
        service.execute("minimize_window", {"window_id": "w1"})["status"] == "minimized"
    )
    with pytest.raises(SystemControlError, match="approval required"):
        service.execute("minimize_window", {"window_id": "w1"})  # replay


def test_launch_app_allowlist(service) -> None:
    with pytest.raises(SystemControlError, match="not allowlisted"):
        service.execute("launch_app", {"app_id": "rm -rf /"})
    _approve(service, "launch_app", {"app_id": "calculator"})
    assert (
        service.execute("launch_app", {"app_id": "calculator"})["status"] == "launched"
    )


def test_open_path_rejects_sensitive_and_outside(service, tmp_path) -> None:
    secret = tmp_path / ".env"
    secret.write_text("KEY=1")
    with pytest.raises(SystemControlError, match="sensitive-file"):
        service.execute("open_path", {"path": str(secret)})
    with pytest.raises(SystemControlError, match="outside the allowed roots"):
        service.execute("open_path", {"path": "/etc/passwd"})


def test_open_path_requires_approval_then_dispatches(service, tmp_path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("hi")
    params = {"path": str(target)}
    with pytest.raises(SystemControlError, match="approval required"):
        service.execute("open_path", params)
    _approve(service, "open_path", params)
    assert service.execute("open_path", params)["status"] == "opened"


def test_window_id_validation(service) -> None:
    for bad in ("", "   ", "a\nb", "x" * 200):
        with pytest.raises(SystemControlError):
            service.execute("close_window", {"window_id": bad})


def test_noop_backend_fails_closed() -> None:
    svc = SystemControlService(backend=NoOpDesktopBackend(), gate=ConfirmationGate())
    with pytest.raises(DesktopUnavailableError):
        svc.execute("list_windows", {})


def test_backend_output_is_redacted(service) -> None:
    class LeakyBackend(FakeBackend):
        def list_windows(self):
            return [{"id": "w1", "title": "token=sk-secret-1234567890abcdef"}]

    svc = SystemControlService(
        backend=LeakyBackend(""), gate=ConfirmationGate(), allowed_roots=[]
    )
    title = svc.execute("list_windows", {})["windows"][0]["title"]
    assert "sk-secret-1234567890abcdef" not in title
