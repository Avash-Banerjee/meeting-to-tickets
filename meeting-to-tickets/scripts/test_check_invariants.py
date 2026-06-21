from __future__ import annotations

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


def test_check_normalized_flags_non_integer_chunks(tmp_path):
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


def test_check_normalized_flags_unparseable_yaml(tmp_path):
    # Mismatched quote inside an unquoted scalar produces a YAMLError.
    p = _write(tmp_path, "normalized.md", """
        ---
        meeting_slug: "x
        chunks: 1
        ---

        Alice: hello.
    """)
    violations = check_normalized(p)
    assert any("no parseable YAML frontmatter" in v.message for v in violations)


from check_invariants import (
    check_qa,
    check_clusters,
    check_ticket,
    check_quote_provenance,
    check_ticket_cluster_counts,
)


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


def test_check_qa_flags_total_qa_mismatch(tmp_path):
    # frontmatter claims 2 Q&As but only 1 is present in the body.
    p = _write(tmp_path, "qa.md", """
        ---
        source: normalized.md
        chunks_processed: 1
        total_qa: 2
        dropped: 0
        ---

        ### Q1 — Title (lens: problem in life)
        **Answer:** ans.
        **Confidence:** grounded
        **Chunk:** 1
        **Quotes:**
        - Priya: "verbatim text"
    """)
    violations = check_qa(p)
    assert any("total_qa" in v.message for v in violations)


def test_check_qa_flags_dropped_count_mismatch(tmp_path):
    # frontmatter claims dropped=2 but the Dropped section has one entry.
    p = _write(tmp_path, "qa.md", """
        ---
        source: normalized.md
        chunks_processed: 1
        total_qa: 0
        dropped: 2
        ---

        ## Dropped
        - Q (proposed): "single entry" — reason given here.
    """)
    violations = check_qa(p)
    assert any("dropped" in v.message.lower() and "count" in v.message.lower() for v in violations)


def test_check_clusters_flags_unknown_qa_reference(tmp_path):
    # Cluster references Q7 but qa.md has no Q7 — when called with the qa-id set.
    p = _write(tmp_path, "clusters.md", """
        ---
        total_clusters: 1
        unclustered_qa: 0
        ---

        ## C1 — Theme (suggested type: feature)
        **Rationale:** because.
        **Q&A:** Q1, Q7
    """)
    violations = check_clusters(p, qa_ids={"Q1"})
    assert any("Q7" in v.message for v in violations)


def test_check_clusters_passes_when_qa_ids_match(tmp_path):
    p = _write(tmp_path, "clusters.md", """
        ---
        total_clusters: 1
        unclustered_qa: 0
        ---

        ## C1 — Theme (suggested type: feature)
        **Rationale:** because.
        **Q&A:** Q1, Q2
    """)
    assert check_clusters(p, qa_ids={"Q1", "Q2"}) == []


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

        ## Evidence
        - qa.md -> Q1
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


def test_check_ticket_missing_key_does_not_double_report(tmp_path):
    # `type` is missing entirely — we should see ONE violation about the
    # missing key, not also a "invalid type: None" follow-up.
    p = _write(tmp_path, "01-x.md", """
        ---
        priority_hint: medium
        source_meeting: clean-short
        cluster_id: C1
        ---

        # Title

        ## Description
        > Priya: "verbatim quote"

        ## Acceptance criteria
        - [ ] (inferred) Criterion one
    """)
    violations = check_ticket(p)
    type_messages = [v.message for v in violations if "type" in v.message]
    assert len(type_messages) == 1
    assert "missing required key: type" in type_messages[0]


def test_check_ticket_flags_non_inferred_ac_without_evidence(tmp_path):
    # AC bullet does NOT start with "(inferred)" and there's no Evidence
    # section referencing a Q&A id -> traceability violation.
    p = _write(tmp_path, "01-x.md", """
        ---
        type: feature
        priority_hint: medium
        source_meeting: clean-short
        cluster_id: C1
        ---

        # Title

        ## Description
        > Priya: "verbatim quote"

        ## Acceptance criteria
        - [ ] User can do thing.
    """)
    violations = check_ticket(p)
    assert any("trace" in v.message.lower() or "evidence" in v.message.lower() for v in violations)


def test_check_ticket_passes_when_all_ac_inferred(tmp_path):
    # All ACs are explicitly (inferred) so no Evidence is required.
    p = _write(tmp_path, "01-x.md", """
        ---
        type: feature
        priority_hint: medium
        source_meeting: clean-short
        cluster_id: C1
        ---

        # Title

        ## Description
        > Priya: "verbatim quote"

        ## Acceptance criteria
        - [ ] (inferred) Criterion one
        - [x] (inferred) Criterion two
    """)
    assert check_ticket(p) == []


def test_check_ticket_passes_when_evidence_references_qa(tmp_path):
    p = _write(tmp_path, "01-x.md", """
        ---
        type: feature
        priority_hint: medium
        source_meeting: clean-short
        cluster_id: C1
        ---

        # Title

        ## Description
        > Priya: "verbatim quote"

        ## Acceptance criteria
        - [ ] User can export.
        - [ ] (inferred) Column order matches finance.

        ## Evidence
        - qa.md -> Q1, Q3
    """)
    assert check_ticket(p) == []


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


# ----- quote-provenance + ticket-cluster-count tests -----


