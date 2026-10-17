"""Phase 3 voice tuning: Kannada / Hindi / English / Sanskrit.

All tests are unit/mocked: no microphone, speaker, model, or network is
touched. Fixture strings are CONSTRUCTED (native-script fragments plus
English words); tests assert detection / routing / normalisation behaviour,
never translation or TTS quality. Real-audio, real-model, and real-device
behaviour remain explicitly unverified gaps.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from openjarvis.cli._voice_chat import VoiceSession, speak
from openjarvis.speech.voice_state import split_sentences
from openjarvis.speech.voice_tuning import (
    detect_language,
    normalize_for_tts,
    normalize_language_code,
    resolve_tts_voice,
    segment_by_language,
)

# ---------------------------------------------------------------- detection


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ನಾಳೆ ಬೆಂಗಳೂರಿಗೆ ಹೋಗುತ್ತೇನೆ", "kn"),
        ("आज का काम है", "hi"),
        ("मैं घर जा रहा हूँ", "hi"),
        ("धर्मः रक्षति रक्षितः", "sa"),
        ("ॐ नमः शिवाय", "sa"),
        ("Hello, how are you today?", "en"),
        ("ನಾಳೆ meeting ಇದೆ", "kn"),  # code-switched, Kannada dominant
        ("", None),
        ("123", None),
        ("...?!", None),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_detect_language_unmarked_devanagari_defaults_to_hindi():
    assert detect_language("नमस्ते") == "hi"


def test_detect_language_devanagari_default_sanskrit():
    assert detect_language("नमस्ते", devanagari_default="sa") == "sa"


def test_detect_language_sanskrit_markers_outvote_hindi():
    # "है" is Hindi, but visarga + -ति verb forms dominate → Sanskrit.
    assert detect_language("धर्मः रक्षति है") == "sa"


# ---------------------------------------------------------------- segmentation


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ನಾಳೆ meeting ಇದೆ", [("kn", "ನಾಳೆ"), ("en", "meeting"), ("kn", "ಇದೆ")]),
        ("आज meeting है", [("hi", "आज"), ("en", "meeting"), ("hi", "है")]),
        ("Hello world", [("en", "Hello world")]),
        ("धर्मः रक्षति", [("sa", "धर्मः रक्षति")]),
        ("", []),
        ("   ", []),
        ("123", [("en", "123")]),
    ],
)
def test_segment_by_language(text, expected):
    assert segment_by_language(text) == expected


def test_segment_by_language_devanagari_default_sanskrit():
    assert segment_by_language("नमस्ते", devanagari_default="sa") == [("sa", "नमस्ते")]


# ---------------------------------------------------------------- normalisation


@pytest.mark.parametrize(
    "text,language,expected",
    [
        ("मेरे पास १२३ रुपये हैं", "hi", "मेरे पास 123 रुपये हैं"),
        ("ನನ್ನ ಬಳಿ ೧೨೩ ರೂಪಾಯಿ ಇದೆ", "kn", "ನನ್ನ ಬಳಿ 123 ರೂಪಾಯಿ ಇದೆ"),
        ("यह वाक्य है।", "hi", "यह वाक्य है."),
        ("धर्मः रक्षति ॥", "sa", "धर्मः रक्षति ."),
        ("Hello   world.", "en", "Hello world."),
        ("", "en", ""),
    ],
)
def test_normalize_for_tts(text, language, expected):
    assert normalize_for_tts(text, language) == expected


def test_normalize_for_tts_never_transliterates():
    assert normalize_for_tts("ನಮಸ್ತೆ", "kn") == "ನಮಸ್ತೆ"


# -------------------------------------------------------- STT language normalisation


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("kn", "kn"),
        ("Kannada", "kn"),
        ("HINDI", "hi"),
        ("sanskrit", "sa"),
        ("saṃskṛta", "sa"),
        ("English", "en"),
        ("  ", None),
        ("", None),
        (None, None),
        ("fr", "fr"),  # untuned languages still pass through to STT
        ("zh-cn", "zh-cn"),
        ("not a language!", None),
    ],
)
def test_normalize_language_code(raw, expected):
    assert normalize_language_code(raw) == expected


def test_voice_session_stt_language_uses_aliases():
    kn = VoiceSession(config=_Config(_Speech(language="Kannada")))
    assert kn.get_stt_language() == "kn"


# ---------------------------------------------------------------- TTS voice resolution


def test_resolve_english_kokoro_honors_configured_voice():
    res = resolve_tts_voice(
        language="en",
        backend_id="kokoro",
        configured_backend="kokoro",
        configured_voice_id="bm_george",
    )
    assert (res.voice_id, res.status) == ("bm_george", "ok")


def test_resolve_english_kokoro_substitutes_non_english_voice():
    res = resolve_tts_voice(
        language="en",
        backend_id="kokoro",
        configured_backend="kokoro",
        configured_voice_id="hf_configured",
    )
    assert (res.voice_id, res.status) == ("bm_george", "substituted")


def test_resolve_hindi_kokoro_without_h_voice_is_fail_closed():
    res = resolve_tts_voice(
        language="hi",
        backend_id="kokoro",
        configured_backend="kokoro",
        configured_voice_id="bm_george",
    )
    assert res.voice_id is None
    assert res.status == "no-curated-voice"


def test_resolve_hindi_kokoro_with_h_voice_is_routable_untested():
    # Hook test: the resolver only checks the h* prefix convention from
    # kokoro_tts._VOICE_PREFIX_TO_LANG — "hf_hook" is NOT a claim that a
    # real Kokoro voice with this ID exists.
    res = resolve_tts_voice(
        language="hi",
        backend_id="kokoro",
        configured_backend="kokoro",
        configured_voice_id="hf_hook",
    )
    assert (res.voice_id, res.status) == ("hf_hook", "untested")


@pytest.mark.parametrize("language", ["kn", "sa"])
def test_resolve_kannada_sanskrit_kokoro_has_no_pipeline(language):
    res = resolve_tts_voice(
        language=language,
        backend_id="kokoro",
        configured_backend="kokoro",
        configured_voice_id="bm_george",
    )
    assert res.voice_id is None
    assert res.status == "no-local-pipeline"


@pytest.mark.parametrize(
    "language,backend,expected_status",
    [
        ("hi", "openai_tts", "untested"),
        ("kn", "openai_tts", "untested"),
        ("sa", "cartesia", "untested"),
        ("en", "openai_tts", "ok"),
        ("en", "cartesia", "ok"),
    ],
)
def test_resolve_cloud_backends_are_routable_untested(
    language, backend, expected_status
):
    res = resolve_tts_voice(
        language=language,
        backend_id=backend,
        configured_backend=backend,
        configured_voice_id="configured-voice",
    )
    assert res.voice_id == "configured-voice"
    assert res.status == expected_status


def test_resolve_cloud_fallback_uses_backend_default():
    res = resolve_tts_voice(
        language="hi",
        backend_id="openai_tts",
        configured_backend="kokoro",
        configured_voice_id="bm_george",
    )
    assert (res.voice_id, res.status) == ("onyx", "untested")


def test_resolve_unknown_language_and_backend():
    assert (
        resolve_tts_voice(
            language="fr",
            backend_id="kokoro",
            configured_backend="kokoro",
            configured_voice_id="bm_george",
        ).status
        == "unknown-language"
    )
    assert (
        resolve_tts_voice(
            language="en",
            backend_id="nope",
            configured_backend="nope",
            configured_voice_id="x",
        ).status
        == "unknown-backend"
    )


# -------------------------------------------------------- sentence splitting (Indic)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("यह एक वाक्य है। अगला वाक्य।", ["यह एक वाक्य है।", "अगला वाक्य।"]),
        (
            "धर्मः रक्षति रक्षितः ॥ अगला श्लोकः ॥",
            ["धर्मः रक्षति रक्षितः ॥", "अगला श्लोकः ॥"],
        ),
        ("ಹೇಗಿದ್ದೀರಿ. ಚೆನ್ನಾಗಿದ್ದೇನೆ.", ["ಹೇಗಿದ್ದೀರಿ.", "ಚೆನ್ನಾಗಿದ್ದೇನೆ."]),
        ("Hello. नमस्ते।", ["Hello.", "नमस्ते।"]),
        ("डॉ. स्मित् आए।", ["डॉ. स्मित् आए।"]),
        ("The value is 3.14. Next.", ["The value is 3.14.", "Next."]),
    ],
)
def test_split_sentences_indic(text, expected):
    assert split_sentences(text) == expected


# -------------------------------------------------------- session voice_for_language


@dataclass
class _Speech:
    tts_backend: str = "kokoro"
    voice_id: str = "bm_george"
    voice_speed: float = 1.0
    language: str = ""


@dataclass
class _Config:
    speech: _Speech


class _Backend:
    def __init__(self, backend_id: str) -> None:
        self.backend_id = backend_id

    def health(self) -> bool:
        return True


class _Console:
    def __init__(self) -> None:
        self.printed: list[str] = []

    def print(self, message) -> None:
        self.printed.append(str(message))


def _session(**kwargs) -> VoiceSession:
    return VoiceSession(config=_Config(speech=_Speech(**kwargs)))


def test_voice_for_language_blocks_kannada_on_kokoro_once():
    session, console = _session(), _Console()
    assert session.voice_for_language(_Backend("kokoro"), "kn", console) == (
        None,
        1.0,
    )
    # Second call: same warning is not repeated.
    session.voice_for_language(_Backend("kokoro"), "kn", console)
    assert len(console.printed) == 1
    assert "Kannada" in console.printed[0]


def test_voice_for_language_hindi_on_openai_tts():
    session = _session(tts_backend="openai_tts", voice_id="nova")
    assert session.voice_for_language(_Backend("openai_tts"), "hi") == ("nova", 1.0)


def test_voice_for_language_unknown_backend_keeps_backend_rule():
    session = _session()
    # A test-double backend (non-string backend_id) falls back to the
    # backend-level rule instead of failing.
    backend = _Backend("kokoro")
    backend.backend_id = object()  # type: ignore[assignment]
    assert session.voice_for_language(backend, "kn") == ("", 1.0)


# -------------------------------------------------------- speak() integration (mocked)


def _patch_tts(monkeypatch, backend_cls, played) -> None:
    from openjarvis.core.registry import TTSRegistry

    monkeypatch.setattr(TTSRegistry, "contains", lambda key: True)
    monkeypatch.setattr(TTSRegistry, "get", lambda key: lambda: backend_cls(key))
    monkeypatch.setattr(
        "openjarvis.speech.voice_io.play_wav",
        lambda audio, **kwargs: played.append(audio),
    )


def test_speak_skips_kannada_segment_on_kokoro(monkeypatch) -> None:
    from openjarvis.speech.tts import TTSResult

    spoken: list[tuple[str, str]] = []
    played: list[bytes] = []

    class Backend(_Backend):
        def synthesize(self, text, **kwargs):
            spoken.append((self.backend_id, text))
            return TTSResult(audio=b"wav", sample_rate=24000, format="wav")

    _patch_tts(monkeypatch, Backend, played)
    console = _Console()
    speak("Hello world. ನಮಸ್ಕಾರ.", console, _session(), allow_barge_in=False)

    assert spoken == [("kokoro", "Hello world.")]
    assert played == [b"wav"]
    assert any("Kannada" in line for line in console.printed)


def test_speak_code_switch_hindi_english_per_segment_voice(monkeypatch) -> None:
    from openjarvis.speech.tts import TTSResult

    spoken: list[tuple[str, str, str]] = []
    played: list[bytes] = []

    class Backend(_Backend):
        def synthesize(self, text, **kwargs):
            spoken.append((self.backend_id, kwargs.get("voice_id", ""), text))
            return TTSResult(audio=b"wav", sample_rate=24000, format="wav")

    _patch_tts(monkeypatch, Backend, played)
    session = _session(tts_backend="kokoro", voice_id="hf_hook")
    speak("आज meeting है", _Console(), session, allow_barge_in=False)

    # Hindi segments use the configured h* voice; the English word uses
    # the Kokoro English default (substituted, warned once).
    assert spoken == [
        ("kokoro", "hf_hook", "आज"),
        ("kokoro", "bm_george", "meeting"),
        ("kokoro", "hf_hook", "है"),
    ]
    assert played == [b"wav", b"wav", b"wav"]


def test_speak_all_kannada_on_kokoro_speaks_nothing(monkeypatch) -> None:
    from openjarvis.speech.tts import TTSResult

    spoken: list[str] = []
    played: list[bytes] = []

    class Backend(_Backend):
        def synthesize(self, text, **kwargs):
            spoken.append(text)
            return TTSResult(audio=b"wav", sample_rate=24000, format="wav")

    _patch_tts(monkeypatch, Backend, played)
    console = _Console()
    speak("ಕಾಯಕವೇ ಕೈಲಾಸ", console, _session(), allow_barge_in=False)
    assert spoken == []
    assert played == []
    assert any("Kannada" in line for line in console.printed)


def test_speak_passes_per_segment_language_to_cartesia(monkeypatch) -> None:
    from openjarvis.speech.tts import TTSResult

    spoken: list[tuple[str, str]] = []
    played: list[bytes] = []

    class Backend(_Backend):
        def synthesize(self, text, **kwargs):
            spoken.append((kwargs.get("language", ""), text))
            return TTSResult(audio=b"wav", sample_rate=24000, format="wav")

    _patch_tts(monkeypatch, Backend, played)
    session = _session(tts_backend="cartesia", voice_id="cartesia-uuid")
    speak("आज meeting है", _Console(), session, allow_barge_in=False)

    assert spoken == [("hi", "आज"), ("en", "meeting"), ("hi", "है")]


def test_speak_normalizes_devanagari_digits(monkeypatch) -> None:
    from openjarvis.speech.tts import TTSResult

    spoken: list[str] = []
    played: list[bytes] = []

    class Backend(_Backend):
        def synthesize(self, text, **kwargs):
            spoken.append(text)
            return TTSResult(audio=b"wav", sample_rate=24000, format="wav")

    _patch_tts(monkeypatch, Backend, played)
    session = _session(tts_backend="kokoro", voice_id="hf_hook")
    speak("मेरे पास १२३ रुपये हैं", _Console(), session, allow_barge_in=False)

    assert spoken == ["मेरे पास 123 रुपये हैं"]
