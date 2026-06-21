import pathlib
import textwrap

import pytest

from check_invariants import check_normalized, Violation


def _write(tmp_path: pathlib.Path, name: str, body: str) -> pathlib.Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(body).lstrip("\n"))
    return p


def test_check_normalized_passes_on_clean_input(tmp_path):
    p = _write(tmp_path, "normalized.md", """
        ---
        meeting_slug: x
        date: 2026-06-19
        participants: [Alice, Priya]
        chunks: 1
        format_warning: null
        ---

        <!-- chunk 1/1 -->
        Alice: hello.
        Priya: hi.
    """)
    assert check_normalized(p) == []


def test_check_normalized_flags_missing_required_key(tmp_path):
    p = _write(tmp_path, "normalized.md", """
        ---
        meeting_slug: x
        chunks: 1
        format_warning: null
        ---
        Alice: hello.
    """)
    violations = check_normalized(p)
    assert any("participants" in v.message for v in violations)


def test_check_normalized_flags_missing_chunk_markers_when_multi_chunk(tmp_path):
    p = _write(tmp_path, "normalized.md", """
        ---
        meeting_slug: x
        date: 2026-06-19
        participants: [Alice]
        chunks: 2
        format_warning: null
        ---

        Alice: hello.
    """)
    violations = check_normalized(p)
    assert any("chunk" in v.message.lower() for v in violations)


def test_check_normalized_flags_invalid_yaml(tmp_path):
    p = _write(tmp_path, "normalized.md", """
        ---
        meeting_slug: x
        chunks: not-an-integer
        participants: [Alice]
        date: 2026-06-19
        format_warning: null
        ---

        Alice: hello.
    """)
    violations = check_normalized(p)
    assert any("chunks" in v.message for v in violations)
