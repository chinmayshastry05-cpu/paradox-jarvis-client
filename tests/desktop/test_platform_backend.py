"""Tests for the real platform desktop backends (gap-B).

Every OS call is mocked: these tests run with NO live display and must
never move a real mouse, press a real key, or open a real window. They
assert the exact argv / script each backend would hand to the OS tool,
the fail-closed behaviour when a tool or display is missing, and that
the confirmation gate still fronts the new actions.
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List
from unittest import mock

import pytest

from openjarvis.desktop import platform_backend as pb
from openjarvis.desktop.platform_backend import (
    LinuxX11Backend,
    MacOSBackend,
    WindowsBackend,
    create_platform_backend,
)
from openjarvis.desktop.system_control import (
    TOOL_NAME,
    DesktopUnavailableError,
    NoOpDesktopBackend,
    SystemControlError,
    SystemControlService,
)
from openjarvis.security.confirmation import ConfirmationGate


def _cp(stdout: str = "", returncode: int = 0, stderr: str = "") -> Any:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _which(mapping: Dict[str, str | None]):
    def fake(name: str, *args: Any, **kwargs: Any) -> str | None:
        return mapping.get(name)

    return fake


@pytest.fixture
def linux_env():
    with (
        mock.patch.dict("os.environ", {"DISPLAY": ":0"}, clear=True),
        mock.patch.object(
            pb.shutil, "which", side_effect=_which({"xdotool": "/usr/bin/xdotool"})
        ),
    ):
        yield


@pytest.fixture
def linux_backend(linux_env):
    return LinuxX11Backend()


# -- Linux X11 -------------------------------------------------------------


def test_linux_no_display_is_unavailable() -> None:
    with mock.patch.dict("os.environ", {}, clear=True):
        with pytest.raises(DesktopUnavailableError, match="no display"):
            LinuxX11Backend().list_windows()


def test_linux_wayland_without_x11_is_unavailable() -> None:
    with mock.patch.dict("os.environ", {"WAYLAND_DISPLAY": "wayland-1"}, clear=True):
        with pytest.raises(DesktopUnavailableError, match="Wayland"):
            LinuxX11Backend().focus_window("42")


def test_linux_missing_xdotool_is_unavailable(linux_env) -> None:
    with mock.patch.object(pb.shutil, "which", side_effect=_which({})):
        with pytest.raises(DesktopUnavailableError, match="xdotool"):
            LinuxX11Backend().list_windows()


def test_linux_list_windows_parses_ids_and_focus(linux_backend) -> None:
    def fake_run(argv, **kwargs):
        if argv[-1] == "getactivewindow":
            return _cp("42\n")
        if argv[1] == "search":
            return _cp("42\n7\n")
        if argv[1] == "getwindowname":
            return _cp({"42": "Chat — Jarvis\n", "7": "Calc\n"}[argv[2]])
        raise AssertionError(f"unexpected argv: {argv}")

    with mock.patch.object(pb.subprocess, "run", side_effect=fake_run):
        windows = linux_backend.list_windows()
    assert windows == [
        {"id": "42", "title": "Chat — Jarvis", "focused": True},
        {"id": "7", "title": "Calc", "focused": False},
    ]


def test_linux_window_ops_send_exact_xdotool_argv(linux_backend) -> None:
    seen: List[list] = []

    def fake_run(argv, **kwargs):
        seen.append(argv)
        return _cp("")

    with mock.patch.object(pb.subprocess, "run", side_effect=fake_run):
        assert linux_backend.focus_window("42")["status"] == "focused"
        assert linux_backend.minimize_window("42")["status"] == "minimized"
        assert linux_backend.close_window("42")["status"] == "closed"
    assert seen == [
        ["xdotool", "windowactivate", "--sync", "42"],
        ["xdotool", "windowminimize", "--sync", "42"],
        ["xdotool", "windowclose", "--sync", "42"],
    ]


def test_linux_maximize_needs_wmctrl(linux_backend) -> None:
    with mock.patch.object(
        pb.shutil,
        "which",
        side_effect=_which({"xdotool": "/usr/bin/xdotool"}),
    ):
        with pytest.raises(DesktopUnavailableError, match="wmctrl"):
            linux_backend.maximize_window("42")
    with (
        mock.patch.object(
            pb.shutil,
            "which",
            side_effect=_which(
                {"xdotool": "/usr/bin/xdotool", "wmctrl": "/usr/bin/wmctrl"}
            ),
        ),
        mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock,
    ):
        assert linux_backend.maximize_window("42")["status"] == "maximized"
        assert run_mock.call_args[0][0] == [
            "wmctrl",
            "-i",
            "-r",
            "42",
            "-b",
            "add,maximized_vert,maximized_horz",
        ]


def test_linux_input_argv(linux_backend) -> None:
    seen: List[list] = []

    def fake_run(argv, **kwargs):
        seen.append(argv)
        return _cp("")

    with mock.patch.object(pb.subprocess, "run", side_effect=fake_run):
        linux_backend.mouse_move(10, 20)
        linux_backend.mouse_click(10, 20, "right")
        linux_backend.key_press(["ctrl", "l"])
        linux_backend.type_text("hi\nthere")
    assert seen == [
        ["xdotool", "mousemove", "10", "20"],
        ["xdotool", "mousemove", "10", "20"],
        ["xdotool", "click", "3"],
        ["xdotool", "key", "ctrl+l"],
        ["xdotool", "type", "--clearmodifiers", "--", "hi\nthere"],
    ]


def test_linux_tool_failure_is_fail_closed_with_reason(linux_backend) -> None:
    with mock.patch.object(
        pb.subprocess,
        "run",
        return_value=_cp("", returncode=1, stderr="no such window"),
    ):
        with pytest.raises(SystemControlError, match="no such window"):
            linux_backend.focus_window("42")


def test_linux_invalid_window_id_never_reaches_os(linux_backend) -> None:
    with mock.patch.object(pb.subprocess, "run") as run_mock:
        with pytest.raises(SystemControlError, match="invalid"):
            linux_backend.focus_window("42; rm -rf /")
    run_mock.assert_not_called()


def test_linux_screenshot_prefers_import(linux_backend, tmp_path) -> None:
    dest = str(tmp_path / "shot.png")
    with (
        mock.patch.object(
            pb.shutil,
            "which",
            side_effect=_which(
                {
                    "xdotool": "/usr/bin/xdotool",
                    "import": "/usr/bin/import",
                    "scrot": "/usr/bin/scrot",
                }
            ),
        ),
        mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock,
    ):
        result = linux_backend.screenshot(dest)
    assert result["tool"] == "import"
    assert run_mock.call_args[0][0] == ["import", "-window", "root", dest]


def test_linux_screenshot_falls_back_to_scrot(linux_backend, tmp_path) -> None:
    dest = str(tmp_path / "shot.png")
    with (
        mock.patch.object(
            pb.shutil,
            "which",
            side_effect=_which(
                {"xdotool": "/usr/bin/xdotool", "scrot": "/usr/bin/scrot"}
            ),
        ),
        mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock,
    ):
        assert linux_backend.screenshot(dest)["tool"] == "scrot"
        assert run_mock.call_args[0][0] == ["scrot", dest]


def test_linux_screenshot_no_tool_is_unavailable(linux_backend, tmp_path) -> None:
    dest = str(tmp_path / "shot.png")
    with mock.patch.object(
        pb.shutil, "which", side_effect=_which({"xdotool": "/usr/bin/xdotool"})
    ):
        with pytest.raises(DesktopUnavailableError, match="no screenshot tool"):
            linux_backend.screenshot(dest)


def test_linux_launch_app_uses_first_available(linux_backend) -> None:
    with (
        mock.patch.object(
            pb.shutil,
            "which",
            side_effect=_which(
                {"xdotool": "/usr/bin/xdotool", "kcalc": "/usr/bin/kcalc"}
            ),
        ),
        mock.patch.object(pb.subprocess, "Popen") as popen_mock,
    ):
        result = linux_backend.launch_app("calculator")
    assert result["status"] == "launched"
    assert result["command"] == "kcalc"
    assert popen_mock.call_args[0][0] == ["kcalc"]


def test_linux_launch_app_no_executable_is_unavailable(linux_backend) -> None:
    with mock.patch.object(
        pb.shutil, "which", side_effect=_which({"xdotool": "/usr/bin/xdotool"})
    ):
        with pytest.raises(DesktopUnavailableError, match="no known executable"):
            linux_backend.launch_app("calculator")


def test_linux_open_path_uses_xdg_open(linux_backend) -> None:
    with (
        mock.patch.object(
            pb.shutil,
            "which",
            side_effect=_which(
                {"xdotool": "/usr/bin/xdotool", "xdg-open": "/usr/bin/xdg-open"}
            ),
        ),
        mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock,
    ):
        assert linux_backend.open_path("/home/u/doc.txt")["status"] == "opened"
        assert run_mock.call_args[0][0] == ["xdg-open", "/home/u/doc.txt"]


# -- macOS ------------------------------------------------------------------


@pytest.fixture
def macos_backend():
    with mock.patch.object(
        pb.shutil,
        "which",
        side_effect=_which({"osascript": "/usr/bin/osascript"}),
    ):
        yield MacOSBackend()


def test_macos_list_windows_parses_unit_separator(macos_backend) -> None:
    stdout = (
        "101\x1fSafari\x1f1\x1fApple\n"
        "bad line without separators\n"
        "102\x1fTextEdit\x1f2\x1fNotes\n"
    )
    with mock.patch.object(pb.subprocess, "run", return_value=_cp(stdout)) as run_mock:
        windows = macos_backend.list_windows()
    assert windows == [
        {"id": "101:1", "title": "Apple", "process": "Safari", "focused": False},
        {"id": "102:2", "title": "Notes", "process": "TextEdit", "focused": False},
    ]
    assert run_mock.call_args[0][0][:2] == ["osascript", "-e"]


def test_macos_focus_script_uses_axraise(macos_backend) -> None:
    with mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock:
        assert macos_backend.focus_window("101:1")["status"] == "focused"
    script = run_mock.call_args[0][0][2]
    assert "process id 101" in script
    assert 'perform action "AXRaise" of window 1' in script


def test_macos_mouse_needs_cliclick(macos_backend) -> None:
    with mock.patch.object(pb.shutil, "which", side_effect=_which({})):
        with pytest.raises(DesktopUnavailableError, match="cliclick"):
            macos_backend.mouse_move(1, 2)
    with (
        mock.patch.object(
            pb.shutil, "which", side_effect=_which({"cliclick": "/opt/cliclick"})
        ),
        mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock,
    ):
        assert macos_backend.mouse_click(10, 20, "right")["button"] == "right"
        assert run_mock.call_args[0][0] == ["cliclick", "rc:10,20"]


def test_macos_middle_click_is_unavailable(macos_backend) -> None:
    with mock.patch.object(
        pb.shutil, "which", side_effect=_which({"cliclick": "/opt/cliclick"})
    ):
        with pytest.raises(DesktopUnavailableError, match="middle click"):
            macos_backend.mouse_click(1, 2, "middle")


def test_macos_key_press_char_and_named(macos_backend) -> None:
    with mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock:
        macos_backend.key_press(["ctrl", "l"])
        macos_backend.key_press(["Return"])
    scripts = [c[0][0][2] for c in run_mock.call_args_list]
    assert 'keystroke "l" using {control down}' in scripts[0]
    assert "key code 36" in scripts[1]


def test_macos_type_text_escapes_quotes(macos_backend) -> None:
    with mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock:
        macos_backend.type_text('say "hi"')
    script = run_mock.call_args[0][0][2]
    assert 'keystroke "say \\"hi\\""' in script


def test_macos_screenshot_argv(macos_backend, tmp_path) -> None:
    dest = str(tmp_path / "shot.png")
    with (
        mock.patch.object(
            pb.shutil, "which", side_effect=_which({"screencapture": "/usr/sbin/s"})
        ),
        mock.patch.object(pb.subprocess, "run", return_value=_cp("")) as run_mock,
    ):
        assert macos_backend.screenshot(dest)["tool"] == "screencapture"
        assert run_mock.call_args[0][0] == ["screencapture", "-x", dest]


# -- Windows ----------------------------------------------------------------


@pytest.fixture
def windows_backend():
    return WindowsBackend()


def _windows_run(stdout: str = "") -> mock.Mock:
    return mock.patch.object(pb.subprocess, "run", return_value=_cp(stdout))


def _windows_which() -> mock.Mock:
    return mock.patch.object(
        pb.shutil, "which", side_effect=_which({"pwsh": "C:\\pwsh.exe"})
    )


def test_windows_list_windows_parses_tabs(windows_backend) -> None:
    stdout = "1234\t99\tNotepad\n5678\t100\tCalc\n"
    with _windows_which(), _windows_run(stdout):
        windows = windows_backend.list_windows()
    assert windows == [
        {"id": "1234", "title": "Notepad", "process_id": "99", "focused": False},
        {"id": "5678", "title": "Calc", "process_id": "100", "focused": False},
    ]


def test_windows_focus_checks_true_and_passes_hwnd_as_arg(windows_backend) -> None:
    with _windows_which(), _windows_run("True\n") as run_mock:
        assert windows_backend.focus_window("1234")["status"] == "focused"
    argv = run_mock.call_args[0][0]
    assert argv[0] == "C:\\pwsh.exe"
    assert argv[-1] == "1234"  # HWND travels as $args, never interpolated
    assert "SetForegroundWindow" in argv[4]
    with _windows_which(), _windows_run("False\n"):
        with pytest.raises(SystemControlError, match="could not focus"):
            windows_backend.focus_window("1234")


def test_windows_key_press_super_rejected(windows_backend) -> None:
    with pytest.raises(SystemControlError, match="does not support modifier"):
        windows_backend.key_press(["super", "l"])


def test_windows_key_press_sendkeys_arg(windows_backend) -> None:
    with _windows_which(), _windows_run("") as run_mock:
        assert windows_backend.key_press(["ctrl", "s"])["status"] == "key_pressed"
    assert run_mock.call_args[0][0][-1] == "^s"


def test_windows_screenshot_uses_dotnet(windows_backend, tmp_path) -> None:
    dest = str(tmp_path / "shot.png")
    with _windows_which(), _windows_run("") as run_mock:
        result = windows_backend.screenshot(dest)
    assert result["tool"] == "powershell-dotnet"
    argv = run_mock.call_args[0][0]
    assert "CopyFromScreen" in argv[4]
    assert argv[-1] == dest


def test_windows_no_powershell_is_unavailable(windows_backend) -> None:
    with mock.patch.object(pb.shutil, "which", side_effect=_which({})):
        with pytest.raises(DesktopUnavailableError, match="PowerShell"):
            windows_backend.list_windows()


# -- factory -----------------------------------------------------------------


def test_factory_selects_platform_backend() -> None:
    assert isinstance(create_platform_backend("linux"), LinuxX11Backend)
    assert isinstance(create_platform_backend("darwin"), MacOSBackend)
    assert isinstance(create_platform_backend("win32"), WindowsBackend)
    assert isinstance(create_platform_backend("freebsd"), NoOpDesktopBackend)


# -- service: gate + validation still front the new actions ------------------


class _StubBackend:
    """Records new-action calls; returns canned results."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def mouse_move(self, x: int, y: int):
        self.calls.append(("mouse_move", (x, y)))
        return {"status": "moved"}

    def mouse_click(self, x: int, y: int, button: str = "left"):
        self.calls.append(("mouse_click", (x, y, button)))
        return {"status": "clicked"}

    def key_press(self, keys):
        self.calls.append(("key_press", (tuple(keys),)))
        return {"status": "key_pressed"}

    def type_text(self, text: str):
        self.calls.append(("type_text", (text,)))
        return {"status": "typed"}

    def screenshot(self, path: str):
        self.calls.append(("screenshot", (path,)))
        return {"status": "screenshot"}


