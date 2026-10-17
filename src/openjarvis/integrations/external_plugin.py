"""External-plugin runner (Phase 2).

License-clean integrations run as *separate processes*, never in-process
imports: Hermes gateway, Cua driver, Claude Code Router, Oh My Hermes,
Geo Sleuth. This module is the single enforcement point for that shape:

* Disabled by default — the caller must pass ``enabled=True`` (opt-in).
* No shell — ``shell=False`` always; command is an argv list.
* Consequential runs need an operator confirmer callback; without one
  the run is refused fail-closed.
* Geo Sleuth is privacy-sensitive: it additionally needs an explicit
  ``privacy_ack=True`` (the operator has reviewed the privacy impact).
* Long-running plugins (Hermes gateway) are NOT run one-shot here — use
  :mod:`openjarvis.integrations.hermes_gateway` lifecycle supervision.
* Child environment is scrubbed to an allowlist (no secrets leak through).
* Stdout/stderr are redacted before being returned.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from openjarvis.security.delivery_redaction import redact_text

logger = logging.getLogger(__name__)

# Env vars a child plugin process may see. Everything else — including
# any credential-bearing variable — is stripped.
ENV_ALLOWLIST = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR"})


@dataclass(frozen=True)
class ExternalPluginSpec:
    """One external plugin: how to launch it, and what it needs."""

    key: str
    description: str
    license: str
    # Default argv. None = the operator must supply the command; we do
    # not invent a CLI for a tool we have not verified.
    command: Optional[tuple[str, ...]] = None
    command_hint: str = ""
    requires_privacy_ack: bool = False
    long_running: bool = False


PLUGIN_SPECS: dict[str, ExternalPluginSpec] = {
    # `hermes gateway` is Hermes Agent's documented gateway entrypoint
    # (see its README: "hermes gateway # Start the messaging gateway").
    "hermes-gateway": ExternalPluginSpec(
        key="hermes-gateway",
        description="Hermes Agent messaging gateway (side-by-side process).",
        license="MIT",
        command=("hermes", "gateway"),
        long_running=True,
    ),
    "cua-driver": ExternalPluginSpec(
        key="cua-driver",
        description="Cua computer-use driver (external plugin only).",
        license="MIT",
        command_hint="Operator supplies the Cua driver command.",
    ),
    "claude-code-router": ExternalPluginSpec(
        key="claude-code-router",
        description="Claude Code Router control plane (external only).",
        license="MIT",
        command_hint="Operator supplies the router command.",
    ),
    "oh-my-hermes": ExternalPluginSpec(
        key="oh-my-hermes",
        description="Oh My Hermes plugin (external only).",
        license="MIT",
        command_hint="Operator supplies the plugin command.",
    ),
    "geo-sleuth": ExternalPluginSpec(
        key="geo-sleuth",
        description="Geo Sleuth photo-geolocation skill (privacy-sensitive).",
        license="MIT",
        command_hint="Operator supplies the skill command.",
        requires_privacy_ack=True,
    ),
    "hermes-gadget-sdk": ExternalPluginSpec(
        key="hermes-gadget-sdk",
        description="Hermes Gadget SDK device client (needs hardware).",
        license="MIT",
        command_hint="Operator supplies the device-client command.",
    ),
}


@dataclass
class PluginResult:
    """Outcome of one external-plugin run."""

    ok: bool
    returncode: Optional[int] = None
    stdout: str = ""  # redacted
    stderr: str = ""  # redacted
    error: str = ""


def scrubbed_env() -> dict[str, str]:
    """Child-process environment: allowlist only, no secrets."""
    return {k: v for k, v in os.environ.items() if k in ENV_ALLOWLIST}


def run_plugin(
    key: str,
    args: Sequence[str] = (),
    *,
    command: Optional[Sequence[str]] = None,
    enabled: bool = False,
    confirm: Optional[Callable[[str], bool]] = None,
    privacy_ack: bool = False,
    timeout_seconds: float = 60.0,
) -> PluginResult:
    """Run an external plugin as a one-shot subprocess.

    Refuses (``ok=False``) when: the plugin is unknown, not enabled,
    long-running, privacy acknowledgement is missing, no confirmer is
    supplied, or the operator declines. Never uses a shell.
    """
    spec = PLUGIN_SPECS.get(key)
    if spec is None:
        return PluginResult(ok=False, error=f"unknown external plugin: {key}")
    if not enabled:
        return PluginResult(
            ok=False, error=f"plugin {key} is disabled (opt-in required)"
        )
    if spec.long_running:
        return PluginResult(
            ok=False,
            error=f"plugin {key} is long-running; use SideBySideProcess",
        )
    if spec.requires_privacy_ack and not privacy_ack:
        return PluginResult(
            ok=False,
            error=f"plugin {key} requires explicit privacy acknowledgement",
        )
    if confirm is None:
        return PluginResult(
            ok=False, error=f"plugin {key} requires an operator confirmer"
        )

    base = list(command) if command is not None else list(spec.command or ())
    if not base:
        return PluginResult(
            ok=False,
            error=f"plugin {key} has no command configured: {spec.command_hint}",
        )
    argv = base + [str(a) for a in args]
    if not confirm(f"Run external plugin {key}: {' '.join(argv)}?"):
        return PluginResult(ok=False, error=f"operator declined plugin {key}")

    try:
        completed = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=scrubbed_env(),
        )
    except subprocess.TimeoutExpired:
        return PluginResult(
            ok=False, error=f"plugin {key} timed out after {timeout_seconds}s"
        )
    except (OSError, ValueError) as exc:
        return PluginResult(ok=False, error=f"plugin {key} failed to start: {exc}")

    return PluginResult(
        ok=completed.returncode == 0,
        returncode=completed.returncode,
        stdout=redact_text(completed.stdout or ""),
        stderr=redact_text(completed.stderr or ""),
        error="" if completed.returncode == 0 else f"exit {completed.returncode}",
    )


__all__ = [
    "ENV_ALLOWLIST",
    "ExternalPluginSpec",
    "PLUGIN_SPECS",
    "PluginResult",
    "run_plugin",
    "scrubbed_env",
]
