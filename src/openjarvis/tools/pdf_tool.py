"""PDF text extraction tool — extract text from PDF files via pdfplumber."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, List, Optional

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._paths import resolve_allowed_dirs
from openjarvis.tools._stubs import BaseTool, ToolSpec

_DEFAULT_MAX_CHARS = 50_000


def _parse_pages(pages_str: str, total_pages: int) -> List[int]:
    """Parse a page range string into zero-indexed page numbers.

    Supports formats like ``"1-5"`` (range) and ``"1,3,5"`` (list).
    Page numbers in the input are 1-indexed; the returned list is 0-indexed.

    Parameters
    ----------
    pages_str:
        Page specification string.
    total_pages:
        Total number of pages in the PDF.

    Returns
    -------
    List[int]
        Sorted list of zero-indexed page numbers.
    """
    result: list[int] = []
    for part in pages_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = max(1, int(start_str.strip()))
            end = min(total_pages, int(end_str.strip()))
            result.extend(range(start - 1, end))
        else:
            page_num = int(part)
            if 1 <= page_num <= total_pages:
                result.append(page_num - 1)
    return sorted(set(result))


@ToolRegistry.register("pdf_extract")
class PDFExtractTool(BaseTool):
    """Extract text content from PDF files using pdfplumber."""

    tool_id = "pdf_extract"

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
            name="pdf_extract",
            description=(
                "Extract text from a PDF file. Returns the extracted text content."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the PDF file.",
                    },
                    "pages": {
                        "type": "string",
                        "description": (
                            "Page range to extract, e.g. '1-5' or '1,3,5'."
                            " Omit to extract all pages."
                        ),
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": ("Maximum characters to return. Default 50000."),
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
                tool_name="pdf_extract",
                content="No file_path provided.",
                success=False,
            )

        path = Path(file_path)
        if not path.is_absolute() and self._allowed_dirs:
            # A relative name means "inside the sandbox", not the process cwd.
            path = self._allowed_dirs[0] / path

        # Validate extension
        if path.suffix.lower() != ".pdf":
            return ToolResult(
                tool_name="pdf_extract",
                content=f"Not a PDF file: {file_path}",
                success=False,
            )

        # Check sensitive file policy
        from openjarvis.security.file_policy import is_sensitive_file

        if is_sensitive_file(path):
            return ToolResult(
                tool_name="pdf_extract",
                content=f"Access denied: {file_path} is a sensitive file.",
                success=False,
            )

        # Read via descriptors FIRST (before the pdfplumber import check):
        # containment, symlink resolution and the open are one operation,
        # and a path escape is refused even when pdfplumber is absent.
        # pdfplumber reads from the in-memory BytesIO — the file is
        # never re-opened by string.
        from openjarvis.security.canonical_path import (
            UnsafePathError,
            UnsupportedPlatformError,
            read_bytes_within,
        )

        try:
            raw, resolved = read_bytes_within(path, self._allowed_dirs)
        except UnsafePathError:
            return ToolResult(
                tool_name="pdf_extract",
                content=f"Access denied: {file_path} is outside allowed directories.",
                success=False,
            )
        except UnsupportedPlatformError:
            if self._allowed_dirs:
                return ToolResult(
                    tool_name="pdf_extract",
                    content=(
                        f"Access denied: {file_path} cannot be opened "
                        "safely on this platform."
                    ),
                    success=False,
                )
            # TOCTOU-allowlisted: no boundary/descriptor; no containment claimed
            try:
                with open(file_path, "rb") as f:
                    raw = f.read()
            except FileNotFoundError:
                return ToolResult(
                    tool_name="pdf_extract",
                    content=f"File not found: {file_path}",
                    success=False,
                )
            except OSError as exc:
                return ToolResult(
                    tool_name="pdf_extract",
                    content=f"Read error: {exc}",
                    success=False,
                )
            resolved = path
        except FileNotFoundError:
            return ToolResult(
                tool_name="pdf_extract",
                content=f"File not found: {file_path}",
                success=False,
            )
        except IsADirectoryError:
            return ToolResult(
                tool_name="pdf_extract",
                content=f"Not a file: {file_path}",
                success=False,
            )
        except OSError as exc:
            return ToolResult(
                tool_name="pdf_extract",
                content=f"Read error: {exc}",
                success=False,
            )

        try:
            import pdfplumber
        except ImportError:
            return ToolResult(
                tool_name="pdf_extract",
                content=(
                    "pdfplumber package not installed."
                    " Install with: pip install pdfplumber"
                ),
                success=False,
            )

        max_chars = params.get("max_chars", _DEFAULT_MAX_CHARS)
        pages_param = params.get("pages")

        try:
            # TOCTOU-safe: file-like object, not a path
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                total_pages = len(pdf.pages)

                if pages_param:
                    page_indices = _parse_pages(pages_param, total_pages)
                else:
                    page_indices = list(range(total_pages))

                text_parts: list[str] = []
                for idx in page_indices:
                    if 0 <= idx < total_pages:
                        page_text = pdf.pages[idx].extract_text() or ""
                        text_parts.append(page_text)

                text = "\n\n".join(text_parts)
                if len(text) > max_chars:
                    text = text[:max_chars] + "\n\n[Content truncated]"

                return ToolResult(
                    tool_name="pdf_extract",
                    content=text or "No text content found in PDF.",
                    success=True,
                    metadata={
                        "file_path": str(resolved),
                        "total_pages": total_pages,
                        "pages_extracted": len(page_indices),
                    },
                )
        except Exception as exc:
            return ToolResult(
                tool_name="pdf_extract",
                content=f"PDF extraction error: {exc}",
                success=False,
            )


__all__ = ["PDFExtractTool"]
