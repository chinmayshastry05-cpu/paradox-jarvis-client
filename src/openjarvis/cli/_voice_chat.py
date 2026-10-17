"""Voice input/output helpers for the interactive chat session."""

from __future__ import annotations

import select
import sys
import threading
from typing import Any, Optional

from rich.markup import escape

VOICE_EXIT = object()

# Backend selection is shared with the API server and lives in
# openjarvis.speech._tts_discovery. Importing that at module level would pull
# the whole speech stack -- numpy included -- into every `jarvis` invocation,
# which tests/cli/test_cli.py guards against, so these aliases resolve lazily.
_LAZY_TTS_NAMES = {
    "_TTS_BACKEND_ORDER": "TTS_BACKEND_ORDER",
    "_BACKEND_DEFAULT_VOICE": "BACKEND_DEFAULT_VOICE",
}


def __getattr__(name: str) -> Any:
    target = _LAZY_TTS_NAMES.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from openjarvis.speech import _tts_discovery

    return getattr(_tts_discovery, target)


def _terminal_safe_text(value: object) -> str:
    """Remove terminal controls and escape Rich markup from dynamic text."""
    printable = "".join(
        char for char in str(value) if char in ("\n", "\t") or char.isprintable()
    )
    return escape(printable)


class _BargeInListener:
    """Daemon thread: any keypress on a TTY stdin requests cancellation.

    Only runs during ``speak()`` (no other stdin reader is active then), and
    only when stdin is a TTY — piped/non-interactive stdin never starts it.
    In canonical terminal mode a keypress becomes readable on Enter, so
    pressing Enter is the barge-in gesture. ``select`` failures (e.g. a
    non-selectable stdin) end the thread silently instead of breaking chat.
    """

    def __init__(self, machine: Any) -> None:
        self._machine = machine
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            sys.stdin.fileno()
        except Exception:
            return
        while not self._stop.is_set():
            try:
                readable, _, _ = select.select([sys.stdin], [], [], 0.05)
            except Exception:
                return
            if readable:
                try:
                    if sys.stdin.read(1):
                        self._machine.request_cancel()
                        return
                except Exception:
                    return


