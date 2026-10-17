"""Desktop system control for Paradox Jarvis Ultra (Phase 6, desktop only).

GUI / system-control surface: window management, app launching, and
file operations integrated with the agent. Every consequential action
goes through the central confirmation gate
(:class:`openjarvis.security.confirmation.ConfirmationGate`): the caller
first grants an approval for ONE exact ``(action, params)`` pair via
``POST /v1/approvals/tool`` (tool ``desktop.system_control``) and the
execute path consumes it single-use by exact match. There is no
"approve everything" mode, and this module never bypasses the gate.

No real desktop interaction happens here by default: the default
backend (:class:`NoOpDesktopBackend`) reports desktop control as
unavailable. A platform backend
(:mod:`openjarvis.desktop.platform_backend`) plugs in via
:class:`DesktopBackend`; tests inject a fake. File paths are validated
against allowed roots and the sensitive-file policy, and
backend-returned text is redacted before it leaves this module.

shortcut: listing uses the string-level containment pre-check plus the
sensitive-file filter, NOT the descriptor-based ``open_within`` open —
it never opens a file, it only lists names. Upgrade to ``open_within``
if any listing path is ever opened by string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence

from openjarvis.security.canonical_path import resolve_within
from openjarvis.security.confirmation import ConfirmationGate
from openjarvis.security.delivery_redaction import redact_text
from openjarvis.security.file_policy import filter_sensitive_paths, is_sensitive_file

TOOL_NAME = "desktop.system_control"

# Action catalogue: consequential actions require a consumed gate
# approval; read-only actions do not. No shell / arbitrary-command
# action exists on purpose — app launching is allowlist-only.
ACTIONS: Dict[str, Dict[str, Any]] = {
    "list_windows": {"consequential": False, "params": {}},
    "list_apps": {"consequential": False, "params": {}},
    "list_directory": {"consequential": False, "params": {"path": "string"}},
    "focus_window": {"consequential": True, "params": {"window_id": "string"}},
    "minimize_window": {"consequential": True, "params": {"window_id": "string"}},
    "maximize_window": {"consequential": True, "params": {"window_id": "string"}},
    "close_window": {"consequential": True, "params": {"window_id": "string"}},
    "launch_app": {"consequential": True, "params": {"app_id": "string"}},
    "open_path": {"consequential": True, "params": {"path": "string"}},
    # Input / screenshot actions (gap-B platform backends). All
    # consequential: each one moves the real desktop or captures it.
    "mouse_move": {"consequential": True, "params": {"x": "int", "y": "int"}},
    "mouse_click": {
        "consequential": True,
        "params": {"x": "int", "y": "int", "button": "string"},
    },
    "key_press": {"consequential": True, "params": {"keys": "list"}},
    "type_text": {"consequential": True, "params": {"text": "string"}},
    "screenshot": {"consequential": True, "params": {"path": "string"}},
}

# Allowlisted launch targets: display label only — no executable paths,
# no shell. A platform backend maps these ids to OS launch behaviour.
ALLOWED_APPS: Dict[str, str] = {
    "calculator": "Calculator",
    "text_editor": "Text editor",
    "browser": "Web browser",
    "file_manager": "File manager",
    "terminal": "Terminal",
}

_MAX_ID_LEN = 128
_MAX_TEXT_LEN = 10_000
_MAX_KEYS = 8
_MAX_COORD = 100_000
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_KEY_TOKEN = re.compile(r"^[A-Za-z0-9_+\-]{1,32}$")
_BUTTONS = ("left", "middle", "right")


class SystemControlError(ValueError):
    """Safe, redacted system-control failure (safe to show in the UI)."""


class DesktopUnavailableError(SystemControlError):
    """No desktop backend is wired in (no real desktop interaction)."""


def describe_actions() -> List[Dict[str, Any]]:
    """Return the action catalogue (stable order, no secrets)."""
    return [{"action": name, **spec} for name, spec in ACTIONS.items()]


def _clean_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemControlError(f"{field} must be a non-empty string")
    cleaned = value.strip()
    if len(cleaned) > _MAX_ID_LEN or _CONTROL_CHARS.search(cleaned):
        raise SystemControlError(f"{field} is invalid")
    return cleaned


def _clean_path(value: Any, allowed_roots: Sequence[Path]) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SystemControlError("path must be a non-empty string")
    if _CONTROL_CHARS.search(value):
        raise SystemControlError("path is invalid")
    try:
        resolved = resolve_within(value.strip(), allowed_roots)
    except ValueError as exc:
        raise SystemControlError("path is outside the allowed roots") from exc
    if is_sensitive_file(resolved):
        raise SystemControlError("path is blocked by the sensitive-file policy")
    return resolved


def _clean_coord(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SystemControlError(f"{field} must be an integer")
    if not 0 <= value <= _MAX_COORD:
        raise SystemControlError(f"{field} is out of range 0..{_MAX_COORD}")
    return value


def _clean_button(value: Any) -> str:
    if not isinstance(value, str) or value not in _BUTTONS:
        raise SystemControlError(f"button must be one of: {', '.join(_BUTTONS)}")
    return value


def _clean_keys(value: Any) -> List[str]:
    if not isinstance(value, list):
        raise SystemControlError("keys must be a list of key names")
    if not 1 <= len(value) <= _MAX_KEYS:
        raise SystemControlError(f"keys must hold 1..{_MAX_KEYS} entries")
    for key in value:
        if not isinstance(key, str) or not _KEY_TOKEN.match(key):
            raise SystemControlError(f"invalid key name: {key!r}")
    return list(value)


def _clean_text(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise SystemControlError("text must be a non-empty string")
    if len(value) > _MAX_TEXT_LEN:
        raise SystemControlError(f"text is longer than {_MAX_TEXT_LEN} chars")
    # Newline/tab are legitimate typing; other control chars are not.
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value):
        raise SystemControlError("text contains control characters")
    return value


class DesktopBackend(Protocol):
    """Platform desktop backend. All methods are mocked in tests."""

    def list_windows(self) -> List[Dict[str, Any]]: ...
    def list_apps(self) -> List[Dict[str, Any]]: ...
    def list_directory(self, path: str) -> List[str]: ...
    def focus_window(self, window_id: str) -> Dict[str, Any]: ...
    def minimize_window(self, window_id: str) -> Dict[str, Any]: ...
    def maximize_window(self, window_id: str) -> Dict[str, Any]: ...
    def close_window(self, window_id: str) -> Dict[str, Any]: ...
    def launch_app(self, app_id: str) -> Dict[str, Any]: ...
    def open_path(self, path: str) -> Dict[str, Any]: ...
    def mouse_move(self, x: int, y: int) -> Dict[str, Any]: ...
    def mouse_click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]: ...
    def key_press(self, keys: Sequence[str]) -> Dict[str, Any]: ...
    def type_text(self, text: str) -> Dict[str, Any]: ...
    def screenshot(self, path: str) -> Dict[str, Any]: ...


class NoOpDesktopBackend:
    """Default backend: reports desktop control as unavailable.

    No real desktop interaction, no subprocess, no shell. A platform
    backend replaces this; until one is wired in, every action fails
    closed with a clear message instead of pretending to act.
    """

    def _unavailable(self) -> Any:
        raise DesktopUnavailableError(
            "desktop control backend is not wired in on this build"
        )

    def list_windows(self) -> List[Dict[str, Any]]:
        return self._unavailable()

    def list_apps(self) -> List[Dict[str, Any]]:
        return self._unavailable()

    def list_directory(self, path: str) -> List[str]:
        return self._unavailable()

    def focus_window(self, window_id: str) -> Dict[str, Any]:
        return self._unavailable()

    def minimize_window(self, window_id: str) -> Dict[str, Any]:
        return self._unavailable()

    def maximize_window(self, window_id: str) -> Dict[str, Any]:
        return self._unavailable()

    def close_window(self, window_id: str) -> Dict[str, Any]:
        return self._unavailable()

    def launch_app(self, app_id: str) -> Dict[str, Any]:
        return self._unavailable()

    def open_path(self, path: str) -> Dict[str, Any]:
        return self._unavailable()

    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        return self._unavailable()

    def mouse_click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        return self._unavailable()

    def key_press(self, keys: Sequence[str]) -> Dict[str, Any]:
        return self._unavailable()

    def type_text(self, text: str) -> Dict[str, Any]:
        return self._unavailable()

    def screenshot(self, path: str) -> Dict[str, Any]:
        return self._unavailable()


@dataclass
class SystemControlService:
    """Validate + approval-gate + dispatch desktop system-control actions."""

    backend: Any = None
    gate: Optional[ConfirmationGate] = None
    allowed_roots: Sequence[Path] = ()
    allowed_apps: Optional[Dict[str, str]] = None

    def __post_init__(self) -> None:
        if self.backend is None:
            self.backend = NoOpDesktopBackend()
        if self.gate is None:
            self.gate = ConfirmationGate()
        if self.allowed_apps is None:
            self.allowed_apps = dict(ALLOWED_APPS)
        self._roots: List[Path] = [Path(r) for r in self.allowed_roots]

    # -- validation -----------------------------------------------------
    def validate(self, action: str, params: Any) -> Dict[str, Any]:
        """Validate (action, params); returns normalised params."""
        if action not in ACTIONS:
            raise SystemControlError(f"unknown system-control action: {action}")
        if not isinstance(params, dict):
            raise SystemControlError("params must be a JSON object")
        expected = set(ACTIONS[action]["params"])
        unknown = set(params) - expected
        if unknown:
            raise SystemControlError(f"unknown params for {action}: {sorted(unknown)}")
        normalised: Dict[str, Any] = {}
        if "window_id" in expected:
            normalised["window_id"] = _clean_id(params.get("window_id"), "window_id")
        if "app_id" in expected:
            app_id = _clean_id(params.get("app_id"), "app_id")
            if app_id not in (self.allowed_apps or {}):
                raise SystemControlError(f"app_id is not allowlisted: {app_id}")
            normalised["app_id"] = app_id
        if "path" in expected:
            normalised["path"] = str(_clean_path(params.get("path"), self._roots))
        if "x" in expected:
            normalised["x"] = _clean_coord(params.get("x"), "x")
        if "y" in expected:
            normalised["y"] = _clean_coord(params.get("y"), "y")
        if "button" in expected:
            # Button defaults to left when omitted; an explicit bad
            # value is rejected, never silently coerced.
            normalised["button"] = _clean_button(params.get("button", "left"))
        if "keys" in expected:
            normalised["keys"] = _clean_keys(params.get("keys"))
        if "text" in expected:
            normalised["text"] = _clean_text(params.get("text"))
        return normalised

    # -- execution ------------------------------------------------------
    def execute(self, action: str, params: Any) -> Dict[str, Any]:
        """Validate, consume a gate approval (consequential only), dispatch."""
        normalised = self.validate(action, params)
        if ACTIONS[action]["consequential"]:
            assert self.gate is not None
            approved = self.gate.consume_matching(
                TOOL_NAME, {"action": action, "params": normalised}
            )
            if not approved:
                raise SystemControlError(
                    "approval required: grant a single-use approval for this "
                    "exact action + params via POST /v1/approvals/tool first"
                )
        try:
            result = self._dispatch(action, normalised)
        except DesktopUnavailableError:
            raise
        except SystemControlError:
            raise
        except Exception as exc:  # backend failures must not leak internals
            raise SystemControlError(
                f"{action} failed: {redact_text(str(exc))}"
            ) from exc
        return self._sanitize(result)

    def _dispatch(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        backend = self.backend
        if action == "list_windows":
            return {"windows": self._sanitize(backend.list_windows())}
        if action == "list_apps":
            return {"apps": self._sanitize(backend.list_apps())}
        if action == "list_directory":
            entries = backend.list_directory(params["path"])
            kept = filter_sensitive_paths([Path(params["path"]) / e for e in entries])
            kept_names = {p.name for p in kept}
            return {"path": params["path"], "entries": sorted(kept_names)}
        if action in (
            "focus_window",
            "minimize_window",
            "maximize_window",
            "close_window",
        ):
            return self._sanitize(getattr(backend, action)(params["window_id"]))
        if action == "launch_app":
            return self._sanitize(backend.launch_app(params["app_id"]))
        if action == "open_path":
            return self._sanitize(backend.open_path(params["path"]))
        if action == "mouse_move":
            return self._sanitize(backend.mouse_move(params["x"], params["y"]))
        if action == "mouse_click":
            return self._sanitize(
                backend.mouse_click(params["x"], params["y"], params["button"])
            )
        if action == "key_press":
            return self._sanitize(backend.key_press(params["keys"]))
        if action == "type_text":
            return self._sanitize(backend.type_text(params["text"]))
        if action == "screenshot":
            return self._sanitize(backend.screenshot(params["path"]))
        raise SystemControlError(f"unknown system-control action: {action}")

    @staticmethod
    def _sanitize(value: Any) -> Any:
        """Redact strings recursively so backend text cannot leak secrets."""
        if isinstance(value, str):
            return redact_text(value)
        if isinstance(value, dict):
            return {k: SystemControlService._sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [SystemControlService._sanitize(v) for v in value]
        return value


__all__ = [
    "ACTIONS",
    "ALLOWED_APPS",
    "TOOL_NAME",
    "DesktopBackend",
    "DesktopUnavailableError",
    "NoOpDesktopBackend",
    "SystemControlError",
    "SystemControlService",
    "describe_actions",
]
