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


from check_invariants import check_qa, check_clusters, check_ticket


def test_check_qa_passes_on_clean_input(tmp_path):
    p = _write(tmp_path, "qa.md", """
        ---
        source: normalized.md
        chunks_processed: 1
        total_qa: 1
        dropped: 0
        ---

        ### Q1 — Title (lens: problem in life)
        **Answer:** ans.
        **Confidence:** grounded
        **Chunk:** 1
        **Quotes:**
        - Priya: "verbatim text here"
    """)
    assert check_qa(p) == []


def test_check_qa_flags_qa_without_quote(tmp_path):
    p = _write(tmp_path, "qa.md", """
        ---
        source: normalized.md
        chunks_processed: 1
        total_qa: 1
        dropped: 0
        ---

        ### Q1 — Title (lens: problem in life)
        **Answer:** ans.
        **Confidence:** grounded
        **Chunk:** 1
    """)
    violations = check_qa(p)
    assert any("quote" in v.message.lower() for v in violations)


def test_check_qa_flags_dropped_without_reason(tmp_path):
    p = _write(tmp_path, "qa.md", """
        ---
        source: normalized.md
        chunks_processed: 1
        total_qa: 0
        dropped: 1
        ---

        ## Dropped
        - Q (proposed): "no reason here"
    """)
    violations = check_qa(p)
    assert any("reason" in v.message.lower() for v in violations)


def test_check_clusters_passes_on_clean_input(tmp_path):
    p = _write(tmp_path, "clusters.md", """
        ---
        total_clusters: 1
        unclustered_qa: 0
        ---

        ## C1 — Theme (suggested type: feature)
        **Rationale:** because.
        **Q&A:** Q1
    """)
    assert check_clusters(p) == []


def test_check_clusters_flags_bad_type(tmp_path):
    p = _write(tmp_path, "clusters.md", """
        ---
        total_clusters: 1
        unclustered_qa: 0
        ---

        ## C1 — Theme (suggested type: epic)
        **Rationale:** because.
        **Q&A:** Q1
    """)
    violations = check_clusters(p)
    assert any("type" in v.message.lower() for v in violations)


def test_check_ticket_passes_on_clean_input(tmp_path):
    p = _write(tmp_path, "01-x.md", """
        ---
        type: feature
        priority_hint: medium
        source_meeting: clean-short
        cluster_id: C1
        ---

        # Title

        ## Description
        Body with evidence.

        > Priya: "verbatim quote"

        ## Acceptance criteria
        - [ ] Criterion one
        - [ ] (inferred) Criterion two
    """)
    assert check_ticket(p) == []


def test_check_ticket_flags_missing_blockquote(tmp_path):
    p = _write(tmp_path, "01-x.md", """
        ---
        type: feature
        priority_hint: medium
        source_meeting: clean-short
        cluster_id: C1
        ---

        # Title

        ## Description
        Body.

        ## Acceptance criteria
        - [ ] Criterion one
    """)
    violations = check_ticket(p)
    assert any("quote" in v.message.lower() for v in violations)


def test_check_ticket_flags_bad_type(tmp_path):
    p = _write(tmp_path, "01-x.md", """
        ---
        type: epic
        priority_hint: medium
        source_meeting: clean-short
        cluster_id: C1
        ---

        # Title

        ## Description
        > Priya: "verbatim quote"

        ## Acceptance criteria
        - [ ] Criterion one
    """)
    violations = check_ticket(p)
    assert any("type" in v.message.lower() for v in violations)
