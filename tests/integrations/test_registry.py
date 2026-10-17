"""Tests for the Phase 2 licence/integration registry."""

import pytest

from openjarvis.integrations import registry
from openjarvis.integrations.registry import (
    LicenseBoundaryError,
    ensure_copy_blocked,
)

# The 25 delivered-inventory entries from the matrix must all be present.
DELIVERED_KEYS = {
    "cactus",
    "open-higgsfield-ai",
    "ponytail",
    "hermes-gadget-sdk",
    "herald-os",
    "octop",
    "voxcpm",
    "cua",
    "rea",
    "awesome-free-llm-apis",
    "oh-my-hermes",
    "geo-sleuth",
    "opendroid",
    "gods-eye-view",
    "openmontage",
    "open-generative-ai",
    "hermes-agent",
    "claude-code-router",
    "agentic-browser-bridge",
    "studyreels",
    "tally-llm",
    "clientops-ai-demo",
    "risklabs",
    "first-role-radar",
    "openclaw-skills",
}


def test_all_delivered_entries_present():
    assert DELIVERED_KEYS <= set(registry.REGISTRY)


def test_no_entry_claims_copy_integration():
    for key, desc in registry.REGISTRY.items():
        assert desc.copy_policy.startswith(("blocked:", "avoid:", "n/a:")), key
        assert (
            "copy" not in desc.integration.lower() or "not" in desc.integration.lower()
        ), key


def test_blocked_entries_raise():
    for key in [
        "openmontage",  # AGPL-3.0
        "cactus",  # source-available
        "opendroid",  # unverified
        "gods-eye-view",
        "studyreels",
        "tally-llm",
        "clientops-ai-demo",
        "risklabs",
        "first-role-radar",
        "open-higgsfield-ai",
        "open-generative-ai",
    ]:
        with pytest.raises(LicenseBoundaryError):
            ensure_copy_blocked(key)


def test_permissive_entries_use_interface_not_copy():
    # Hermes / bridge / Cua are permissive but the policy is still
    # "avoid copying — use the interface".
    for key in ["hermes-agent", "agentic-browser-bridge", "cua", "oh-my-hermes"]:
        ensure_copy_blocked(key)  # must NOT raise
        assert registry.get(key).copy_policy.startswith("avoid:")


def test_blocked_entries_cover_agpl_and_unverified():
    blocked = {d.key for d in registry.blocked_entries()}
    assert {"openmontage", "cactus", "opendroid", "studyreels"} <= blocked
    assert "hermes-agent" not in blocked
    assert "agentic-browser-bridge" not in blocked


def test_unknown_key_raises_keyerror():
    with pytest.raises(KeyError):
        registry.get("no-such-repo")
