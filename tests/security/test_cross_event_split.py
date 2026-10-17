"""Cross-event secret split (Phase 1).

``redact_sse_stream`` wraps an SSE generator and redacts every frame
before emission. Two cases:

* Plain-text (non-JSON) data: one shared StreamingRedactor carries
  state across frames, so a secret split across two plain-text frames
  IS caught.
* JSON data: each frame is redacted whole-payload. A secret split
  across two discrete JSON events is NOT reconstructed — the JSON
  framing breaks the pattern. That is the documented hard boundary
  (see ``delivery_redaction`` module docstring); the last test proves
  it so the limitation is pinned, not assumed away.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from openjarvis.security.delivery_redaction import redact_sse_stream


async def _collect(chunks):
    async def _gen():
        for c in chunks:
            yield c

    return [c async for c in redact_sse_stream(_gen())]


def _run(chunks):
    return asyncio.run(_collect(chunks))


def test_plain_text_split_across_frames_is_caught():
    # sk- + 30 chars split across two plain-text frames. The shared
    # redactor holds the suspicious suffix across the frame boundary.
    key = "sk-" + "A" * 30
    out = _run(
        [
            f"data: the key is {key[:10]}\n\n",
            f"data: {key[10:]} end\n\n",
        ]
    )
    joined = "".join(out)
    assert key not in joined
    assert "sk-" not in joined


def test_plain_text_assignment_split_across_frames_is_caught():
    out = _run(
        [
            'data: password = "sec\n\n',
            'data: ret1234" done\n\n',
        ]
    )
    joined = "".join(out)
    # The secret VALUE must be gone. (The placeholder itself is named
    # "[REDACTED:password_assignment]", so "password" may appear.)
    assert "secret1234" not in joined
    assert "[REDACTED" in joined


def test_json_frame_fully_inside_is_redacted():
    key = "sk-" + "B" * 30
    payload = json.dumps({"text": f"leaked {key} here"})
    out = _run([f"data: {payload}\n\n"])
    joined = "".join(out)
    assert key not in joined
    assert "sk-" not in joined


def test_json_clean_frame_bytes_preserved():
    payload = json.dumps({"text": "hello world", "n": 1})
    out = _run([f"data: {payload}\n\n"])
    assert out == [f"data: {payload}\n\n"]


def test_done_sentinel_passes_through():
    out = _run(["data: [DONE]\n\n"])
    assert out == ["data: [DONE]\n\n"]


def test_event_lines_preserved():
    payload = json.dumps({"tool": "x", "arguments": "{}"})
    out = _run([f"event: tool_call_start\ndata: {payload}\n\n"])
    assert out == [f"event: tool_call_start\ndata: {payload}\n\n"]


def test_frame_split_across_chunks_reassembled():
    key = "sk-" + "C" * 30
    payload = json.dumps({"text": key})
    frame = f"data: {payload}\n\n"
    # Split the frame mid-JSON across two chunks.
    out = _run([frame[:10], frame[10:]])
    joined = "".join(out)
    assert key not in joined


def test_cross_event_json_split_is_a_documented_boundary():
    """HARD BOUNDARY: a secret split across two JSON events is NOT caught.

    Frame 1 ends with the bare literal ``password`` (not a secret on
    its own); frame 2 starts with the value. Neither JSON payload
    matches a pattern, so both pass through and a client concatenating
    the text fields reconstructs the secret. This test pins the
    limitation — it must NOT be "fixed" by weakening the assertion.
    The mitigation is per-frame whole-payload redaction (a secret
    fully inside one frame is always caught) plus never splitting one
    logical payload across discrete JSON events.
    """
    f1 = json.dumps({"text": "password"})
    f2 = json.dumps({"text": '= "secret1234"'})
    out = _run([f"data: {f1}\n\n", f"data: {f2}\n\n"])
    joined = "".join(out)
    # The boundary: both halves pass through (neither matches alone).
    assert "password" in joined
    assert "secret1234" in joined


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