class VoiceSession:
    """Cache healthy speech backends for one interactive chat session."""

    def __init__(self, config: object | None = None) -> None:
        self._config = config
        self._stt_resolved = False
        self._stt_backend: Any = None
        self._tts_backend: Any = None
        self._tts_attempted: set[str] = set()
        self._voice_prefs: tuple[str, str, float] | None = None
        self._voice_warned: set[str] = set()
        # (backend, language, resolver status) warned about once per session
        # by voice_for_language (e.g. a skipped Kannada segment).
        self._voice_lang_warned: set[tuple[str, str, str]] = set()
        # Imported lazily like the other speech helpers: importing the
        # openjarvis.speech package at module level would pull the whole
        # speech stack into every `jarvis` invocation.
        from openjarvis.speech.voice_state import PushToTalkStateMachine

        self.state_machine = PushToTalkStateMachine()
        self._wake_word_detector: Any = None

    def request_barge_in(self) -> None:
        """Programmatic barge-in: stop the current TTS/playback cleanly."""
        self.state_machine.request_cancel()

    def get_wake_word_detector(self) -> Any:
        """Opt-in local wake-word detector (OFF unless configured on)."""
        if self._wake_word_detector is None:
            from openjarvis.core.config import load_config
            from openjarvis.speech.indic import LocalWakeWordDetector

            config = self._config if self._config is not None else load_config()
            speech = getattr(config, "speech", None)
            self._wake_word_detector = LocalWakeWordDetector(
                phrase=getattr(speech, "wake_word_phrase", "jarvis") or "jarvis",
                enabled=bool(getattr(speech, "wake_word_enabled", False)),
            )
        return self._wake_word_detector

    def check_wake_word(self, audio: bytes) -> bool:
        """True if the configured wake phrase is heard in ``audio``.

        Local-only: detection runs through the session's STT backend (or
        never fires when none is available). Audio is never sent anywhere
        for wake-word detection.
        """
        detector = self.get_wake_word_detector()
        if not detector.enabled:
            return False
        return detector.detect(audio, transcriber=self.get_stt_backend())

    def get_stt_backend(self) -> Any:
        """Resolve and health-check STT once, then reuse the loaded backend."""
        if not self._stt_resolved:
            from openjarvis.core.config import load_config
            from openjarvis.speech._discovery import get_speech_backend

            config = self._config if self._config is not None else load_config()
            self._stt_backend = get_speech_backend(config)
            self._stt_resolved = True
        return self._stt_backend

    def get_stt_language(self) -> Optional[str]:
        """Return the configured ``speech.language``, or None to auto-detect.

        Long names ("Kannada", "HINDI") normalise to backend codes ("kn",
        "hi"); other BCP-47-ish codes pass through untouched.
        """
        from openjarvis.core.config import load_config
        from openjarvis.speech.voice_tuning import normalize_language_code

        config = self._config if self._config is not None else load_config()
        return normalize_language_code(getattr(config.speech, "language", ""))

    def get_tts_backend(self) -> Any:
        """Return a cached healthy TTS backend, falling through once per key.

        Returns None when voice output is disabled (``speech.tts_enabled``
        is False) or when no backend is healthy.
        """
        if self._tts_backend is not None:
            return self._tts_backend

        from openjarvis.speech._tts_discovery import get_tts_backend

        preferred, _, _ = self.get_voice_preferences()
        from openjarvis.core.config import load_config

        config = self._config if self._config is not None else load_config()
        enabled = bool(getattr(config.speech, "tts_enabled", True))
        self._tts_backend = get_tts_backend(
            preferred, attempted=self._tts_attempted, enabled=enabled
        )
        return self._tts_backend

    def get_voice_preferences(self) -> tuple[str, str, float]:
        """Resolve configured (tts_backend, voice_id, speed), cached per session."""
        if self._voice_prefs is None:
            from openjarvis.core.config import load_config
            from openjarvis.speech._tts_discovery import voice_preferences

            config = self._config if self._config is not None else load_config()
            self._voice_prefs = voice_preferences(config)
        return self._voice_prefs

    def voice_for_backend(self, backend: Any, console: Any = None) -> tuple[str, float]:
        """Return the voice ID valid for ``backend``, plus the configured speed.

        Voice IDs are not portable across backends, so the configured
        ``speech.voice_id`` is honored only when ``backend`` is the configured
        ``speech.tts_backend``. Otherwise the fallback backend's own default is
        used and the substitution is reported once per session.
        """
        want_backend, voice_id, speed = self.get_voice_preferences()
        active = getattr(backend, "backend_id", "") or ""
        if active == want_backend:
            return voice_id, speed

        from openjarvis.speech._tts_discovery import default_voice_for

        substitute = default_voice_for(active)
        if console is not None and active not in self._voice_warned:
            self._voice_warned.add(active)
            console.print(
                f"[dim yellow]Voice: {want_backend!r} unavailable — using "
                f"{active!r} with its default voice "
                f"({substitute or 'backend default'}).[/dim yellow]"
            )
        return substitute, speed

    def voice_for_language(
        self, backend: Any, language: Optional[str], console: Any = None
    ) -> tuple[Optional[str], float]:
        """Return the voice ID valid for ``language`` on ``backend``.

        Returns ``(None, speed)`` exactly when the segment must NOT be
        synthesised on this backend (fail-closed: no local pipeline, or
        no curated voice for the language — the caller skips the segment
        instead of mis-speaking it in a wrong-language voice).
        ``""`` means "no voice argument" (the backend picks its default).
        Unknown/custom backends (and test doubles) keep the backend-level
        ``voice_for_backend`` rule. Warnings fire once per
        (backend, language, resolver status) per session.
        """
        from openjarvis.speech.voice_tuning import resolve_tts_voice

        want_backend, voice_id_cfg, speed = self.get_voice_preferences()
        active = getattr(backend, "backend_id", "") or ""
        if not isinstance(active, str) or active not in (
            "kokoro",
            "openai_tts",
            "cartesia",
        ):
            voice_id, speed = self.voice_for_backend(backend, console)
            return voice_id, speed
        resolved = resolve_tts_voice(
            language=language,
            backend_id=active,
            configured_backend=want_backend,
            configured_voice_id=voice_id_cfg,
        )
        if resolved.status in (
            "no-curated-voice",
            "no-local-pipeline",
            "unknown-language",
            "unknown-backend",
            "substituted",
            "untested",
        ):
            key = (active, language or "", resolved.status)
            if console is not None and key not in self._voice_lang_warned:
                self._voice_lang_warned.add(key)
                console.print(f"[dim yellow]Voice: {resolved.reason}[/dim yellow]")
        return resolved.voice_id, speed

    def discard_tts_backend(self) -> None:
        """Forget a backend that failed synthesis and allow the next fallback."""
        self._tts_backend = None


