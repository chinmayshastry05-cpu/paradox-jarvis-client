"""Tests for the Nexa SDK shim's delivery redaction (Phase 1 remainder).

The real ``nexaai`` package is not installed in CI, so these tests inject
a stub SDK into ``sys.modules`` before importing the shim — the same
approach as ``tests/engine/test_apple_fm_shim.py``. They prove the
shim's SSE stream goes through ``redact_sse_stream`` and its
non-streaming response through ``redact_text``: a secret fully inside
one streamed chunk / one response must never reach the client raw.
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

SECRET = "sk-" + "A" * 24


class _FakeLLM:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    def generate(self, prompt: str, max_tokens: int = 1024):  # noqa: ANN202
        # Streaming path iterates the return value; non-streaming joins
        # a list. One list serves both.
        return list(self._tokens)


def _load_shim(tokens: list[str]):
    """Import a fresh copy of the shim against a stub ``nexaai``."""
    sdk = types.ModuleType("nexaai")
    sdk.LLM = lambda: _FakeLLM(tokens)  # type: ignore[attr-defined]
    sys.modules["nexaai"] = sdk
    sys.modules.pop("openjarvis.engine.nexa_shim", None)
    mod = importlib.import_module("openjarvis.engine.nexa_shim")
    mod = importlib.reload(mod)
    return mod


@pytest.fixture
def shim_with_secret():
    mod = _load_shim(["hello ", SECRET, " done"])
    yield mod
    sys.modules.pop("openjarvis.engine.nexa_shim", None)
    sys.modules.pop("nexaai", None)


class TestNexaShimDeliveryRedaction:
    def test_stream_redacts_secret_in_chunk(self, shim_with_secret):
        client = TestClient(shim_with_secret.app)
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
        ) as resp:
            assert resp.status_code == 200
            body = "".join(resp.iter_text())
        assert SECRET not in body
        assert "[REDACTED:" in body
        # Clean tokens and the stream terminator still flow through.
        assert "hello " in body
        assert "data: [DONE]" in body

    def test_non_streaming_redacts_secret(self, shim_with_secret):
        client = TestClient(shim_with_secret.app)
        resp = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
        )
        assert resp.status_code == 200
        content = resp.json()["choices"][0]["message"]["content"]
        assert SECRET not in content
        assert "[REDACTED:" in content
        assert "hello " in content
