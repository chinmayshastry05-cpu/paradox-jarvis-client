"""Tests for Phase 6 desktop REST routes (mounted router, fake backend)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openjarvis.desktop.system_control import TOOL_NAME
from openjarvis.security.confirmation import ConfirmationGate
from openjarvis.server import desktop_routes


class FakeBackend:
    def list_windows(self):
        return [{"id": "w1", "title": "Chat"}]

    def list_apps(self):
        return [{"id": "calculator", "label": "Calculator"}]

    def list_directory(self, path: str):
        return ["a.txt", ".env"]

    def focus_window(self, window_id: str):
        return {"window_id": window_id, "status": "focused"}

    def minimize_window(self, window_id: str):
        return {"window_id": window_id, "status": "minimized"}

    def maximize_window(self, window_id: str):
        return {"window_id": window_id, "status": "maximized"}

    def close_window(self, window_id: str):
        return {"window_id": window_id, "status": "closed"}

    def launch_app(self, app_id: str):
        return {"app_id": app_id, "status": "launched"}

    def open_path(self, path: str):
        return {"path": path, "status": "opened"}


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    app.state.confirmation_gate = ConfirmationGate()
    app.state.desktop_backend = FakeBackend()
    app.state.desktop_allowed_roots = [tmp_path]
    app.state.desktop_settings_path = tmp_path / "desktop-settings.json"
    app.include_router(desktop_routes.router)
    test_client = TestClient(app)
    test_client._tmp = tmp_path  # type: ignore[attr-defined]
    return test_client


def test_list_actions(client) -> None:
    resp = client.get("/v1/desktop/system-control/actions")
    assert resp.status_code == 200
    actions = {a["action"]: a for a in resp.json()["actions"]}
    assert actions["close_window"]["consequential"] is True
    assert actions["list_windows"]["consequential"] is False


def test_execute_read_only_without_approval(client) -> None:
    resp = client.post(
        "/v1/desktop/system-control/execute",
        json={"action": "list_windows", "params": {}},
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["windows"][0]["id"] == "w1"


def test_execute_consequential_without_approval_is_403(client) -> None:
    resp = client.post(
        "/v1/desktop/system-control/execute",
        json={"action": "close_window", "params": {"window_id": "w1"}},
    )
    assert resp.status_code == 403
    assert "approval required" in resp.json()["detail"]


def test_execute_consequential_with_gate_approval(client) -> None:
    gate = client.app.state.confirmation_gate
    gate.grant(TOOL_NAME, {"action": "close_window", "params": {"window_id": "w1"}})
    resp = client.post(
        "/v1/desktop/system-control/execute",
        json={"action": "close_window", "params": {"window_id": "w1"}},
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["status"] == "closed"
    # Single-use: replay is refused.
    resp2 = client.post(
        "/v1/desktop/system-control/execute",
        json={"action": "close_window", "params": {"window_id": "w1"}},
    )
    assert resp2.status_code == 403


def test_execute_unknown_action_is_422(client) -> None:
    resp = client.post(
        "/v1/desktop/system-control/execute",
        json={"action": "shell_exec", "params": {"command": "id"}},
    )
    assert resp.status_code == 422


def test_execute_launch_app_not_allowlisted_is_422(client) -> None:
    resp = client.post(
        "/v1/desktop/system-control/execute",
        json={"action": "launch_app", "params": {"app_id": "evil"}},
    )
    assert resp.status_code == 422


def test_settings_get_put_round_trip(client) -> None:
    get_resp = client.get("/v1/desktop/settings")
    assert get_resp.status_code == 200
    assert get_resp.json()["theme"] == "dark"
    put_resp = client.put(
        "/v1/desktop/settings",
        json={
            "theme": "light",
            "accent": "amber",
            "density": "compact",
            "start_view": "chat",
            "reduced_motion": False,
            "confirm_before_consequential": True,
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["theme"] == "light"
    assert client.get("/v1/desktop/settings").json()["accent"] == "amber"


def test_settings_put_rejects_unknown_key(client) -> None:
    resp = client.put("/v1/desktop/settings", json={"theme": "dark", "backdoor": True})
    assert resp.status_code == 422


def test_settings_put_rejects_bad_theme(client) -> None:
    resp = client.put("/v1/desktop/settings", json={"theme": "neon"})
    assert resp.status_code == 422
