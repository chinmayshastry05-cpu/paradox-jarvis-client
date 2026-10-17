"""Phase 6 desktop GUI: system control + desktop settings."""

from openjarvis.desktop.platform_backend import (
    LinuxX11Backend,
    MacOSBackend,
    WindowsBackend,
    create_platform_backend,
)
from openjarvis.desktop.settings import DesktopSettings, load_settings, save_settings
from openjarvis.desktop.system_control import (
    SystemControlService,
    describe_actions,
)

__all__ = [
    "DesktopSettings",
    "LinuxX11Backend",
    "MacOSBackend",
    "SystemControlService",
    "WindowsBackend",
    "create_platform_backend",
    "describe_actions",
    "load_settings",
    "save_settings",
]