@pytest.fixture
def new_action_service(tmp_path):
    return SystemControlService(
        backend=_StubBackend(),
        gate=ConfirmationGate(),
        allowed_roots=[tmp_path],
    )


def _approve(service, action, params) -> None:
    service.gate.grant(TOOL_NAME, {"action": action, "params": params})


def test_new_actions_require_approval(new_action_service) -> None:
    with pytest.raises(SystemControlError, match="approval required"):
        new_action_service.execute("mouse_click", {"x": 1, "y": 2})
    assert new_action_service.backend.calls == []


def test_new_actions_dispatch_after_exact_approval(new_action_service) -> None:
    _approve(new_action_service, "mouse_click", {"x": 1, "y": 2, "button": "left"})
    assert (
        new_action_service.execute("mouse_click", {"x": 1, "y": 2})["status"]
        == "clicked"
    )
    _approve(new_action_service, "key_press", {"keys": ["ctrl", "l"]})
    assert (
        new_action_service.execute("key_press", {"keys": ["ctrl", "l"]})["status"]
        == "key_pressed"
    )


def test_new_action_validation(new_action_service, tmp_path) -> None:
    for action, params in [
        ("mouse_move", {"x": -1, "y": 0}),
        ("mouse_move", {"x": True, "y": 0}),
        ("mouse_move", {"x": 100_001, "y": 0}),
        ("mouse_click", {"x": 0, "y": 0, "button": "sideways"}),
        ("key_press", {"keys": []}),
        ("key_press", {"keys": ["a;rm"]}),
        ("key_press", {"keys": "ctrl"}),
        ("type_text", {"text": ""}),
        ("type_text", {"text": "bad\x00text"}),
        ("screenshot", {"path": "/etc/shot.png"}),
    ]:
        with pytest.raises(SystemControlError):
            new_action_service.execute(action, params)
    assert new_action_service.backend.calls == []


