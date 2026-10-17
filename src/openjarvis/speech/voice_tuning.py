"""Per-language voice tuning for Kannada / Hindi / English / Sanskrit.

Pure, offline helpers for the voice pipeline. Nothing here touches a
microphone, a model, or the network: detection is Unicode-script counting
plus small marker lexicons, TTS normalisation is text rewriting, and the
per-language voice resolver only decides *which* voice ID (if any) a
segment may be synthesised with. Real STT/TTS quality is unverified —
see :mod:`openjarvis.speech.indic` for the honesty rules.

Honesty limits of this module (do not over-claim):

- Language detection is script + marker heuristics, not identification:
  Devanagari is shared by Hindi and Sanskrit, so unmarked Devanagari
  defaults to Hindi (or the caller's ``devanagari_default``) and Sanskrit
  needs markers or explicit configuration. Latin-script Hindi/Sanskrit
  (Roman or IAST transliteration) is detected as English — a known gap.
- Kannada and Sanskrit have NO local TTS pipeline in this repo (Kokoro
  has no pipeline for either), so the resolver returns "no-local-pipeline"
  and the caller must skip those segments rather than mis-speak them in
  an English voice. Hindi via Kokoro needs a user-configured ``h*`` voice
  ID from the installed Kokoro release; this repo curates none.
- Cloud TTS (OpenAI / Cartesia) is "untested": routable when the user
  explicitly configured that backend, never a verified-quality claim.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from openjarvis.speech._tts_discovery import default_voice_for
from openjarvis.speech.indic import get_language_profile

__all__ = [
    "TTSVoiceResolution",
    "detect_language",
    "normalize_for_tts",
    "normalize_language_code",
    "resolve_tts_voice",
    "segment_by_language",
]

# ---------------------------------------------------------------------------
# Script classification
# ---------------------------------------------------------------------------

# Internal script classes. "latin" is really "non-Indic alphabetic": any
# letter outside the Kannada / Devanagari blocks lands here and routes to
# the English voice. Other scripts are NOT tuned by this module.
_KANNADA = "kn"
_DEVANAGARI = "deva"
_LATIN = "latin"


def _script_of(ch: str) -> Optional[str]:
    """Script class of one character, or None if script-neutral."""
    o = ord(ch)
    if 0x0C80 <= o <= 0x0CFF:
        return _KANNADA
    if (
        0x0900 <= o <= 0x097F
        or 0xA8E0 <= o <= 0xA8FF  # Devanagari Extended-A
        or 0x1CD0 <= o <= 0x1CFF  # Vedic Extensions (Sanskrit svaras)
    ):
        return _DEVANAGARI
    if ch.isalpha():
        return _LATIN
    return None


# ---------------------------------------------------------------------------
# Hindi / Sanskrit disambiguation (both use Devanagari)
# ---------------------------------------------------------------------------

# Whole-word markers. Hindi: copulas, postpositions, pronouns — function
# words that rarely appear in Sanskrit. Sanskrit: classical verb forms,
# discourse particles, and adverbs. Either list alone is weak; the scores
# are compared, and ties fall back to the caller's default.
_HINDI_MARKERS = frozenset(
    "है हैं था थी थे हुआ हुई हुए होगा होगी होंगे "
    "का की के को ने से में पर यह वह ये वे नहीं और भी तो ही "
    "क्या कब कहाँ कैसे क्यों कितना अपना अपनी अपने उसका उसकी उसके "
    "इसका इसकी इसके हम तुम आप मैं मेरा मेरी मेरे तेरा तेरी तेरे "
    "जो वो इस उस इन उन जब तब अब यहाँ वहाँ जहाँ".split()
)
_SANSKRIT_MARKERS = frozenset(
    "अस्ति सन्ति भवति भवन्ति करोति कुर्वन्ति गच्छति आगच्छति "
    "पठति लिखति वदति शृणोति पश्यति जानाति तिष्ठति "
    "एव खलु नूनम् इति इदानीम् अत्र तत्र यत्र कुत्र अन्यत्र सर्वत्र उभयत्र "
    "यथा तथा यदि तर्हि यदा तदा कदा अद्य श्वः ह्यः चेत् किल ननु अहो ॐ".split()
)
# Hindi words that legitimately end in visarga (borrowed from Sanskrit).
# Every other visarga-final word scores toward Sanskrit.
_HINDI_VISARGA_EXCEPTIONS = frozenset({"अतः", "प्रातः", "पुनः", "अन्तः"})

_TOKEN_RE = re.compile(r"[^\s.,;:!?।॥\"'“”‘’()\[\]{}<>]+")


def _tokens(text: str) -> list[str]:
    """Whitespace/punctuation-delimited words (virama stays inside)."""
    return _TOKEN_RE.findall(text)


def _disambiguate_devanagari(text: str, default: str) -> str:
    """Hindi vs Sanskrit for Devanagari text (marker scores, tie → default)."""
    hi_score = 0
    sa_score = 0
    for token in _tokens(text):
        if token in _HINDI_MARKERS:
            hi_score += 1
        if token in _SANSKRIT_MARKERS:
            sa_score += 1
        # Structural Sanskrit cues: visarga-final and -म्-final words, and
        # short -ति present-tense verb forms (Hindi -ति nouns like शक्ति
        # can false-positive here; the Hindi-marker score outvotes them
        # when Hindi function words are present).
        if token.endswith("ः") and token not in _HINDI_VISARGA_EXCEPTIONS:
            sa_score += 1
        if token.endswith("म्"):
            sa_score += 1
        if token.endswith("ति"):
            sa_score += 1
    if sa_score > hi_score:
        return "sa"
    if hi_score > sa_score:
        return "hi"
    return default if default in ("hi", "sa") else "hi"


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------


def detect_language(
    text: str,
    *,
    devanagari_default: str = "hi",
) -> Optional[str]:
    """Detect the dominant language of ``text``: kn | hi | sa | en | None.

    Dominant Unicode script wins (ties go to the earliest-appearing
    script). Devanagari is disambiguated by Hindi/Sanskrit markers, with
    unmarked Devanagari falling back to ``devanagari_default``. Returns
    None when ``text`` carries no script-bearing characters (empty,
    digits, or punctuation only).
    """
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for index, ch in enumerate(text):
        script = _script_of(ch)
        if script is None:
            continue
        counts[script] = counts.get(script, 0) + 1
        first_seen.setdefault(script, index)
    if not counts:
        return None
    winner = max(counts, key=lambda s: (counts[s], -first_seen[s]))
    if winner == _KANNADA:
        return "kn"
    if winner == _LATIN:
        return "en"
    return _disambiguate_devanagari(text, devanagari_default)


def segment_by_language(
    text: str,
    *,
    devanagari_default: str = "hi",
) -> list[tuple[str, str]]:
    """Split ``text`` into (language, segment) runs by script.

    Neutral characters (spaces, punctuation, ASCII digits) are absorbed
    into the surrounding run, so "ನಾಳೆ meeting ಇದೆ" becomes Kannada /
    English / Kannada. Devanagari runs are disambiguated per run. Empty
    or whitespace-only input yields []; script-neutral input (e.g. "123")
    yields one English segment (digits are read in the default voice).
    """
    if not text or not text.strip():
        return []
    # Classify; fill neutral chars from the previous run (leading neutrals
    # take the next run's class).
    classes: list[Optional[str]] = [_script_of(ch) for ch in text]
    last: Optional[str] = None
    for i, cls in enumerate(classes):
        if cls is not None:
            last = cls
        elif last is not None:
            classes[i] = last
    nxt: Optional[str] = None
    for i in range(len(classes) - 1, -1, -1):
        if classes[i] is not None:
            nxt = classes[i]
        elif nxt is not None:
            classes[i] = nxt
    if all(cls is None for cls in classes):
        return [("en", text.strip())]
    segments: list[tuple[str, str]] = []
    start = 0
    for i in range(1, len(classes) + 1):
        if i == len(classes) or classes[i] != classes[start]:
            run = text[start:i].strip()
            if run:
                script = classes[start]
                if script == _KANNADA:
                    language = "kn"
                elif script == _LATIN:
                    language = "en"
                else:
                    language = _disambiguate_devanagari(run, devanagari_default)
                segments.append((language, run))
            start = i
    return segments


# ---------------------------------------------------------------------------
# Config language normalisation (STT passthrough)
# ---------------------------------------------------------------------------

_BCP47_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{2})?$")


def normalize_language_code(code: object) -> Optional[str]:
    """Normalise a configured language to a backend language code.

    Long names / aliases ("Kannada", "HINDI", "saṃskṛta") map to the
    profile code (kn / hi / sa); any other BCP-47-ish code ("fr",
    "zh-cn") passes through untouched so STT keeps working for
    languages this module does not tune; anything else yields None
    (auto-detect) instead of forwarding garbage to Whisper.
    """
    if not isinstance(code, str):
        return None
    key = code.strip().lower()
    if not key:
        return None
    profile = get_language_profile(key)
    if profile is not None:
        return profile.code
    if _BCP47_RE.match(key):
        return key
    return None


# ---------------------------------------------------------------------------
# TTS input normalisation (pronunciation / phoneme handling)
# ---------------------------------------------------------------------------

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_KANNADA_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")


def normalize_for_tts(text: str, language: Optional[str] = None) -> str:
    """Normalise ``text`` for TTS input in ``language``.

    NFC normalisation, Devanagari/Kannada digits → ASCII digits (backends
    pronounce ASCII digits; Indic digits are often skipped or garbled),
    danda/double-danda → "." (a boundary every backend understands), and
    whitespace collapse. The text itself is otherwise untouched — no
    transliteration, no word substitution — so pronunciation can only gain
    from digit/danda handling, never from a guessed respelling.
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.translate(_DEVANAGARI_DIGITS)
    normalized = normalized.translate(_KANNADA_DIGITS)
    normalized = normalized.replace("॥", ".").replace("।", ".")
    return " ".join(normalized.split())


