"""Live smoke test: real free TTS synthesis.

STATUS: harness re-registers the requested backend because conftest
clears TTSRegistry before every test; a live run is the remaining step.
Nothing here is a claimed live result until the test passes for real.

Default backend is Kokoro: fully local, open-source, zero spend, and
keyless — no API key exists to provide. Any API key a cloud backend
needs comes from that backend's own environment configuration only;
this harness never reads, passes, or logs any key.

Env vars:
- ``TTS_SMOKE_BACKEND`` — backend id, default ``"kokoro"``.
- ``TTS_SMOKE_TEXT`` — phrase to synthesize (default: short greeting).
- ``TTS_SMOKE_VOICE`` — voice id; empty means the backend default.

Skip (fail-closed) conditions:
- Requested backend unavailable / not installed -> SKIP, not failure.
- Synthesis failing only because a dependency is not installed -> SKIP.

Run::

    pytest tests/smoke/test_free_tts.py -m live -v

NOTE: the first Kokoro run downloads model weights; that is a local,
free, one-time download, not a spend.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

from openjarvis.core.registry import TTSRegistry
from openjarvis.speech._tts_discovery import get_tts_backend

_DEFAULT_TEXT = "Hello, this is a Jarvis smoke test."

# conftest's autouse _clean_registries clears TTSRegistry before every
# test, and import-time @TTSRegistry.register() does not re-run for an
# already-imported module — so re-register the requested backend here,
# the same way tests/speech/test_tts_backends.py does.
_BACKEND_CLASSES = {
    "kokoro": ("openjarvis.speech.kokoro_tts", "KokoroTTSBackend"),
    "openai_tts": ("openjarvis.speech.openai_tts", "OpenAITTSBackend"),
    "cartesia": ("openjarvis.speech.cartesia_tts", "CartesiaTTSBackend"),
}


@pytest.mark.live
@pytest.mark.slow
def test_free_tts_synthesizes_audio(tmp_path: Path) -> None:
    backend_id = os.environ.get("TTS_SMOKE_BACKEND", "kokoro") or "kokoro"
    text = os.environ.get("TTS_SMOKE_TEXT", _DEFAULT_TEXT) or _DEFAULT_TEXT
    voice_id = os.environ.get("TTS_SMOKE_VOICE", "")

    module_name, class_name = _BACKEND_CLASSES.get(backend_id, (None, None))
    if module_name is not None:
        backend_cls = getattr(importlib.import_module(module_name), class_name)
        TTSRegistry.register_value(backend_id, backend_cls)

    backend = get_tts_backend(backend_id)
    if backend is None:
        pytest.skip(
            f"TTS backend {backend_id!r} unavailable "
            "(not installed / failed health check)"
        )

    kwargs = {"output_format": "wav"}
    if voice_id:
        kwargs["voice_id"] = voice_id
    try:
        result = backend.synthesize(text, **kwargs)
    except RuntimeError as exc:
        if "not installed" in str(exc):
            pytest.skip(f"TTS dependency not installed: {exc}")
        raise

    assert result.audio, "TTS produced no audio bytes"
    assert result.duration_seconds > 0, "TTS reported zero duration"
    if result.format == "wav":
        assert result.audio[:4] == b"RIFF", "WAV output missing RIFF header"

    out_path = tmp_path / "smoke.wav"
    result.save(out_path)
    assert out_path.stat().st_size == len(result.audio)