def test_screenshot_path_must_be_png(new_action_service, tmp_path) -> None:
    # The service allows the path (inside roots); the backend rejects the
    # non-PNG suffix — surfaced, never silently coerced.
    class PngEnforcingBackend(_StubBackend):
        def screenshot(self, path: str):
            return pb._clean_screenshot_path(path) and {"status": "screenshot"}

    svc = SystemControlService(
        backend=PngEnforcingBackend(),
        gate=ConfirmationGate(),
        allowed_roots=[tmp_path],
    )
    dest = str(tmp_path / "shot.jpg")
    _approve(svc, "screenshot", {"path": dest})
    with pytest.raises(SystemControlError, match="must end in .png"):
        svc.execute("screenshot", {"path": dest})


def test_noop_new_actions_fail_closed() -> None:
    svc = SystemControlService(backend=NoOpDesktopBackend(), gate=ConfirmationGate())
    for action, params in [
        ("mouse_move", {"x": 1, "y": 2}),
        ("mouse_click", {"x": 1, "y": 2, "button": "left"}),
        ("key_press", {"keys": ["a"]}),
        ("type_text", {"text": "hi"}),
        ("screenshot", {"path": "/tmp/shot.png"}),
    ]:
        _approve(svc, action, params)
        with pytest.raises(DesktopUnavailableError):
            svc.execute(action, params)


def test_routes_default_backend_is_platform() -> None:
    from openjarvis.server import desktop_routes

    backend = desktop_routes._get_backend(None)
    assert isinstance(backend, (LinuxX11Backend, MacOSBackend, WindowsBackend))
