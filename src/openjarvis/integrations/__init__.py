"""License-clean external integrations (Phase 2).

Nothing here copies or vendors another project's code. Integrations run
via resolver / external process / MCP stdio only; see ``registry.py`` for
the licence boundary of every candidate repo.
"""

from openjarvis.integrations.external_plugin import (
    PLUGIN_SPECS,
    PluginResult,
    run_plugin,
)
from openjarvis.integrations.hermes_gateway import HermesGateway, SideBySideProcess
from openjarvis.integrations.registry import (
    REGISTRY,
    LicenseBoundaryError,
    blocked_entries,
    ensure_copy_blocked,
    get,
)

__all__ = [
    "REGISTRY",
    "PLUGIN_SPECS",
    "LicenseBoundaryError",
    "HermesGateway",
    "PluginResult",
    "SideBySideProcess",
    "blocked_entries",
    "ensure_copy_blocked",
    "get",
    "run_plugin",
]
