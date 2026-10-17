"""REST endpoints for Phase 6 desktop GUI: system control + settings.

System control (``/v1/desktop/system-control/*``) is the server side of
the desktop GUI's system-control surface. Consequential actions require
a single-use approval granted for the exact (action, params) pair via
``POST /v1/approvals/tool`` (tool ``desktop.system_control``); the
execute path consumes it. Read-only actions (list windows/apps/directory)
need no approval. No shell / arbitrary-command action exists.

Settings (``/v1/desktop/settings``) are appearance-only preferences;
they cannot disable the confirmation gate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from openjarvis.desktop.platform_backend import create_platform_backend
from openjarvis.desktop.settings import (
    DesktopSettings,
    load_settings,
    save_settings,
)
from openjarvis.desktop.system_control import (
    DesktopUnavailableError,
    SystemControlError,
    SystemControlService,
    describe_actions,
)
from openjarvis.security.confirmation import ConfirmationGate

try:
    from fastapi import APIRouter, HTTPException, Request
except ImportError:
    raise ImportError("fastapi is required for desktop routes")

logger = logging.getLogger(__name__)

router = APIRouter()

_gate: Optional[ConfirmationGate] = None


def _get_gate(request: Optional[Request] = None) -> ConfirmationGate:
    global _gate
    if request is not None:
        app_gate = getattr(getattr(request, "app", None), "state", None)
        if app_gate is not None:
            shared = getattr(app_gate, "confirmation_gate", None)
            if isinstance(shared, ConfirmationGate):
                return shared
    if _gate is None:
        _gate = ConfirmationGate()
    return _gate


def _get_backend(request: Optional[Request] = None) -> Any:
    if request is not None:
        app_state = getattr(getattr(request, "app", None), "state", None)
        if app_state is not None:
            backend = getattr(app_state, "desktop_backend", None)
            if backend is not None:
                return backend
    # Default: the real platform backend. It fails closed (503) when its
    # OS tools or a display are missing — never a silent no-op.
    return create_platform_backend()


def _get_settings_path(request: Optional[Request] = None) -> Optional[Path]:
    if request is not None:
        app_state = getattr(getattr(request, "app", None), "state", None)
        if app_state is not None:
            configured = getattr(app_state, "desktop_settings_path", None)
            if configured is not None:
                return Path(configured)
    return None


def _get_service(request: Optional[Request] = None) -> SystemControlService:
    # Allowed roots default to the user's home directory. Tests inject a
    # narrower root via app.state.desktop_allowed_roots.
    roots: Any = [Path.home()]
    if request is not None:
        app_state = getattr(getattr(request, "app", None), "state", None)
        if app_state is not None:
            configured = getattr(app_state, "desktop_allowed_roots", None)
            if configured is not None:
                roots = [Path(r) for r in configured]
    return SystemControlService(
        backend=_get_backend(request),
        gate=_get_gate(request),
        allowed_roots=roots,
    )


@router.get("/v1/desktop/system-control/actions")
async def list_system_control_actions() -> Dict[str, Any]:
    return {"actions": describe_actions()}


@router.post("/v1/desktop/system-control/execute")
async def execute_system_control(
    body: Dict[str, Any], request: Request
) -> Dict[str, Any]:
    action = body.get("action")
    params = body.get("params", {})
    if not isinstance(action, str) or not action:
        raise HTTPException(status_code=422, detail="action must be a non-empty string")
    if not isinstance(params, dict):
        raise HTTPException(status_code=422, detail="params must be a JSON object")
    service = _get_service(request)
    try:
        result = service.execute(action, params)
    except DesktopUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SystemControlError as exc:
        # Approval-gated failures are 403; validation failures are 422.
        if str(exc).startswith("approval required"):
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info("Desktop system-control executed: %s", action)
    return {"action": action, "result": result}


@router.get("/v1/desktop/settings")
async def get_desktop_settings(request: Request) -> Dict[str, Any]:
    return load_settings(_get_settings_path(request)).to_dict()


@router.put("/v1/desktop/settings")
async def put_desktop_settings(
    body: Dict[str, Any], request: Request
) -> Dict[str, Any]:
    try:
        settings = DesktopSettings.from_dict(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    saved = save_settings(settings, _get_settings_path(request))
    return saved.to_dict()
