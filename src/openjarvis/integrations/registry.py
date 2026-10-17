"""License / integration registry for Paradox Jarvis Ultra (Phase 2).

Data mirror of ``docs/paradox-jarvis-ultra-matrix.md`` §1: every candidate
repo, its *verified* licence, and how it may integrate. The rule is uniform:

**nothing is copied into the fork.** Permissive licences (MIT/Apache-2.0)
are integrated via resolver / external process / MCP stdio only; AGPL,
source-available, unverified-license, and separate-project code is never
copied or linked in-process. A plugin-plan entry here does NOT mean the
feature is implemented — it records the only permitted integration shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


class LicenseBoundaryError(RuntimeError):
    """Raised when code tries to cross a licence boundary (copy/link)."""


# Statuses: "base" (fork base), "guidance", "list", "unrelated",
# "reference" (read-only reference, do not copy), "separate" (separate
# project, do not copy), "resolver" (skill resolver, no vendoring),
# "external-process" (side-by-side / subprocess, never in-process),
# "external-mcp" (MCP stdio server), "external-model" (weights + GPU,
# not integrated), "external-skill-gated" (external skill, gated),
# "blocked-agpl", "blocked-source-available", "blocked-unverified",
# "blocked-paid", "unverified".
BLOCKED_STATUSES = frozenset(
    {
        "blocked-agpl",
        "blocked-source-available",
        "blocked-unverified",
        "blocked-paid",
        "separate",
    }
)


@dataclass(frozen=True)
class IntegrationDescriptor:
    """One matrix entry: licence + permitted integration shape."""

    key: str
    repo_url: str
    license: str  # verified licence string from the matrix
    status: str
    integration: str  # how it may integrate, if at all
    copy_policy: str  # "blocked: <reason>" or "avoid: <interface to use>"


REGISTRY: Dict[str, IntegrationDescriptor] = {
    "openjarvis": IntegrationDescriptor(
        "openjarvis",
        "https://github.com/open-jarvis/openjarvis",
        "Apache-2.0",
        "base",
        "Fork base; keep LICENSE + attribution + history.",
        "n/a: base of the fork",
    ),
    "paradox-jarvis-ultra": IntegrationDescriptor(
        "paradox-jarvis-ultra",
        "https://github.com/chinmayshastry05-cpu/paradox-jarvis-ultra",
        "Apache-2.0 (inherited)",
        "base",
        "Private personal fork. Do not strip upstream attribution.",
        "n/a: this fork",
    ),
    "cactus": IntegrationDescriptor(
        "cactus",
        "https://github.com/cactus-compute/cactus",
        "Source-available, NOT OSI open source",
        "blocked-source-available",
        "No copying. A Cactus integration must be separate, explicitly "
        "licensed, with NOTICE + LICENSE intact — not assumed.",
        "blocked: source-available, not OSI open source",
    ),
    "open-higgsfield-ai": IntegrationDescriptor(
        "open-higgsfield-ai",
        "https://github.com/Autom8AI/Open-Higgsfield-AI",
        "UNVERIFIED (description claims MIT, no LICENSE file detected)",
        "blocked-unverified",
        "None. Do NOT assume free generation; backends are paid/key-gated.",
        "blocked: licence unverified",
    ),
    "ponytail": IntegrationDescriptor(
        "ponytail",
        "https://github.com/dietrichgebert/ponytail",
        "MIT",
        "guidance",
        "Prompt-only coding guidance, followed as a working rule.",
        "n/a: guidance, not code",
    ),
    "hermes-gadget-sdk": IntegrationDescriptor(
        "hermes-gadget-sdk",
        "https://github.com/Adolanium/hermes-gadget-sdk",
        "MIT",
        "external-process",
        "External Hermes-ecosystem device SDK (ESP32/Linux client). "
        "Do NOT vendor. No device integration implemented.",
        "avoid: external SDK, never vendored",
    ),
    "herald-os": IntegrationDescriptor(
        "herald-os",
        "https://github.com/iamlukethedev/Herald-OS",
        "MIT",
        "unrelated",
        "None — an agent-native OS, out of scope for Jarvis.",
        "n/a: unrelated domain",
    ),
    "octop": IntegrationDescriptor(
        "octop",
        "https://github.com/TencentCloud/Octop",
        "MIT",
        "reference",
        "Reference only — competing self-hosted assistant. Do NOT copy.",
        "blocked: reference only per matrix policy",
    ),
    "voxcpm": IntegrationDescriptor(
        "voxcpm",
        "https://github.com/OpenBMB/VoxCPM",
        "Apache-2.0",
        "external-model",
        "External TTS model only (if ever). Weights + GPU required; "
        "model terms unchecked. NOT integrated or tested.",
        "avoid: external model, never vendored",
    ),
    "cua": IntegrationDescriptor(
        "cua",
        "https://github.com/trycua/cua",
        "MIT",
        "external-process",
        "External computer-use plugin only (operator-supplied driver "
        "command), opt-in + per-action approval. Never vendored. "
        "Cua Spaces cloud NOT proposed.",
        "avoid: external plugin, never vendored",
    ),
    "rea": IntegrationDescriptor(
        "rea",
        "https://github.com/morluto/rea",
        "MIT",
        "unrelated",
        "None — reverse-engineering agent tool, unrelated domain.",
        "n/a: unrelated domain",
    ),
    "awesome-free-llm-apis": IntegrationDescriptor(
        "awesome-free-llm-apis",
        "https://github.com/mnfst/awesome-free-llm-apis",
        "CC0-1.0 (list)",
        "list",
        "Reference list only. Listed services have their own terms/keys; "
        '"free" is NOT verified.',
        "n/a: list, not code",
    ),
    "oh-my-hermes": IntegrationDescriptor(
        "oh-my-hermes",
        "https://github.com/rlaope/oh-my-hermes",
        "MIT",
        "external-process",
        "External Hermes plugin only (operator-supplied command). "
        "Do NOT vendor. No plugin integration verified.",
        "avoid: external plugin, never vendored",
    ),
    "geo-sleuth": IntegrationDescriptor(
        "geo-sleuth",
        "https://github.com/Oldcircle/geo-sleuth",
        "MIT",
        "external-skill-gated",
        "External skill only, gated: opt-in + per-run approval + explicit "
        "privacy acknowledgement. Privacy-sensitive. Do NOT vendor.",
        "avoid: external gated skill, never vendored",
    ),
    "opendroid": IntegrationDescriptor(
        "opendroid",
        "https://github.com/yashab-cyber/opendroid",
        "UNVERIFIED — no license detected",
        "blocked-unverified",
        "None. No license = no reuse permission. No Android control.",
        "blocked: licence unverified",
    ),
    "gods-eye-view": IntegrationDescriptor(
        "gods-eye-view",
        "https://github.com/bilawalsidhu/gods-eye-view",
        "UNVERIFIED — no license detected",
        "blocked-unverified",
        "None. Unlicensed visualization demo, unrelated domain.",
        "blocked: licence unverified",
    ),
    "openmontage": IntegrationDescriptor(
        "openmontage",
        "https://github.com/calesthio/OpenMontage",
        "AGPL-3.0",
        "blocked-agpl",
        "None until an explicit licensing decision. Do NOT copy or link "
        "into the Apache-2.0 fork.",
        "blocked: AGPL-3.0 — no copying/linking without a licensing decision",
    ),
    "open-generative-ai": IntegrationDescriptor(
        "open-generative-ai",
        "https://github.com/Anil-matcha/Open-Generative-AI",
        "MIT (GitHub API)",
        "blocked-paid",
        "None. Backends are paid/key-gated MuAPI frontends; 'no content "
        "filters / unrestricted' is a safety flag, not a feature.",
        "blocked: paid/key-gated backends, free generation NOT verified",
    ),
    "hermes-agent": IntegrationDescriptor(
        "hermes-agent",
        "https://github.com/NousResearch/hermes-agent",
        "MIT",
        "resolver",
        "Resolver (HermesResolver) + eval subprocess backend + "
        "side-by-side gateway process. Do NOT copy Hermes source.",
        "avoid: resolver / external process, never copied",
    ),
    "claude-code-router": IntegrationDescriptor(
        "claude-code-router",
        "https://github.com/musistudio/claude-code-router",
        "MIT",
        "external-process",
        "External / reference only (operator-supplied command). "
        "Do NOT vendor. No router integration verified.",
        "avoid: external process, never vendored",
    ),
    "agentic-browser-bridge": IntegrationDescriptor(
        "agentic-browser-bridge",
        "https://github.com/chinmayshastry05-cpu/agentic-browser-bridge",
        "MIT",
        "external-mcp",
        "External MCP stdio server (bridge_server_entry). Never imported "
        "in-process. Keep MIT notice.",
        "avoid: external MCP stdio, never imported in-process",
    ),
    "studyreels": IntegrationDescriptor(
        "studyreels",
        "https://github.com/chinmayshastry05-cpu/studyreels",
        "UNVERIFIED — no license detected",
        "separate",
        "None. Separate, unlicensed project. Do NOT copy.",
        "blocked: separate project, licence unverified",
    ),
    "tally-llm": IntegrationDescriptor(
        "tally-llm",
        "https://github.com/chinmayshastry05-cpu/tally-llm",
        "UNVERIFIED — no license detected",
        "separate",
        "None. Separate research prototype. Tally work stays separate.",
        "blocked: separate project, licence unverified",
    ),
    "clientops-ai-demo": IntegrationDescriptor(
        "clientops-ai-demo",
        "https://github.com/chinmayshastry05-cpu/clientops-ai-demo",
        "UNVERIFIED — no license detected",
        "separate",
        "None. Separate triage-assistant demo. Do NOT copy.",
        "blocked: separate project, licence unverified",
    ),
    "risklabs": IntegrationDescriptor(
        "risklabs",
        "https://github.com/chinmayshastry05-cpu/risklabs",
        "UNVERIFIED — no license detected",
        "separate",
        "None. Separate college academic project. Do NOT copy.",
        "blocked: separate project, licence unverified",
    ),
    "first-role-radar": IntegrationDescriptor(
        "first-role-radar",
        "https://github.com/ChinmaysTG/first-role-radar",
        "UNVERIFIED — no license detected",
        "separate",
        "None. Separate job-research tool (SerpApi, key-gated).",
        "blocked: separate project, licence unverified",
    ),
    "openclaw-skills": IntegrationDescriptor(
        "openclaw-skills",
        "https://github.com/openclaw/skills",
        "UNVERIFIED",
        "resolver",
        "Resolver may fetch at runtime; do NOT vendor skill text. "
        "Per-skill licences must be checked before reuse.",
        "avoid: runtime resolver, never vendored",
    ),
    "dependency-licences": IntegrationDescriptor(
        "dependency-licences",
        "",
        "UNVERIFIED",
        "unverified",
        "Do NOT assert a dependency's licence. Check each package's own "
        "LICENSE before redistributing or vendoring.",
        "blocked: licence unverified — check per-package",
    ),
}


def get(key: str) -> IntegrationDescriptor:
    """Return the descriptor for *key* or raise KeyError."""
    return REGISTRY[key]


def all_descriptors() -> List[IntegrationDescriptor]:
    """All registry entries, sorted by key."""
    return [REGISTRY[k] for k in sorted(REGISTRY)]


def blocked_entries() -> List[IntegrationDescriptor]:
    """Entries whose code must not be copied or linked in."""
    return [d for d in all_descriptors() if d.status in BLOCKED_STATUSES]


def ensure_copy_blocked(key: str) -> None:
    """Raise :class:`LicenseBoundaryError` if copying *key* is blocked.

    Permissive-licence entries do not raise: their copy policy is
    "avoid" (use the resolver / external interface), which is a policy
    statement, not a licence prohibition — enforced by never having a
    copy path, not by this guard.
    """
    descriptor = get(key)
    if descriptor.copy_policy.startswith("blocked:"):
        raise LicenseBoundaryError(
            f"Copying {key} ({descriptor.repo_url}) is blocked: "
            f"{descriptor.copy_policy}"
        )


__all__ = [
    "BLOCKED_STATUSES",
    "IntegrationDescriptor",
    "LicenseBoundaryError",
    "REGISTRY",
    "all_descriptors",
    "blocked_entries",
    "ensure_copy_blocked",
    "get",
]
