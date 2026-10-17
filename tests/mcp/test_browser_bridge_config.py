"""Tests for bridge MCP config registration (Phase 2 wiring)."""

from openjarvis.mcp.browser_bridge import (
    BRIDGE_DEFAULT_ALLOWED_ORIGINS,
    BRIDGE_DEFAULT_INCLUDE_TOOLS,
    BRIDGE_SERVER_NAME,
    bridge_server_entry,
    register_bridge_server,
)


def test_register_adds_bridge_entry():
    config = {"tools": {"mcp": {"servers": []}}}
    updated = register_bridge_server(config, bridge_path="/tmp/fake-bridge")
    assert config["tools"]["mcp"]["servers"] == []  # input not mutated
    servers = updated["tools"]["mcp"]["servers"]
    assert len(servers) == 1
    entry = servers[0]
    assert entry["name"] == BRIDGE_SERVER_NAME
    assert entry["command"] == "node"
    assert entry["args"][0] == "/tmp/fake-bridge/dist/src/index.js"
    assert entry["include_tools"] == sorted(BRIDGE_DEFAULT_INCLUDE_TOOLS)
    assert entry["allowed_origins"] == list(BRIDGE_DEFAULT_ALLOWED_ORIGINS)


def test_register_creates_missing_levels():
    updated = register_bridge_server({})
    assert updated["tools"]["mcp"]["servers"][0]["name"] == BRIDGE_SERVER_NAME


def test_register_preserves_existing_servers_and_entry():
    existing = {"name": "other", "command": "x"}
    config = {"tools": {"mcp": {"servers": [existing]}}}
    updated = register_bridge_server(config, bridge_path="/tmp/b")
    assert updated["tools"]["mcp"]["servers"][0] == existing
    assert updated["tools"]["mcp"]["servers"][1]["name"] == BRIDGE_SERVER_NAME


def test_register_does_not_duplicate_existing_bridge():
    mine = bridge_server_entry("/tmp/mine")
    config = {"tools": {"mcp": {"servers": [mine]}}}
    updated = register_bridge_server(config, bridge_path="/tmp/other")
    servers = updated["tools"]["mcp"]["servers"]
    assert len(servers) == 1
    assert servers[0]["args"][0] == "/tmp/mine/dist/src/index.js"  # operator wins