# ---------------------------------------------------------------------------
# Per-language TTS voice resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TTSVoiceResolution:
    """Outcome of resolving a TTS voice for one language on one backend.

    ``voice_id`` is None exactly when the segment must NOT be synthesised
    on this backend (fail-closed: never mis-speak a segment in a
    wrong-language voice). ``""`` means "no voice argument" (the backend
    picks its own default — Cartesia). ``status`` is a routing verdict,
    never a quality claim: "ok" = routable, "untested" = routable but
    quality unverified, the rest = do not synthesise here.
    """

    voice_id: Optional[str]
    status: str  # ok | substituted | untested | no-curated-voice |
    # no-local-pipeline | unknown-language | unknown-backend
    reason: str


_KOKORO_EN_PREFIXES = ("a", "b")  # American / British English voices


def resolve_tts_voice(
    *,
    language: Optional[str],
    backend_id: str,
    configured_backend: str,
    configured_voice_id: str,
) -> TTSVoiceResolution:
    """Pick the voice for ``language`` on ``backend_id`` (or refuse).

    The configured voice is honoured only when it belongs to the segment's
    language (Kokoro voice IDs carry a language prefix: a/b = English,
    h = Hindi). A configured English voice is never handed a Hindi segment
    and vice versa — that mismatch is the mis-pronunciation this resolver
    exists to prevent.
    """
    profile = get_language_profile(language or "")
    if profile is None:
        return TTSVoiceResolution(
            voice_id=None,
            status="unknown-language",
            reason=(
                f"No voice tuning for language {language!r}: this module "
                "tunes Kannada, Hindi, English, and Sanskrit only."
            ),
        )
    if backend_id == "kokoro":
        if language == "en":
            if (
                configured_backend == "kokoro"
                and configured_voice_id
                and configured_voice_id[:1] in _KOKORO_EN_PREFIXES
            ):
                return TTSVoiceResolution(
                    voice_id=configured_voice_id,
                    status="ok",
                    reason="Configured Kokoro English voice.",
                )
            if configured_backend == "kokoro" and configured_voice_id:
                return TTSVoiceResolution(
                    voice_id=default_voice_for("kokoro"),
                    status="substituted",
                    reason=(
                        f"Configured voice {configured_voice_id!r} is not an "
                        "English (a*/b*) Kokoro voice, so this English "
                        "segment uses the Kokoro default instead of "
                        "mis-routing it to a non-English voice."
                    ),
                )
            return TTSVoiceResolution(
                voice_id=default_voice_for("kokoro"),
                status="ok",
                reason="Kokoro default English voice.",
            )
        if language == "hi":
            if configured_backend == "kokoro" and configured_voice_id.startswith("h"):
                return TTSVoiceResolution(
                    voice_id=configured_voice_id,
                    status="untested",
                    reason=(
                        "Configured Hindi (h*) Kokoro voice; the Hindi "
                        "pipeline is untested in this repo."
                    ),
                )
            return TTSVoiceResolution(
                voice_id=None,
                status="no-curated-voice",
                reason=(
                    "No curated Hindi Kokoro voice: set speech.voice_id to "
                    "a Hindi Kokoro voice (h* prefix) from the installed "
                    "Kokoro release. This Hindi segment is skipped rather "
                    "than mis-spoken in an English voice."
                ),
            )
        # Kannada / Sanskrit: Kokoro has no pipeline for either.
        return TTSVoiceResolution(
            voice_id=None,
            status="no-local-pipeline",
            reason=(
                f"Kokoro has no {profile.name} pipeline, so {profile.name} "
                "TTS is unsupported locally. This segment is skipped; "
                "configure a cloud TTS backend to voice it (untested)."
            ),
        )
    if backend_id in ("openai_tts", "cartesia"):
        voice = (
            configured_voice_id
            if configured_backend == backend_id and configured_voice_id
            else default_voice_for(backend_id)
        )
        if language == "en":
            return TTSVoiceResolution(
                voice_id=voice,
                status="ok",
                reason=f"English via {backend_id} (configured/cloud backend).",
            )
        return TTSVoiceResolution(
            voice_id=voice,
            status="untested",
            reason=(
                f"{profile.name} via {backend_id}: routable because the user "
                "explicitly configured a cloud backend, but quality is "
                "untested in this repo and the backend needs its API key."
            ),
        )
    return TTSVoiceResolution(
        voice_id=None,
        status="unknown-backend",
        reason=f"No voice tuning for TTS backend {backend_id!r}.",
    )