def read_voice_input(console: Any, session: VoiceSession) -> Optional[str] | object:
    """Accept a typed command/message, or record after an empty submission."""
    try:
        typed = input("You> [type, or press Enter to speak] ")
    except (EOFError, KeyboardInterrupt):
        return VOICE_EXIT
    typed = typed.strip()
    return typed if typed else record_voice(console, session)


def record_voice(
    console: Any,
    session: VoiceSession | None = None,
) -> Optional[str] | object:
    """Record from mic, transcribe, and return text or a loop sentinel.

    Drives the push-to-talk state machine: IDLE -> LISTENING -> PROCESSING
    -> IDLE. The ``finally`` always returns the machine to IDLE so a failed
    turn can never wedge the next one.
    """
    from openjarvis.speech.voice_io import record_until_silence
    from openjarvis.speech.voice_state import VoiceState

    active_session = session or VoiceSession()
    machine = active_session.state_machine
    if machine.state is not VoiceState.IDLE:
        machine.to_idle()  # self-heal a stale turn; never raise into chat
    machine.clear_cancel()
    machine.transition(VoiceState.LISTENING)
    try:
        backend = active_session.get_stt_backend()
        if backend is None:
            console.print(
                "[red]No speech-to-text backend available. "
                "Install the voice dependencies with: "
                "pip install 'OpenJarvis[speech]', or configure a healthy "
                "OpenAI/Deepgram backend.[/red]"
            )
            return VOICE_EXIT

        console.print("[dim cyan]Listening… (speak now, stops on silence)[/dim cyan]")
        try:
            audio_bytes = record_until_silence()
        except KeyboardInterrupt:
            return VOICE_EXIT
        except Exception as exc:
            # PortAudio failures are regular Exceptions (and can surface as
            # OSError), so report them without letting terminal control sequences
            # through. SystemExit deliberately continues to propagate, while
            # Ctrl-C maps to the chat loop's graceful-exit sentinel above.
            console.print(f"[red]Mic error: {_terminal_safe_text(exc)}[/red]")
            return VOICE_EXIT

        machine.transition(VoiceState.PROCESSING)
        console.print("[dim]Transcribing…[/dim]")
        try:
            result = backend.transcribe(
                audio_bytes,
                format="wav",
                language=active_session.get_stt_language(),
            )
            text = result.text.strip()
            if text:
                console.print(f"[bold]You (voice):[/bold] {_terminal_safe_text(text)}")
                return text
            console.print("[dim]Nothing heard — try again.[/dim]")
            return None
        except Exception as exc:
            console.print(f"[red]Transcription error: {_terminal_safe_text(exc)}[/red]")
            return None
    finally:
        machine.to_idle()