def _scaffold_meeting(tmp_path: pathlib.Path, normalized_body: str, *, qa: str | None = None,
                     tickets: dict[str, str] | None = None,
                     clusters: str | None = None,
                     dropped: str | None = None) -> pathlib.Path:
    """Write a minimal meeting folder for cross-file checks."""
    folder = tmp_path / "meeting"
    folder.mkdir()
    (folder / "normalized.md").write_text(textwrap.dedent(normalized_body).lstrip("\n"))
    if qa is not None:
        (folder / "qa.md").write_text(textwrap.dedent(qa).lstrip("\n"))
    if clusters is not None:
        (folder / "clusters.md").write_text(textwrap.dedent(clusters).lstrip("\n"))
    if dropped is not None:
        (folder / "dropped.md").write_text(textwrap.dedent(dropped).lstrip("\n"))
    if tickets is not None:
        (folder / "tickets").mkdir()
        for name, body in tickets.items():
            (folder / "tickets" / name).write_text(textwrap.dedent(body).lstrip("\n"))
    return folder


def test_check_quote_provenance_passes_when_ticket_quote_in_transcript(tmp_path):
    folder = _scaffold_meeting(
        tmp_path,
        """
        ---
        meeting_slug: x
        participants: [Priya]
        chunks: 1
        format_warning: null
        ---

        <!-- chunk 1/1 -->
        Priya: I open the dashboard, screenshot it, then retype the numbers.
        """,
        tickets={
            "01-x.md": """
                ---
                type: feature
                priority_hint: medium
                source_meeting: x
                cluster_id: C1
                ---

                # T

                ## Description
                > Priya: "I open the dashboard, screenshot it, then retype the numbers."

                ## Acceptance criteria
                - [ ] (inferred) Something.
            """,
        },
    )
    assert check_quote_provenance(folder) == []


def test_check_quote_provenance_flags_fabricated_ticket_quote(tmp_path):
    folder = _scaffold_meeting(
        tmp_path,
        """
        ---
        meeting_slug: x
        participants: [Priya]
        chunks: 1
        format_warning: null
        ---

        <!-- chunk 1/1 -->
        Priya: I open the dashboard, screenshot it.
        """,
        tickets={
            "01-x.md": """
                ---
                type: feature
                priority_hint: medium
                source_meeting: x
                cluster_id: C1
                ---

                # T

                ## Description
                > Priya: "totally fabricated phrase not in transcript"

                ## Acceptance criteria
                - [ ] (inferred) Something.
            """,
        },
    )
    violations = check_quote_provenance(folder)
    assert any("not found" in v.message.lower() or "no matching" in v.message.lower()
               for v in violations)


def test_check_quote_provenance_tolerates_smart_quotes(tmp_path):
    # Transcript uses straight quotes; ticket uses curly quotes.
    folder = _scaffold_meeting(
        tmp_path,
        """
        ---
        meeting_slug: x
        participants: [Priya]
        chunks: 1
        format_warning: null
        ---

        <!-- chunk 1/1 -->
        Priya: We tried a shared Notion page last quarter.
        """,
        tickets={
            "01-x.md": """
                ---
                type: feature
                priority_hint: medium
                source_meeting: x
                cluster_id: C1
                ---

                # T

                ## Description
                > Priya: “We tried a shared Notion page last quarter.”

                ## Acceptance criteria
                - [ ] (inferred) Something.
            """,
        },
    )
    assert check_quote_provenance(folder) == []


def test_check_quote_provenance_flags_fabricated_qa_quote(tmp_path):
    folder = _scaffold_meeting(
        tmp_path,
        """
        ---
        meeting_slug: x
        participants: [Priya]
        chunks: 1
        format_warning: null
        ---

        <!-- chunk 1/1 -->
        Priya: Reporting first.
        """,
        qa="""
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
            - Priya: "this phrase does not appear in the transcript"
        """,
    )
    violations = check_quote_provenance(folder)
    assert any("Q1" in v.message for v in violations)


def test_check_ticket_cluster_counts_passes_when_balanced(tmp_path):
    folder = _scaffold_meeting(
        tmp_path,
        """
        ---
        meeting_slug: x
        participants: [Priya]
        chunks: 1
        format_warning: null
        ---

        <!-- chunk 1/1 -->
        Priya: hi.
        """,
        clusters="""
            ---
            total_clusters: 2
            unclustered_qa: 0
            ---

            ## C1 — Theme (suggested type: feature)
            **Q&A:** Q1
            ## C2 — Other (suggested type: feature)
            **Q&A:** Q2
        """,
        dropped="""
            # Dropped clusters

            - C2 — dropped because no behavioural evidence.
        """,
        tickets={
            "01-a.md": """
                ---
                type: feature
                priority_hint: medium
                source_meeting: x
                cluster_id: C1
                ---

                ## Description
                > Priya: "hi."

                ## Acceptance criteria
                - [ ] (inferred) Something.
            """,
        },
    )
    assert check_ticket_cluster_counts(folder) == []


def test_check_ticket_cluster_counts_flags_imbalance(tmp_path):
    folder = _scaffold_meeting(
        tmp_path,
        """
        ---
        meeting_slug: x
        participants: [Priya]
        chunks: 1
        format_warning: null
        ---

        <!-- chunk 1/1 -->
        Priya: hi.
        """,
        clusters="""
            ---
            total_clusters: 3
            unclustered_qa: 0
            ---

            ## C1 — A (suggested type: feature)
            **Q&A:** Q1
            ## C2 — B (suggested type: feature)
            **Q&A:** Q2
            ## C3 — C (suggested type: feature)
            **Q&A:** Q3
        """,
        tickets={
            "01-a.md": """
                ---
                type: feature
                priority_hint: medium
                source_meeting: x
                cluster_id: C1
                ---

                ## Description
                > Priya: "hi."

                ## Acceptance criteria
                - [ ] (inferred) Something.
            """,
        },
    )
    violations = check_ticket_cluster_counts(folder)
    assert any("ticket" in v.message.lower() and "cluster" in v.message.lower() for v in violations)
