"""Audio transcription tool — transcribe audio via OpenAI Whisper."""

from __future__ import annotations

import io
import os
import stat as _stat
from pathlib import Path
from typing import Any, List, Optional

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._paths import resolve_allowed_dirs
from openjarvis.tools._stubs import BaseTool, ToolSpec

_SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


@ToolRegistry.register("audio_transcribe")
class AudioTranscribeTool(BaseTool):
    """Transcribe audio files using OpenAI Whisper or a local provider."""

    tool_id = "audio_transcribe"
    is_local = False

    def __init__(
        self,
        allowed_dirs: Optional[List[str]] = None,
    ) -> None:
        self._allowed_dirs = [
            Path(d).expanduser().resolve() for d in resolve_allowed_dirs(allowed_dirs)
        ]

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="audio_transcribe",
            description=(
                "Transcribe an audio file to text."
                " Supports mp3, wav, m4a, ogg, flac, and webm formats."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the audio file to transcribe.",
                    },
                    "language": {
                        "type": "string",
                        "description": "Optional language code (e.g. 'en', 'es').",
                    },
                    "provider": {
                        "type": "string",
                        "description": (
                            "Transcription provider: 'openai' or 'local'."
                            " Default 'openai'."
                        ),
                    },
                },
                "required": ["file_path"],
            },
            category="media",
            required_capabilities=["file:read"],
        )

    def execute(self, **params: Any) -> ToolResult:
        file_path = params.get("file_path", "")
        if not file_path:
            return ToolResult(
                tool_name="audio_transcribe",
                content="No file_path provided.",
                success=False,
            )

        path = Path(file_path)
        if not path.is_absolute() and self._allowed_dirs:
            # A relative name means "inside the sandbox", not the process cwd.
            path = self._allowed_dirs[0] / path

        # Open via descriptors: containment, symlink resolution and the
        # open are one operation — a path swapped between a string check
        # and the open cannot redirect this read. The file is read from
        # the opened descriptor, never re-opened by string.
        from openjarvis.security.canonical_path import (
            UnsafePathError,
            UnsupportedPlatformError,
            open_within,
        )

        try:
            fd, resolved = open_within(path, self._allowed_dirs, flags=os.O_RDONLY)
        except UnsafePathError:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"Access denied: {file_path} is outside allowed directories.",
                success=False,
            )
        except UnsupportedPlatformError:
            if self._allowed_dirs:
                return ToolResult(
                    tool_name="audio_transcribe",
                    content=(
                        f"Access denied: {file_path} cannot be opened "
                        "safely on this platform."
                    ),
                    success=False,
                )
            return self._legacy_transcribe(file_path, params)
        except FileNotFoundError:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"File not found: {file_path}",
                success=False,
            )
        except IsADirectoryError:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"Not a file: {file_path}",
                success=False,
            )
        except OSError as exc:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"Read error: {exc}",
                success=False,
            )

        try:
            st = os.fstat(fd)
            if not _stat.S_ISREG(st.st_mode):
                return ToolResult(
                    tool_name="audio_transcribe",
                    content=f"Not a file: {file_path}",
                    success=False,
                )
            # Validate format on the RESOLVED path (a symlink could
            # rename the extension between the input string and the file).
            suffix = resolved.suffix.lower()
            if suffix not in _SUPPORTED_FORMATS:
                return ToolResult(
                    tool_name="audio_transcribe",
                    content=(
                        f"Unsupported audio format '{suffix}'."
                        f" Supported: {', '.join(sorted(_SUPPORTED_FORMATS))}."
                    ),
                    success=False,
                )
            if st.st_size > _MAX_FILE_SIZE_BYTES:
                return ToolResult(
                    tool_name="audio_transcribe",
                    content=(
                        f"File too large: {st.st_size} bytes"
                        f" (max {_MAX_FILE_SIZE_BYTES} bytes / 25 MB)."
                    ),
                    success=False,
                )
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
        except OSError as exc:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"Read error: {exc}",
                success=False,
            )
        finally:
            os.close(fd)

        return self._transcribe_bytes(raw, resolved.name, str(resolved), params)

    def _legacy_transcribe(self, file_path: str, params: Any) -> ToolResult:
        """Plain string open, only when no boundary is configured and the
        platform has no descriptor open. No containment is claimed."""
        # TOCTOU-allowlisted: no boundary/descriptor; no containment claimed
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"File not found: {file_path}",
                success=False,
            )
        except OSError as exc:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"Read error: {exc}",
                success=False,
            )
        if len(raw) > _MAX_FILE_SIZE_BYTES:
            return ToolResult(
                tool_name="audio_transcribe",
                content=(
                    f"File too large: {len(raw)} bytes"
                    f" (max {_MAX_FILE_SIZE_BYTES} bytes / 25 MB)."
                ),
                success=False,
            )
        return self._transcribe_bytes(raw, Path(file_path).name, file_path, params)

    def _transcribe_bytes(
        self, raw: bytes, name: str, display_path: str, params: Any
    ) -> ToolResult:
        provider = params.get("provider", "openai")
        language = params.get("language")

        if provider == "local":
            return ToolResult(
                tool_name="audio_transcribe",
                content="Local transcription provider is not yet implemented.",
                success=False,
            )

        if provider != "openai":
            return ToolResult(
                tool_name="audio_transcribe",
                content=(
                    f"Unsupported provider '{provider}'. Supported: 'openai', 'local'."
                ),
                success=False,
            )

        # OpenAI Whisper provider
        try:
            import openai
        except ImportError:
            return ToolResult(
                tool_name="audio_transcribe",
                content=(
                    "openai package not installed. Install with: pip install openai"
                ),
                success=False,
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return ToolResult(
                tool_name="audio_transcribe",
                content="No API key configured. Set OPENAI_API_KEY.",
                success=False,
            )

        try:
            client = openai.OpenAI()
            kwargs: dict[str, Any] = {"model": "whisper-1"}
            if language:
                kwargs["language"] = language

            # Bytes read from the descriptor above — never re-opened by
            # string, so a swapped path cannot redirect this upload.
            bio = io.BytesIO(raw)
            bio.name = name
            kwargs["file"] = bio
            transcription = client.audio.transcriptions.create(**kwargs)

            text = transcription.text
            metadata: dict[str, Any] = {
                "file_path": display_path,
                "provider": provider,
            }
            if language:
                metadata["language"] = language
            if hasattr(transcription, "duration"):
                metadata["duration_ms"] = int(transcription.duration * 1000)

            return ToolResult(
                tool_name="audio_transcribe",
                content=text,
                success=True,
                metadata=metadata,
            )
        except Exception as exc:
            return ToolResult(
                tool_name="audio_transcribe",
                content=f"Transcription error: {exc}",
                success=False,
            )


__all__ = ["AudioTranscribeTool"]
