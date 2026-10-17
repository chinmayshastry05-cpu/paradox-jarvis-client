"""TOCTOU audit tripwire (Phase 1).

Every string-path file open in the audited source trees must either go
through the descriptor helpers in ``openjarvis.security.canonical_path``
or carry an explicit ``# TOCTOU-safe`` / ``# TOCTOU-allowlisted:``
marker with a justification on the same line or within the two lines
above the call. A new unmarked ``open``/``read_text``/``write_text``/
``read_bytes``/``write_bytes`` call fails this test — that is the point:
classify the new site (descriptor helper, or allowlist with a reason)
instead of silently adding a string open.

Containment tests below prove the moved sites refuse symlink escapes.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "openjarvis"

# Trees audited for string-path opens. canonical_path.py itself is the
# helper implementation (excluded); tests/ are excluded.
AUDITED = [
    SRC / "tools",
    SRC / "agents",
    SRC / "memory",
    SRC / "sessions",
    SRC / "traces",
    SRC / "server" / "session_store.py",
    SRC / "connectors" / "store.py",
    SRC / "connectors" / "attachment_store.py",
]

_TARGET_FUNCS = {"open", "read_text", "write_text", "read_bytes", "write_bytes"}
_MARKERS = ("# TOCTOU-safe", "# TOCTOU-allowlisted")


def _iter_py_files():
    for base in AUDITED:
        if base.is_file():
            yield base
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


def _flagged_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in _TARGET_FUNCS:
            yield node
        elif isinstance(func, ast.Attribute) and func.attr in _TARGET_FUNCS:
            # Skip Path.open / os.open etc. only when the attribute is
            # one of the targets — open/read_text/write_text/read_bytes/
            # write_bytes are all covered either way.
            yield node


def test_every_string_open_is_classified():
    """Every flagged call has a TOCTOU marker nearby, or is a helper call."""
    failures = []
    for path in _iter_py_files():
        src = path.read_text(encoding="utf-8")
        lines = src.splitlines()
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT)}: unparseable: {exc}")
            continue
        for node in _flagged_calls(tree):
            lineno = node.lineno  # 1-based
            # The marker must be on the call's line or within the two
            # lines above it (allows a comment line directly above).
            window = lines[max(0, lineno - 3) : lineno]
            if any(m in line for line in window for m in _MARKERS):
                continue
            # Calls that go through the descriptor helpers by
            # construction (open_within / read_bytes_within /
            # open_for_write_within / open_rdwr_within) are not
            # string opens — but those helpers are named differently,
            # so they are never flagged. Anything flagged here is a
            # real string open that needs a marker.
            failures.append(
                f"{path.relative_to(REPO_ROOT)}:{lineno}: "
                f"unclassified string open: {lines[lineno - 1].strip()}"
            )
    assert not failures, (
        "Unclassified string-path file opens (add a descriptor helper "
        "or a '# TOCTOU-allowlisted: <reason>' marker):\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Containment: moved sites refuse symlink escapes
# ---------------------------------------------------------------------------


def test_audio_tool_refuses_symlink_escape(tmp_path):
    from openjarvis.tools.audio_tool import AudioTranscribeTool

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"fake audio")
    link = allowed / "evil.mp3"
    link.symlink_to(outside)
    tool = AudioTranscribeTool(allowed_dirs=[str(allowed)])
    result = tool.execute(file_path=str(link))
    assert not result.success
    assert "Access denied" in result.content


def test_pdf_tool_refuses_symlink_escape(tmp_path):
    from openjarvis.tools.pdf_tool import PDFExtractTool

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4 fake")
    link = allowed / "evil.pdf"
    link.symlink_to(outside)
    tool = PDFExtractTool(allowed_dirs=[str(allowed)])
    result = tool.execute(file_path=str(link))
    assert not result.success
    assert "Access denied" in result.content


def test_ingest_refuses_symlink_escape(tmp_path):
    from openjarvis.tools.storage.ingest import ingest_path, read_document

    root = tmp_path / "root"
    root.mkdir()
    (root / "ok.txt").write_text("hello")
    outside = tmp_path / "outside.txt"
    outside.write_text("SECRET-DO-NOT-INGEST")
    link = root / "evil.txt"
    link.symlink_to(outside)
    # Direct read of the escape link is refused.
    with pytest.raises(Exception, match="outside|UnsafePath"):
        read_document(link, boundary=root)
    # Walk skips the escape link instead of following it.
    chunks = ingest_path(root)
    sources = [c.source for c in chunks]
    assert any("ok.txt" in s for s in sources)
    assert not any("evil" in s for s in sources)
    assert not any("SECRET" in c.content for c in chunks)


def test_browser_screenshot_refuses_symlink_escape(tmp_path, monkeypatch):
    from openjarvis.tools.browser import BrowserScreenshotTool

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    victim = tmp_path / "victim.png"
    victim.write_bytes(b"ORIGINAL")
    link = allowed / "shot.png"
    link.symlink_to(victim)

    class _FakePage:
        def screenshot(self, full_page=False):
            return b"FAKE-PNG"

    class _FakeSession:
        page = _FakePage()

    monkeypatch.setattr("openjarvis.tools.browser._session", _FakeSession())
    tool = BrowserScreenshotTool(allowed_dirs=[str(allowed)])
    result = tool.execute(path=str(link))
    assert not result.success
    assert "Access denied" in result.content
    # The victim file was NOT truncated or overwritten.
    assert victim.read_bytes() == b"ORIGINAL"


def test_image_tool_refuses_symlink_escape(tmp_path, monkeypatch):
    from openjarvis.tools.image_tool import ImageGenerateTool

    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    victim = tmp_path / "victim.png"
    victim.write_bytes(b"ORIGINAL")
    link = allowed / "out.png"
    link.symlink_to(victim)

    class _FakeResp:
        content = b"FAKE-IMG"

        def raise_for_status(self):
            pass

    class _FakeHttpx:
        @staticmethod
        def get(url, follow_redirects=True, timeout=60.0):
            return _FakeResp()

    monkeypatch.setitem(sys.modules, "httpx", _FakeHttpx())

    class _FakeImages:
        def generate(self, model, prompt, size, n):
            class _Data:
                url = "https://example.com/fake.png"

            class _Resp:
                data = [_Data()]

            return _Resp()

    class _FakeOpenAI:
        def __init__(self):
            self.images = _FakeImages()

    monkeypatch.setitem(sys.modules, "openai", type("M", (), {"OpenAI": _FakeOpenAI})())
    tool = ImageGenerateTool(allowed_dirs=[str(allowed)])
    result = tool.execute(prompt="a cat", output_path=str(link))
    assert not result.success
    assert "Access denied" in result.content
    assert victim.read_bytes() == b"ORIGINAL"


def test_skill_manage_refuses_symlink_escape(tmp_path):
    from openjarvis.tools.skill_manage import SkillManageTool

    skills = tmp_path / "skills"
    skills.mkdir()
    victim = tmp_path / "victim.toml"
    victim.write_text("ORIGINAL")
    link = skills / "evil.toml"
    link.symlink_to(victim)
    tool = SkillManageTool(skills_dir=skills)
    result = tool.execute(action="load", name="evil")
    assert not result.success
    assert "Access denied" in result.content
    assert victim.read_text() == "ORIGINAL"
    # Traversal names are rejected outright.
    result = tool.execute(action="create", name="../escape", description="x", steps=[])
    assert not result.success
    assert "Invalid skill name" in result.content


def test_open_for_write_never_truncates_swapped_victim(tmp_path):
    """Regression: O_TRUNC must not fire before the dev/ino check."""
    from openjarvis.security.canonical_path import (
        UnsafePathError,
        open_for_write_within,
    )

    root = tmp_path / "root"
    root.mkdir()
    target = root / "t.txt"
    target.write_text("VICTIM-BYTES")
    victim = tmp_path / "victim.txt"
    victim.write_text("VICTIM-BYTES")

    # Simulate a swap: replace target with a symlink to victim just
    # before the open. open_for_write_within must refuse WITHOUT
    # truncating the victim (it opens without O_TRUNC, validates, then
    # ftruncates only the verified fd).
    target.unlink()
    target.symlink_to(victim)
    with pytest.raises(UnsafePathError):
        open_for_write_within(target, [root])
    assert victim.read_text() == "VICTIM-BYTES"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
