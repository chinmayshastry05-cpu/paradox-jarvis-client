"""Real OS-automation desktop backends for Paradox Jarvis (Phase 6 gap).

Replaces the :class:`NoOpDesktopBackend` stub with platform backends that
drive a real desktop through OS tools — no new dependencies, no shell:

* Linux X11: ``xdotool`` for windows / mouse / keyboard, ``wmctrl`` for
  maximize, ``xdg-open`` for app/path opening, ImageMagick ``import`` /
  ``scrot`` / ``gnome-screenshot`` for screenshots.
* macOS: ``osascript`` (System Events) for windows / keyboard, ``open``
  for app/path opening, ``screencapture`` for screenshots, ``cliclick``
  (if installed) for mouse control.
* Windows: PowerShell + .NET (``user32.dll`` / ``System.Windows.Forms`` /
  ``System.Drawing``) for windows / input / screenshots, ``Start-Process``
  for app/path opening. Scripts never interpolate caller input: values
  travel as ``$args`` elements or strictly validated literals.

Fail-closed: every method first checks its OS-tool + display
preconditions. A missing tool or no display raises
:class:`DesktopUnavailableError` with a clear reason — never a silent
no-op, never a faked success. A nonzero tool exit raises
:class:`SystemControlError` with the (redacted, truncated) tool stderr.

These backends do NOT bypass the confirmation gate: the gate lives in
:class:`openjarvis.desktop.system_control.SystemControlService`, which
sits in front of every backend call. Direct backend use must still be
gated by the caller.

Honest gap: this module is unit-tested with mocked subprocess calls
only. Real mouse/keyboard/window behaviour on a real machine has NOT
been live-tested (the dev VM is headless) and must not be claimed to
work until it is, with the deployer's explicit go-ahead.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from openjarvis.desktop.system_control import (
    ALLOWED_APPS,
    DesktopUnavailableError,
    NoOpDesktopBackend,
    SystemControlError,
)
from openjarvis.security.delivery_redaction import redact_text

__all__ = [
    "LinuxX11Backend",
    "MacOSBackend",
    "WindowsBackend",
    "create_platform_backend",
]

# -- shared validation (backends validate again: they may be called directly) --

_MAX_COORD = 100_000
_MAX_TEXT_LEN = 10_000
_MAX_KEYS = 8
_KEY_TOKEN = re.compile(r"^[A-Za-z0-9_+\-]{1,32}$")
_WINDOW_ID_LINUX = re.compile(r"^\d+$")
_WINDOW_ID_MACOS = re.compile(r"^(\d+):(\d+)$")
_WINDOW_ID_WINDOWS = re.compile(r"^\d+$")
_BUTTONS = {"left": 1, "middle": 2, "right": 3}
_PNG_SUFFIX = ".png"


def _clean_coord(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SystemControlError(f"{field} must be an integer")
    if not 0 <= value <= _MAX_COORD:
        raise SystemControlError(f"{field} is out of range 0..{_MAX_COORD}")
    return value


def _clean_button(value: Any) -> str:
    if not isinstance(value, str) or value not in _BUTTONS:
        raise SystemControlError("button must be one of: left, middle, right")
    return value


def _clean_keys(value: Any) -> List[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise SystemControlError("keys must be a list of key names")
    keys = list(value)
    if not 1 <= len(keys) <= _MAX_KEYS:
        raise SystemControlError(f"keys must hold 1..{_MAX_KEYS} entries")
    for key in keys:
        if not isinstance(key, str) or not _KEY_TOKEN.match(key):
            raise SystemControlError(f"invalid key name: {key!r}")
    return keys


def _clean_text(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise SystemControlError("text must be a non-empty string")
    if len(value) > _MAX_TEXT_LEN:
        raise SystemControlError(f"text is longer than {_MAX_TEXT_LEN} chars")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value):
        raise SystemControlError("text contains control characters")
    return value


def _clean_screenshot_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SystemControlError("path must be a non-empty string")
    path = Path(value.strip())
    if path.suffix.lower() != _PNG_SUFFIX:
        raise SystemControlError("screenshot path must end in .png")
    if not path.parent.is_dir():
        raise SystemControlError("screenshot parent directory does not exist")
    return path


def _clean_window_id(value: Any, pattern: "re.Pattern[str]", what: str) -> str:
    if not isinstance(value, str) or not pattern.match(value):
        raise SystemControlError(f"invalid {what} window_id: {value!r}")
    return value


# -- shared subprocess helpers (no shell, ever) ---------------------------


def _run(
    argv: List[str],
    *,
    timeout: int = 15,
) -> "subprocess.CompletedProcess[str]":
    """Run an OS tool argv list; map failures to fail-closed errors."""
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        raise DesktopUnavailableError(f"required OS tool not found: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SystemControlError(
            f"OS tool timed out after {timeout}s: {argv[0]}"
        ) from exc


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise DesktopUnavailableError(f"required OS tool is not installed: {name}")
    return path


def _check_result(result: "subprocess.CompletedProcess[str]", tool: str) -> str:
    """Return stdout on success; fail closed on a nonzero exit."""
    if result.returncode != 0:
        detail = redact_text((result.stderr or "").strip()[:500])
        raise SystemControlError(
            f"{tool} failed (exit {result.returncode})"
            + (f": {detail}" if detail else "")
        )
    return result.stdout or ""


def _ok_result(
    backend: str,
    action: str,
    **fields: Any,
) -> Dict[str, Any]:
    return {"backend": backend, "status": action, **fields}


class _BaseBackend:
    """Shared helpers: pure-Python directory listing, result shaping."""

    backend_name = "base"

    def list_directory(self, path: str) -> List[str]:
        try:
            return sorted(os.listdir(path))
        except OSError as exc:
            raise SystemControlError(
                f"cannot list directory {path!r}: {redact_text(str(exc))}"
            ) from exc


# -- Linux X11 ------------------------------------------------------------


_LINUX_APPS: Dict[str, List[str]] = {
    "calculator": ["gnome-calculator", "kcalc", "xcalc", "qalculate-gtk"],
    "text_editor": ["gedit", "kate", "mousepad", "xed", "pluma"],
    "browser": ["firefox", "chromium", "google-chrome", "chromium-browser"],
    "file_manager": ["nautilus", "dolphin", "thunar", "pcmanfm"],
    "terminal": ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"],
}


class LinuxX11Backend(_BaseBackend):
    """Linux X11 backend via xdotool / wmctrl / xdg-open / screenshot tools."""

    backend_name = "linux-x11"

    # -- preconditions ----------------------------------------------------
    def _check(self) -> None:
        display = os.environ.get("DISPLAY")
        if not display:
            if os.environ.get("WAYLAND_DISPLAY"):
                raise DesktopUnavailableError(
                    "Wayland session detected (WAYLAND_DISPLAY is set but "
                    "DISPLAY is not): xdotool requires X11 — run under an "
                    "X11 session for desktop control"
                )
            raise DesktopUnavailableError(
                "no display detected (DISPLAY and WAYLAND_DISPLAY are both "
                "unset) — a headless session cannot drive a desktop"
            )
        _require_tool("xdotool")

    def _xdotool(self, *args: str, timeout: int = 15) -> str:
        self._check()
        result = _run(["xdotool", *args], timeout=timeout)
        return _check_result(result, "xdotool")

    # -- DesktopBackend protocol ------------------------------------------
    def list_windows(self) -> List[Dict[str, Any]]:
        self._check()
        active = self._xdotool("getactivewindow").strip()
        out = self._xdotool("search", "--onlyvisible", "--name", ".*", timeout=30)
        windows: List[Dict[str, Any]] = []
        for wid in out.split():
            if not _WINDOW_ID_LINUX.match(wid) or len(windows) >= 100:
                continue
            try:
                title = self._xdotool("getwindowname", wid).strip()
            except SystemControlError:
                continue  # window closed between search and query: skip it
            windows.append({"id": wid, "title": title, "focused": wid == active})
        return windows

    def list_apps(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": app_id,
                "label": ALLOWED_APPS[app_id],
                "available": any(shutil.which(cmd) for cmd in _LINUX_APPS[app_id]),
            }
            for app_id in ALLOWED_APPS
            if app_id in _LINUX_APPS
        ]

    def focus_window(self, window_id: str) -> Dict[str, Any]:
        wid = _clean_window_id(window_id, _WINDOW_ID_LINUX, "X11")
        self._xdotool("windowactivate", "--sync", wid)
        return _ok_result(self.backend_name, "focused", window_id=wid)

    def minimize_window(self, window_id: str) -> Dict[str, Any]:
        wid = _clean_window_id(window_id, _WINDOW_ID_LINUX, "X11")
        self._xdotool("windowminimize", "--sync", wid)
        return _ok_result(self.backend_name, "minimized", window_id=wid)

    def maximize_window(self, window_id: str) -> Dict[str, Any]:
        wid = _clean_window_id(window_id, _WINDOW_ID_LINUX, "X11")
        self._check()
        _require_tool("wmctrl")
        result = _run(
            ["wmctrl", "-i", "-r", wid, "-b", "add,maximized_vert,maximized_horz"]
        )
        _check_result(result, "wmctrl")
        return _ok_result(self.backend_name, "maximized", window_id=wid)

    def close_window(self, window_id: str) -> Dict[str, Any]:
        wid = _clean_window_id(window_id, _WINDOW_ID_LINUX, "X11")
        self._xdotool("windowclose", "--sync", wid)
        return _ok_result(self.backend_name, "closed", window_id=wid)

    def launch_app(self, app_id: str) -> Dict[str, Any]:
        self._check()
        if app_id not in _LINUX_APPS:
            raise SystemControlError(f"app_id is not allowlisted: {app_id}")
        for cmd in _LINUX_APPS[app_id]:
            if shutil.which(cmd):
                try:
                    subprocess.Popen(  # noqa: S603 - argv list, no shell
                        [cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                except OSError as exc:
                    raise SystemControlError(
                        f"could not launch {app_id}: {redact_text(str(exc))}"
                    ) from exc
                return _ok_result(
                    self.backend_name, "launched", app_id=app_id, command=cmd
                )
        raise DesktopUnavailableError(
            f"no known executable installed for app: {app_id}"
        )

    def open_path(self, path: str) -> Dict[str, Any]:
        self._check()
        _require_tool("xdg-open")
        result = _run(["xdg-open", path], timeout=30)
        _check_result(result, "xdg-open")
        return _ok_result(self.backend_name, "opened", path=path)

    # -- input / screenshot ------------------------------------------------
    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        self._xdotool("mousemove", str(_clean_coord(x, "x")), str(_clean_coord(y, "y")))
        return _ok_result(self.backend_name, "moved", x=x, y=y)

    def mouse_click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        button = _clean_button(button)
        self._xdotool("mousemove", str(_clean_coord(x, "x")), str(_clean_coord(y, "y")))
        self._xdotool("click", str(_BUTTONS[button]))
        return _ok_result(self.backend_name, "clicked", x=x, y=y, button=button)

    def key_press(self, keys: Sequence[str]) -> Dict[str, Any]:
        combo = "+".join(_clean_keys(keys))
        self._xdotool("key", combo)
        return _ok_result(self.backend_name, "key_pressed", keys=list(keys))

    def type_text(self, text: str) -> Dict[str, Any]:
        cleaned = _clean_text(text)
        self._xdotool("type", "--clearmodifiers", "--", cleaned)
        return _ok_result(self.backend_name, "typed", chars=len(cleaned))

    def screenshot(self, path: str) -> Dict[str, Any]:
        self._check()
        dest = _clean_screenshot_path(path)
        attempts: List[List[str]] = [
            ["import", "-window", "root", str(dest)],
            ["scrot", str(dest)],
            ["gnome-screenshot", "-f", str(dest)],
        ]
        tried: List[str] = []
        for argv in attempts:
            if shutil.which(argv[0]) is None:
                continue
            tried.append(argv[0])
            result = _run(argv, timeout=30)
            if result.returncode == 0:
                return _ok_result(
                    self.backend_name,
                    "screenshot",
                    path=str(dest),
                    tool=argv[0],
                )
            _check_result(result, argv[0])  # raises with tool stderr
        if not tried:
            raise DesktopUnavailableError(
                "no screenshot tool installed on Linux (tried: import "
                "[ImageMagick], scrot, gnome-screenshot)"
            )
        raise SystemControlError("screenshot failed")  # unreachable


# -- macOS ------------------------------------------------------------------


_MACOS_APPS: Dict[str, str] = {
    "calculator": "Calculator",
    "text_editor": "TextEdit",
    "browser": "Safari",
    "file_manager": "Finder",
    "terminal": "Terminal",
}

_MACOS_KEY_CODES: Dict[str, int] = {
    "return": 36,
    "tab": 48,
    "space": 49,
    "escape": 53,
    "delete": 51,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
}

_MACOS_MODIFIERS: Dict[str, str] = {
    "ctrl": "control down",
    "control": "control down",
    "alt": "option down",
    "option": "option down",
    "shift": "shift down",
    "super": "command down",
    "cmd": "command down",
    "command": "command down",
}


def _applescript_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MacOSBackend(_BaseBackend):
    """macOS backend via osascript / open / screencapture / cliclick."""

    backend_name = "macos"

    def _osascript(self, script: str, *, timeout: int = 15) -> str:
        _require_tool("osascript")
        result = _run(["osascript", "-e", script], timeout=timeout)
        return _check_result(result, "osascript")

    def _parse_window_id(self, window_id: str) -> tuple[int, int]:
        cleaned = _clean_window_id(window_id, _WINDOW_ID_MACOS, "macOS")
        match = _WINDOW_ID_MACOS.match(cleaned)
        assert match is not None
        return int(match.group(1)), int(match.group(2))

    def _window_script(self, window_id: str, body: str) -> str:
        pid, index = self._parse_window_id(window_id)
        return (
            f'tell application "System Events" to tell process id {pid}\n'
            f"{body.format(index=index)}\n"
            "end tell"
        )

    # -- DesktopBackend protocol ------------------------------------------
    def list_windows(self) -> List[Dict[str, Any]]:
        script = (
            'tell application "System Events"\n'
            '  set out to ""\n'
            "  repeat with proc in "
            "(every process where background only is false)\n"
            "    try\n"
            "      set pid to unix id of proc\n"
            "      set pname to name of proc\n"
            "      repeat with i from 1 to (count of windows of proc)\n"
            "        set wtitle to name of window i of proc\n"
            '        set out to out & pid & "\x1f" & pname & "\x1f" '
            '& i & "\x1f" & wtitle & "\n"\n'
            "      end repeat\n"
            "    end try\n"
            "  end repeat\n"
            "  return out\n"
            "end tell"
        )
        out = self._osascript(script, timeout=30)
        windows: List[Dict[str, Any]] = []
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) != 4:
                continue
            pid, pname, index, title = parts
            if not pid.isdigit() or not index.isdigit():
                continue
            windows.append(
                {
                    "id": f"{pid}:{index}",
                    "title": title,
                    "process": pname,
                    "focused": False,
                }
            )
        return windows

    def list_apps(self) -> List[Dict[str, Any]]:
        return [
            {"id": app_id, "label": ALLOWED_APPS[app_id], "available": True}
            for app_id in ALLOWED_APPS
            if app_id in _MACOS_APPS
        ]

    def focus_window(self, window_id: str) -> Dict[str, Any]:
        script = self._window_script(
            window_id,
            '  set frontmost to true\n  perform action "AXRaise" of window {index}',
        )
        self._osascript(script)
        return _ok_result(self.backend_name, "focused", window_id=window_id)

    def minimize_window(self, window_id: str) -> Dict[str, Any]:
        script = self._window_script(
            window_id, "  set minimized of window {index} to true"
        )
        self._osascript(script)
        return _ok_result(self.backend_name, "minimized", window_id=window_id)

    def maximize_window(self, window_id: str) -> Dict[str, Any]:
        # Zoom (green) button click: best-effort standard pattern.
        script = self._window_script(window_id, "  click button 2 of window {index}")
        self._osascript(script)
        return _ok_result(self.backend_name, "maximized", window_id=window_id)

    def close_window(self, window_id: str) -> Dict[str, Any]:
        # Close (red) button click: best-effort standard pattern.
        script = self._window_script(window_id, "  click button 1 of window {index}")
        self._osascript(script)
        return _ok_result(self.backend_name, "closed", window_id=window_id)

    def launch_app(self, app_id: str) -> Dict[str, Any]:
        if app_id not in _MACOS_APPS:
            raise SystemControlError(f"app_id is not allowlisted: {app_id}")
        _require_tool("open")
        result = _run(["open", "-a", _MACOS_APPS[app_id]], timeout=30)
        _check_result(result, "open")
        return _ok_result(self.backend_name, "launched", app_id=app_id)

    def open_path(self, path: str) -> Dict[str, Any]:
        _require_tool("open")
        result = _run(["open", path], timeout=30)
        _check_result(result, "open")
        return _ok_result(self.backend_name, "opened", path=path)

    # -- input / screenshot ------------------------------------------------
    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        _require_tool("cliclick")
        result = _run(["cliclick", f"m:{_clean_coord(x, 'x')},{_clean_coord(y, 'y')}"])
        _check_result(result, "cliclick")
        return _ok_result(self.backend_name, "moved", x=x, y=y)

    def mouse_click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        button = _clean_button(button)
        if button == "middle":
            raise DesktopUnavailableError(
                "middle click is not supported by cliclick on macOS"
            )
        _require_tool("cliclick")
        verb = "c" if button == "left" else "rc"
        result = _run(
            ["cliclick", f"{verb}:{_clean_coord(x, 'x')},{_clean_coord(y, 'y')}"]
        )
        _check_result(result, "cliclick")
        return _ok_result(self.backend_name, "clicked", x=x, y=y, button=button)

    def key_press(self, keys: Sequence[str]) -> Dict[str, Any]:
        cleaned = _clean_keys(keys)
        *modifiers, key = cleaned
        using: List[str] = []
        for mod in modifiers:
            mapped = _MACOS_MODIFIERS.get(mod.lower())
            if mapped is None:
                raise SystemControlError(f"unknown modifier key: {mod!r}")
            using.append(mapped)
        using_clause = f" using {{{', '.join(using)}}}" if using else ""
        if len(key) == 1:
            action = f'keystroke "{_applescript_escape(key)}"{using_clause}'
        else:
            code = _MACOS_KEY_CODES.get(key.lower())
            if code is None:
                raise SystemControlError(f"unknown key name: {key!r}")
            action = f"key code {code}{using_clause}"
        self._osascript(f'tell application "System Events" to {action}')
        return _ok_result(self.backend_name, "key_pressed", keys=list(cleaned))

    def type_text(self, text: str) -> Dict[str, Any]:
        cleaned = _clean_text(text)
        self._osascript(
            'tell application "System Events" to keystroke '
            f'"{_applescript_escape(cleaned)}"'
        )
        return _ok_result(self.backend_name, "typed", chars=len(cleaned))

    def screenshot(self, path: str) -> Dict[str, Any]:
        _require_tool("screencapture")
        dest = _clean_screenshot_path(path)
        result = _run(["screencapture", "-x", str(dest)], timeout=30)
        _check_result(result, "screencapture")
        return _ok_result(
            self.backend_name,
            "screenshot",
            path=str(dest),
            tool="screencapture",
        )


# -- Windows --------------------------------------------------------------


_WINDOWS_APPS: Dict[str, str] = {
    "calculator": "calc.exe",
    "text_editor": "notepad.exe",
    "browser": "msedge.exe",
    "file_manager": "explorer.exe",
    "terminal": "wt.exe",
}

_WINDOWS_USER32 = (
    "Add-Type -TypeDefinition 'using System; "
    "using System.Runtime.InteropServices; "
    "public static class U32 { "
    '[DllImport("user32.dll")] public static extern bool '
    "SetForegroundWindow(IntPtr hWnd); "
    '[DllImport("user32.dll")] public static extern bool '
    "ShowWindow(IntPtr hWnd, int nCmdShow); "
    '[DllImport("user32.dll")] public static extern bool '
    "PostMessage(IntPtr hWnd, uint Msg, UIntPtr wParam, IntPtr lParam); "
    '[DllImport("user32.dll")] public static extern bool '
    "SetCursorPos(int X, int Y); "
    '[DllImport("user32.dll")] public static extern void '
    "mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, "
    "UIntPtr dwExtraInfo); }'"
)

_WINDOWS_SENDKEYS_MAP: Dict[str, str] = {
    "return": "{ENTER}",
    "enter": "{ENTER}",
    "tab": "{TAB}",
    "escape": "{ESC}",
    "esc": "{ESC}",
    "space": " ",
    "delete": "{DEL}",
    "backspace": "{BACKSPACE}",
    "left": "{LEFT}",
    "right": "{RIGHT}",
    "down": "{DOWN}",
    "up": "{UP}",
    "home": "{HOME}",
    "end": "{END}",
    "pageup": "{PGUP}",
    "pagedown": "{PGDN}",
    "insert": "{INS}",
    "f1": "{F1}",
    "f2": "{F2}",
    "f3": "{F3}",
    "f4": "{F4}",
    "f5": "{F5}",
    "f6": "{F6}",
    "f7": "{F7}",
    "f8": "{F8}",
    "f9": "{F9}",
    "f10": "{F10}",
    "f11": "{F11}",
    "f12": "{F12}",
}

_WINDOWS_MODIFIERS: Dict[str, str] = {
    "ctrl": "^",
    "control": "^",
    "alt": "%",
    "shift": "+",
}


class WindowsBackend(_BaseBackend):
    """Windows backend via PowerShell + .NET (user32 / Forms / Drawing)."""

    backend_name = "windows"

    def _powershell(self, script: str, *args: str, timeout: int = 15) -> str:
        exe = shutil.which("pwsh") or shutil.which("powershell")
        if exe is None:
            raise DesktopUnavailableError(
                "PowerShell is not installed (required for Windows desktop control)"
            )
        result = _run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script, *args],
            timeout=timeout,
        )
        return _check_result(result, exe)

    def _hwnd(self, window_id: str) -> str:
        return _clean_window_id(window_id, _WINDOW_ID_WINDOWS, "Windows")

    # -- DesktopBackend protocol ------------------------------------------
    def list_windows(self) -> List[Dict[str, Any]]:
        script = (
            "Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } | "
            "ForEach-Object { "
            '"$($_.MainWindowHandle)`t$($_.Id)`t'
            '$($_.MainWindowTitle -replace "`n", \' \')" }'
        )
        out = self._powershell(script, timeout=30)
        windows: List[Dict[str, Any]] = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) != 3 or not parts[0].isdigit():
                continue
            windows.append(
                {
                    "id": parts[0],
                    "title": parts[2],
                    "process_id": parts[1],
                    "focused": False,
                }
            )
        return windows

    def list_apps(self) -> List[Dict[str, Any]]:
        return [
            {"id": app_id, "label": ALLOWED_APPS[app_id], "available": True}
            for app_id in ALLOWED_APPS
            if app_id in _WINDOWS_APPS
        ]

    def focus_window(self, window_id: str) -> Dict[str, Any]:
        hwnd = self._hwnd(window_id)
        out = self._powershell(
            _WINDOWS_USER32 + "; [U32]::SetForegroundWindow([IntPtr]$args[0])",
            hwnd,
        )
        if out.strip() != "True":
            raise SystemControlError(f"could not focus window: {window_id}")
        return _ok_result(self.backend_name, "focused", window_id=window_id)

    def minimize_window(self, window_id: str) -> Dict[str, Any]:
        hwnd = self._hwnd(window_id)
        self._powershell(
            _WINDOWS_USER32 + "; [U32]::ShowWindow([IntPtr]$args[0], 6) | Out-Null",
            hwnd,
        )
        return _ok_result(self.backend_name, "minimized", window_id=window_id)

    def maximize_window(self, window_id: str) -> Dict[str, Any]:
        hwnd = self._hwnd(window_id)
        self._powershell(
            _WINDOWS_USER32 + "; [U32]::ShowWindow([IntPtr]$args[0], 3) | Out-Null",
            hwnd,
        )
        return _ok_result(self.backend_name, "maximized", window_id=window_id)

    def close_window(self, window_id: str) -> Dict[str, Any]:
        hwnd = self._hwnd(window_id)
        self._powershell(
            _WINDOWS_USER32 + "; [U32]::PostMessage([IntPtr]$args[0], 0x10, "
            "[UIntPtr]::Zero, [IntPtr]::Zero) | Out-Null",
            hwnd,
        )
        return _ok_result(self.backend_name, "closed", window_id=window_id)

    def launch_app(self, app_id: str) -> Dict[str, Any]:
        if app_id not in _WINDOWS_APPS:
            raise SystemControlError(f"app_id is not allowlisted: {app_id}")
        exe = _WINDOWS_APPS[app_id]
        if app_id == "terminal" and shutil.which("wt.exe") is None:
            exe = "powershell.exe"
        self._powershell("Start-Process -FilePath $args[0]", exe)
        return _ok_result(self.backend_name, "launched", app_id=app_id, command=exe)

    def open_path(self, path: str) -> Dict[str, Any]:
        self._powershell("Start-Process -FilePath $args[0]", path)
        return _ok_result(self.backend_name, "opened", path=path)

    # -- input / screenshot ------------------------------------------------
    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        self._powershell(
            _WINDOWS_USER32 + "; [U32]::SetCursorPos([int]$args[0], [int]$args[1])",
            str(_clean_coord(x, "x")),
            str(_clean_coord(y, "y")),
        )
        return _ok_result(self.backend_name, "moved", x=x, y=y)

    def mouse_click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        button = _clean_button(button)
        down, up = {
            "left": (0x0002, 0x0004),
            "middle": (0x0020, 0x0040),
            "right": (0x0008, 0x0010),
        }[button]
        script = (
            _WINDOWS_USER32 + "; [U32]::SetCursorPos([int]$args[0], [int]$args[1]); "
            f"[U32]::mouse_event({down}, 0, 0, 0, [UIntPtr]::Zero); "
            f"[U32]::mouse_event({up}, 0, 0, 0, [UIntPtr]::Zero)"
        )
        self._powershell(
            script,
            str(_clean_coord(x, "x")),
            str(_clean_coord(y, "y")),
        )
        return _ok_result(self.backend_name, "clicked", x=x, y=y, button=button)

    def key_press(self, keys: Sequence[str]) -> Dict[str, Any]:
        cleaned = _clean_keys(keys)
        *modifiers, key = cleaned
        prefix = ""
        for mod in modifiers:
            mapped = _WINDOWS_MODIFIERS.get(mod.lower())
            if mapped is None:
                raise SystemControlError(
                    "Windows SendKeys does not support modifier: "
                    f"{mod!r} (use ctrl / alt / shift)"
                )
            prefix += mapped
        if len(key) == 1:
            if key in "+^%~(){}":
                send = "{" + key + "}"
            else:
                send = key
        else:
            mapped_key = _WINDOWS_SENDKEYS_MAP.get(key.lower())
            if mapped_key is None:
                raise SystemControlError(f"unknown key name: {key!r}")
            send = mapped_key
        self._sendkeys(prefix + send)
        return _ok_result(self.backend_name, "key_pressed", keys=list(cleaned))

    def type_text(self, text: str) -> Dict[str, Any]:
        cleaned = _clean_text(text)
        escaped = "".join(
            "{ENTER}" if ch == "\n" else ("{" + ch + "}" if ch in "+^%~(){}" else ch)
            for ch in cleaned
        )
        self._sendkeys(escaped)
        return _ok_result(self.backend_name, "typed", chars=len(cleaned))

    def _sendkeys(self, send: str) -> None:
        # SendKeys text travels as a $args element, never interpolated.
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "[System.Windows.Forms.SendKeys]::SendWait($args[0])"
        )
        self._powershell(script, send)

    def screenshot(self, path: str) -> Dict[str, Any]:
        dest = _clean_screenshot_path(path)
        script = (
            "Add-Type -AssemblyName System.Drawing; "
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height); "
            "$g = [System.Drawing.Graphics]::FromImage($bmp); "
            "$g.CopyFromScreen($b.Location, "
            "[System.Drawing.Point]::Empty, $b.Size); "
            "$bmp.Save($args[0], "
            "[System.Drawing.Imaging.ImageFormat]::Png)"
        )
        self._powershell(script, str(dest), timeout=30)
        return _ok_result(
            self.backend_name,
            "screenshot",
            path=str(dest),
            tool="powershell-dotnet",
        )


# -- factory ----------------------------------------------------------------


def create_platform_backend(platform: Optional[str] = None) -> Any:
    """Return the real backend for this OS, or NoOp when unsupported.

    ``platform`` overrides :data:`sys.platform` (tests / embedding).
    Never raises: an unknown platform yields the fail-closed NoOp backend.
    """
    plat = platform if platform is not None else sys.platform
    if plat.startswith("linux"):
        return LinuxX11Backend()
    if plat == "darwin":
        return MacOSBackend()
    if plat in ("win32", "cygwin"):
        return WindowsBackend()
    return NoOpDesktopBackend()
