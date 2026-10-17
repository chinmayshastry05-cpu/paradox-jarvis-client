"""Desktop permission checks for the first-run setup wizard.

Report-only: every check returns a result, nothing here blocks setup.
Checks are pure functions of the environment so tests can drive them
with a fake ``which`` and a fake environment mapping.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionCheck:
    """One desktop permission check result."""

    name: str
    ok: bool
    detail: str


def _tool_check(
    name: str, tools: tuple[str, ...], *, which=shutil.which
) -> PermissionCheck:
    found = next((t for t in tools if which(t)), None)
    if found:
        return PermissionCheck(name, True, f"found {found}")
    return PermissionCheck(name, False, f"none of {', '.join(tools)} on PATH")


def check_desktop_permissions(
    *,
    env: dict[str, str] | None = None,
    which=shutil.which,
) -> list[PermissionCheck]:
    """Check desktop automation prerequisites on this machine.

    Display server, X11/Wayland automation tools, and a screenshot tool.
    A missing tool is a warning, not an error: the wizard reports it and
    setup continues.
    """
    environ = env if env is not None else dict(os.environ)
    checks: list[PermissionCheck] = []
    display = environ.get("DISPLAY", "")
    wayland = environ.get("WAYLAND_DISPLAY", "")
    if display or wayland:
        server = "Wayland" if wayland else "X11"
        checks.append(PermissionCheck("display", True, f"{server} session detected"))
    else:
        checks.append(
            PermissionCheck(
                "display",
                False,
                "no DISPLAY or WAYLAND_DISPLAY; desktop control needs a GUI session",
            )
        )
    if wayland:
        checks.append(
            _tool_check("wayland automation", ("ydotool", "wtype"), which=which)
        )
    else:
        checks.append(_tool_check("X11 automation", ("xdotool",), which=which))
    checks.append(_tool_check("screenshot", ("grim", "scrot", "import"), which=which))
    return checks