def speak(
    text: str,
    console: Any,
    session: VoiceSession | None = None,
    *,
    allow_barge_in: bool = True,
) -> None:
    """Synthesize and play text, sentence by sentence, reusing a healthy backend.

    Sentence-level TTS: each sentence is synthesized and played before the
    next one starts, so a long reply starts speaking sooner and a barge-in
    drops only the remaining sentences. If a backend fails mid-response the
    fallback backend resumes with the *remaining* sentences — already-spoken
    sentences are never replayed.

    Code-switching: each sentence is further split into per-language
    segments (Kannada / Hindi / English / Sanskrit by script + markers),
    and each segment is synthesised with that language's voice. A segment
    with no voice on the active backend (e.g. Kannada on Kokoro, which has
    no Kannada pipeline) is skipped with a warning — never mis-spoken in
    a wrong-language voice. Segment text is normalised for TTS first
    (Indic digits → ASCII, danda → ".").

    Barge-in: while speaking, a keypress on a TTY (Enter) or a call to
    ``session.request_barge_in()`` stops the current playback cleanly
    (``play_wav`` halts via ``sd.stop()``) and ends ``speak`` after the
    in-flight sentence. The state machine returns to IDLE either way.
    """
    from openjarvis.speech.indic import get_language_profile
    from openjarvis.speech.voice_io import play_wav
    from openjarvis.speech.voice_state import VoiceState, split_sentences
    from openjarvis.speech.voice_tuning import (
        normalize_for_tts,
        segment_by_language,
    )

    active_session = session or VoiceSession()
    machine = active_session.state_machine
    sentences = split_sentences(text)
    if not sentences:
        return
    # Per-language units for code-switching. The configured language (if
    # Hindi/Sanskrit) disambiguates unmarked Devanagari; otherwise Hindi
    # is the Devanagari default.
    configured: Optional[str] = None
    get_stt_language = getattr(active_session, "get_stt_language", None)
    if callable(get_stt_language):
        try:
            configured = get_stt_language()
        except Exception:
            configured = None
    devanagari_default = configured if configured in ("hi", "sa") else "hi"
    pending: list[tuple[str, str]] = []
    for sentence in sentences:
        pending.extend(
            segment_by_language(sentence, devanagari_default=devanagari_default)
        )
    if not pending:
        return
    if machine.state not in (VoiceState.IDLE, VoiceState.PROCESSING):
        machine.to_idle()  # self-heal a stale turn; never raise into chat
    machine.clear_cancel()
    machine.transition(VoiceState.SPEAKING)

    listener: _BargeInListener | None = None
    if allow_barge_in:
        try:
            if sys.stdin.isatty():
                listener = _BargeInListener(machine)
                listener.start()
        except Exception:
            listener = None
    try:
        # Resolved before the loop: a bad config value must surface as a config
        # error, not be swallowed by the per-backend fallback handler below.
        try:
            active_session.get_voice_preferences()
        except Exception as exc:
            console.print(
                f"[red]Invalid speech config: {_terminal_safe_text(exc)}[/red]"
            )
            return

        pending = list(pending)
        while pending:
            backend = active_session.get_tts_backend()
            if backend is None:
                break
            try:
                while pending:
                    if machine.cancel_requested:
                        return
                    language, segment = pending[0]
                    normalized = normalize_for_tts(segment, language)
                    if not normalized:
                        pending.pop(0)
                        continue
                    voice_id, speed = active_session.voice_for_language(
                        backend, language, console
                    )
                    if voice_id is None:
                        # Fail-closed: no voice for this language on this
                        # backend. Skip the segment (warning already
                        # emitted once by voice_for_language) and keep the
                        # backend for the remaining segments.
                        pending.pop(0)
                        continue
                    synth_kwargs: dict[str, Any] = {
                        "output_format": "wav",
                        "speed": speed,
                    }
                    if voice_id:
                        synth_kwargs["voice_id"] = voice_id
                    # Cartesia takes an explicit per-segment language;
                    # other backends have no language parameter.
                    if getattr(backend, "backend_id", "") == "cartesia":
                        profile = get_language_profile(language)
                        if profile is not None:
                            synth_kwargs["language"] = profile.whisper_code
                    result = backend.synthesize(normalized, **synth_kwargs)
                    if result.audio:
                        play_wav(
                            result.audio,
                            sample_rate=result.sample_rate,
                            should_stop=lambda: machine.cancel_requested,
                        )
                    pending.pop(0)
                return
            except Exception as exc:
                console.print(
                    f"[dim yellow]Voice backend "
                    f"{getattr(backend, 'backend_id', '?')!r} failed: "
                    f"{_terminal_safe_text(exc)}[/dim yellow]"
                )
                active_session.discard_tts_backend()
                if machine.cancel_requested:
                    return

        if pending:
            console.print(
                "[dim yellow]No TTS backend available — install kokoro: "
                "pip install kokoro[/dim yellow]"
            )
    finally:
        if listener is not None:
            listener.stop()
        machine.to_idle()


__all__ = ["VOICE_EXIT", "VoiceSession", "read_voice_input", "record_voice", "speak"]
