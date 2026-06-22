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


def test_check_intake_round_trip_passes_when_words_preserved(tmp_path):
    from check_invariants import check_intake_round_trip

    (tmp_path / "source.txt").write_text(
        "Date: 2026-06-19\n\n"
        "Alice: hello there friend, how are you today\n"
        "Bob: pretty good thanks for asking\n"
    )
    (tmp_path / "normalized.md").write_text(
        "---\n"
        "meeting_slug: x\n"
        "date: 2026-06-19\n"
        "participants: [Alice, Bob]\n"
        "chunks: 1\n"
        "format_warning: null\n"
        "---\n\n"
        "<!-- chunk 1/1 -->\n"
        "<!-- t=00:00 -->\n"
        "Alice: hello there friend, how are you today\n"
        "<!-- t=00:05 -->\n"
        "Bob: pretty good thanks for asking\n"
    )
    assert check_intake_round_trip(tmp_path) == []


def test_check_intake_round_trip_flags_silent_content_loss(tmp_path):
    from check_invariants import check_intake_round_trip

    (tmp_path / "source.txt").write_text("Alice: " + "word " * 100)
    (tmp_path / "normalized.md").write_text(
        "---\n"
        "meeting_slug: x\n"
        "participants: [Alice]\n"
        "chunks: 1\n"
        "format_warning: null\n"
        "---\n\n"
        "<!-- chunk 1/1 -->\n"
        "Alice: " + "word " * 10 + "\n"
    )
    violations = check_intake_round_trip(tmp_path)
    assert any("intake round-trip" in v.message for v in violations)


def test_check_intake_round_trip_skips_decorative_separators_and_header(tmp_path):
    """The dental clinic transcript had `========` separators and a Date/
    Duration/Participants header — the word counter should skip them so
    they don't inflate the source count."""
    from check_invariants import _word_count

    src = (
        "============================================================\n"
        "Discovery Call: Mehta Dental Care\n"
        "Date: 2026-06-18\n"
        "Duration: 58 minutes\n"
        "Participants:\n"
        "  - Dr. Mehta (Principal Dentist)\n"
        "\n"
        "[00:00] Arjun: real content begins here\n"
    )
    assert _word_count(src) > 0
    # Header lines are stripped; counter < naive split.
    assert _word_count(src) < len(src.split())


def test_check_outline_passes_on_clean_input(tmp_path):
    from check_invariants import check_outline

    p = tmp_path / "outline.md"
    p.write_text(textwrap.dedent("""
        ---
        source: normalized.md
        chunks_covered: 2
        themes: 1
        entities: 1
        costs: 1
        commitments: 1
        walk_backs: 1
        ---

        ## Themes
        - T1: After-hours phone gap — chunks [1, 2]

        ## Named entities
        - Mrs. Banerjee — 10-year patient lost; intro chunk 1 (t=03:11)

        ## Named costs
        - 1 hour/evening on confirmation calls (Priya, t=06:44)

        ## Commitments
        - Thursday 4 PM follow-up call (t=35:54)

        ## Walk-backs
        - Marathi support — asked at chunk 1 (t=10:04) — walked back to "Hindi covers them" at chunk 1 (t=10:30)
    """).lstrip())
    assert check_outline(p) == []


def test_check_outline_flags_missing_required_section(tmp_path):
    from check_invariants import check_outline

    p = tmp_path / "outline.md"
    p.write_text(textwrap.dedent("""
        ---
        source: normalized.md
        chunks_covered: 1
        themes: 1
        entities: 0
        costs: 0
        commitments: 0
        walk_backs: 0
        ---

        ## Themes
        - T1: Something — chunks [1]
    """).lstrip())
    violations = check_outline(p)
    assert any("Named entities" in v.message for v in violations)
    assert any("Walk-backs" in v.message for v in violations)


def test_check_outline_flags_count_mismatch(tmp_path):
    from check_invariants import check_outline

    p = tmp_path / "outline.md"
    p.write_text(textwrap.dedent("""
        ---
        source: normalized.md
        chunks_covered: 1
        themes: 5
        entities: 0
        costs: 0
        commitments: 0
        walk_backs: 0
        ---

        ## Themes
        - T1: Something — chunks [1]

        ## Named entities

        ## Walk-backs
    """).lstrip())
    violations = check_outline(p)
    assert any("themes=5" in v.message and "1 bullets" in v.message for v in violations)


def test_check_qa_chunks_present_passes(tmp_path):
    from check_invariants import check_qa_chunks_present

    (tmp_path / "normalized.md").write_text(
        "---\nmeeting_slug: x\nparticipants: [A]\nchunks: 2\nformat_warning: null\n---\n\n"
        "<!-- chunk 1/2 -->\nA: hi\n<!-- chunk 2/2 -->\nA: bye\n"
    )
    (tmp_path / "outline.md").write_text("---\nsource: normalized.md\n---\n## Themes\n")
    qa_chunks = tmp_path / "qa-chunks"
    qa_chunks.mkdir()
    (qa_chunks / "qa-1.md").write_text("---\n---\n")
    (qa_chunks / "qa-2.md").write_text("---\n---\n")
    assert check_qa_chunks_present(tmp_path) == []


def test_check_qa_chunks_present_flags_missing_chunk_file(tmp_path):
    from check_invariants import check_qa_chunks_present

    (tmp_path / "normalized.md").write_text(
        "---\nmeeting_slug: x\nparticipants: [A]\nchunks: 2\nformat_warning: null\n---\n\n"
        "<!-- chunk 1/2 -->\nA: hi\n<!-- chunk 2/2 -->\nA: bye\n"
    )
    (tmp_path / "outline.md").write_text("---\nsource: normalized.md\n---\n## Themes\n")
    qa_chunks = tmp_path / "qa-chunks"
    qa_chunks.mkdir()
    (qa_chunks / "qa-1.md").write_text("---\n---\n")
    # qa-2.md missing
    violations = check_qa_chunks_present(tmp_path)
    assert any("qa-2.md" in v.message for v in violations)


def test_check_qa_chunks_present_skips_when_no_outline(tmp_path):
    """Legacy meeting folders without outline.md aren't expected to have qa-chunks/."""
    from check_invariants import check_qa_chunks_present

    (tmp_path / "normalized.md").write_text(
        "---\nmeeting_slug: x\nchunks: 2\nformat_warning: null\nparticipants: [A]\n---\n"
    )
    assert check_qa_chunks_present(tmp_path) == []


def test_check_walk_back_coverage_passes_when_counts_match(tmp_path):
    from check_invariants import check_walk_back_coverage

    (tmp_path / "outline.md").write_text(
        "---\nsource: normalized.md\nchunks_covered: 1\nthemes: 0\nentities: 0\ncosts: 0\ncommitments: 0\nwalk_backs: 3\n---\n"
    )
    (tmp_path / "qa.md").write_text(
        "---\nsource: qa-chunks/\nchunks_merged: 1\nqa_before_dedup: 3\nqa_after_dedup: 3\ndropped: 0\nwalk_backs_resolved: 3\n---\n"
    )
    assert check_walk_back_coverage(tmp_path) == []


def test_check_walk_back_coverage_flags_mismatch(tmp_path):
    from check_invariants import check_walk_back_coverage

    (tmp_path / "outline.md").write_text(
        "---\nsource: normalized.md\nchunks_covered: 1\nthemes: 0\nentities: 0\ncosts: 0\ncommitments: 0\nwalk_backs: 3\n---\n"
    )
    (tmp_path / "qa.md").write_text(
        "---\nsource: qa-chunks/\nchunks_merged: 1\nqa_before_dedup: 3\nqa_after_dedup: 3\ndropped: 0\nwalk_backs_resolved: 1\n---\n"
    )
    violations = check_walk_back_coverage(tmp_path)
    assert any("3 walk-backs" in v.message and "1" in v.message for v in violations)


def test_check_qa_supports_reconciled_schema(tmp_path):
    """The reconciler-output qa.md uses a different frontmatter shape:
    chunks_merged / qa_before_dedup / qa_after_dedup / walk_backs_resolved
    instead of chunks_processed / total_qa. The schema is auto-detected."""
    from check_invariants import check_qa

    p = tmp_path / "qa.md"
    p.write_text(textwrap.dedent("""
        ---
        source: qa-chunks/
        chunks_merged: 2
        qa_before_dedup: 3
        qa_after_dedup: 2
        dropped: 0
        walk_backs_resolved: 1
        ---

        ### Q1 — Sample (lens: problem in life) [MERGED across chunks 1 and 2]
        **Answer:** ans.
        **Confidence:** grounded
        **Chunks:** 1, 2
        **Quotes:**
        - Speaker: "verbatim text here"

        ### Q2 — Other (lens: cost of doing nothing)
        **Answer:** ans.
        **Confidence:** grounded
        **Chunks:** 2
        **Quotes:**
        - Speaker: "another quote"
    """).lstrip())
    violations = check_qa(p)
    assert violations == []


def test_check_qa_flags_walk_back_coverage_gaps_in_qa_body(tmp_path):
    from check_invariants import check_qa

    p = tmp_path / "qa.md"
    p.write_text(textwrap.dedent("""
        ---
        source: qa-chunks/
        chunks_merged: 2
        qa_before_dedup: 1
        qa_after_dedup: 1
        dropped: 0
        walk_backs_resolved: 0
        ---

        ### Q1 — Sample (lens: problem in life)
        **Answer:** ans.
        **Confidence:** grounded
        **Chunks:** 1
        **Quotes:**
        - Speaker: "verbatim text here"

        ## Walk-back coverage gaps
        - Marathi support — ask at chunk 1 (t=10:04) found, retraction at chunk 1 (t=10:30) not found in any output Q&A
    """).lstrip())
    violations = check_qa(p)
    assert any("uncovered walk-back" in v.message.lower() for v in violations)


def test_check_devrev_files_skipped_when_no_devrev_dir(tmp_path):
    """devrev/ is optional — when absent, no checks fire."""
    from check_invariants import check_devrev_files

    assert check_devrev_files(tmp_path) == []


def test_check_devrev_files_passes_on_clean_pair(tmp_path):
    from check_invariants import check_devrev_files

    tickets = tmp_path / "tickets"
    devrev = tmp_path / "devrev"
    tickets.mkdir()
    devrev.mkdir()
    (tickets / "01-foo.md").write_text("---\ntype: feature\n---\n# Foo\n")
    (devrev / "01-foo.md").write_text(textwrap.dedent("""
        ---
        type: feature_request
        severity: high
        source_meeting: x
        source_ticket: ../tickets/01-foo.md
        ---

        # Foo

        ## Summary
        Body.

        ## Acceptance criteria
        - [ ] Done when X.

        ## Top evidence
        > Speaker: "quote"

        ## Source
        - PM-review ticket: ../tickets/01-foo.md
    """).lstrip())
    assert check_devrev_files(tmp_path) == []


def test_check_devrev_files_flags_missing_companion(tmp_path):
    from check_invariants import check_devrev_files

    tickets = tmp_path / "tickets"
    devrev = tmp_path / "devrev"
    tickets.mkdir()
    devrev.mkdir()
    (tickets / "01-foo.md").write_text("---\ntype: feature\n---\n# Foo\n")
    (tickets / "02-bar.md").write_text("---\ntype: task\n---\n# Bar\n")
    # Only one devrev file — 02 is missing
    (devrev / "01-foo.md").write_text(textwrap.dedent("""
        ---
        type: feature_request
        severity: high
        source_meeting: x
        source_ticket: ../tickets/01-foo.md
        ---

        # Foo

        ## Summary
        Body.

        ## Acceptance criteria
        - [ ] Done.

        ## Top evidence
        > Speaker: "quote"

        ## Source
        - PM-review ticket: ../tickets/01-foo.md
    """).lstrip())
    violations = check_devrev_files(tmp_path)
    assert any("02-bar.md" in v.message for v in violations)


def test_check_devrev_files_flags_invalid_type(tmp_path):
    from check_invariants import check_devrev_files

    tickets = tmp_path / "tickets"
    devrev = tmp_path / "devrev"
    tickets.mkdir()
    devrev.mkdir()
    (tickets / "01-foo.md").write_text("---\ntype: feature\n---\n# Foo\n")
    (devrev / "01-foo.md").write_text(textwrap.dedent("""
        ---
        type: feature
        severity: high
        source_meeting: x
        source_ticket: ../tickets/01-foo.md
        ---

        # Foo

        ## Summary
        Body.

        ## Acceptance criteria
        - [ ] Done.

        ## Top evidence
        > Speaker: "quote"

        ## Source
        - PM-review ticket: ../tickets/01-foo.md
    """).lstrip())
    violations = check_devrev_files(tmp_path)
    assert any(
        "type='feature'" in v.message and "feature_request" in v.message
        for v in violations
    )


def test_check_devrev_files_flags_missing_section(tmp_path):
    from check_invariants import check_devrev_files

    tickets = tmp_path / "tickets"
    devrev = tmp_path / "devrev"
    tickets.mkdir()
    devrev.mkdir()
    (tickets / "01-foo.md").write_text("---\ntype: feature\n---\n# Foo\n")
    (devrev / "01-foo.md").write_text(textwrap.dedent("""
        ---
        type: feature_request
        severity: high
        source_meeting: x
        source_ticket: ../tickets/01-foo.md
        ---

        # Foo

        ## Summary
        Body.

        ## Acceptance criteria
        - [ ] Done.

        ## Source
        - PM-review ticket: ../tickets/01-foo.md
    """).lstrip())
    violations = check_devrev_files(tmp_path)
    assert any("Top evidence" in v.message for v in violations)


def test_check_devrev_files_flags_source_ticket_pointing_nowhere(tmp_path):
    from check_invariants import check_devrev_files

    tickets = tmp_path / "tickets"
    devrev = tmp_path / "devrev"
    tickets.mkdir()
    devrev.mkdir()
    (tickets / "01-foo.md").write_text("---\ntype: feature\n---\n# Foo\n")
    (devrev / "01-foo.md").write_text(textwrap.dedent("""
        ---
        type: feature_request
        severity: high
        source_meeting: x
        source_ticket: ../tickets/99-nonexistent.md
        ---

        # Foo

        ## Summary
        Body.

        ## Acceptance criteria
        - [ ] Done.

        ## Top evidence
        > Speaker: "quote"

        ## Source
        - PM-review ticket: ../tickets/01-foo.md
    """).lstrip())
    violations = check_devrev_files(tmp_path)
    assert any("99-nonexistent.md" in v.message for v in violations)


def test_check_no_internal_scaffolding_passes_clean_ticket(tmp_path):
    from check_invariants import check_no_internal_scaffolding_in_ticket_prose

    p = tmp_path / "ticket.md"
    p.write_text(textwrap.dedent("""
        ---
        type: feature
        priority_hint: medium
        source_meeting: x
        cluster_id: C3
        ---

        # Some title

        ## Business goal
        Strategic outcome described without internal jargon.

        ## Description
        Body without scaffolding references.

        > Speaker: "verbatim"

        ## Acceptance criteria
        - [ ] Criterion one.

        ## Evidence
        - qa.md → Q1, Q2, Q5
        - normalized.md chunk 1
    """).lstrip())
    assert check_no_internal_scaffolding_in_ticket_prose(p) == []


def test_check_no_internal_scaffolding_flags_cluster_id_in_business_goal(tmp_path):
    from check_invariants import check_no_internal_scaffolding_in_ticket_prose

    p = tmp_path / "ticket.md"
    p.write_text(textwrap.dedent("""
        ---
        type: feature
        priority_hint: medium
        source_meeting: x
        cluster_id: C3
        ---

        # Title

        ## Business goal
        Unblocks C1 which is the headline feature.

        ## Description
        Body.

        > Speaker: "verbatim"

        ## Acceptance criteria
        - [ ] Criterion.

        ## Evidence
        - qa.md → Q1
    """).lstrip())
    violations = check_no_internal_scaffolding_in_ticket_prose(p)
    assert any("Business goal" in v.message and "'C1'" in v.message for v in violations)


def test_check_no_internal_scaffolding_flags_q_id_in_description(tmp_path):
    from check_invariants import check_no_internal_scaffolding_in_ticket_prose

    p = tmp_path / "ticket.md"
    p.write_text(textwrap.dedent("""
        ---
        type: feature
        priority_hint: medium
        source_meeting: x
        cluster_id: C1
        ---

        # Title

        ## Business goal
        Strategic outcome.

        ## Description
        This builds on Q5's evidence about cost.

        > Speaker: "verbatim"

        ## Acceptance criteria
        - [ ] Criterion.

        ## Evidence
        - qa.md → Q1, Q5
    """).lstrip())
    violations = check_no_internal_scaffolding_in_ticket_prose(p)
    assert any("Description" in v.message and "'Q5'" in v.message for v in violations)


def test_check_no_internal_scaffolding_allows_evidence_section(tmp_path):
    """The Evidence section is explicitly exempt — that's where Q-ids belong."""
    from check_invariants import check_no_internal_scaffolding_in_ticket_prose

    p = tmp_path / "ticket.md"
    p.write_text(textwrap.dedent("""
        ---
        type: feature
        priority_hint: medium
        source_meeting: x
        cluster_id: C2
        ---

        # Title

        ## Business goal
        Strategic outcome.

        ## Description
        Clean prose.

        > Speaker: "verbatim"

        ## Acceptance criteria
        - [ ] Criterion.

        ## Evidence
        - qa.md → Q1, Q2, Q5, Q12
        - normalized.md chunk 1
        - normalized.md chunk 2
    """).lstrip())
    assert check_no_internal_scaffolding_in_ticket_prose(p) == []


def test_check_no_internal_scaffolding_allows_q1_inside_verbatim_blockquote(tmp_path):
    """Transcript quotes are verbatim and may legitimately contain "Q1"
    (calendar Q1), "C-suite", etc. The check exempts blockquote lines."""
    from check_invariants import check_no_internal_scaffolding_in_ticket_prose

    p = tmp_path / "ticket.md"
    p.write_text(textwrap.dedent("""
        ---
        type: feature
        priority_hint: medium
        source_meeting: x
        cluster_id: C2
        ---

        # Title

        ## Business goal
        Strategic outcome, no scaffolding.

        ## Description
        Body without scaffolding in the drafter's prose.

        > Priya: "We had an incident in Q1 where a contractor's account was still active."

        ## Acceptance criteria
        - [ ] Criterion.

        ## Evidence
        - qa.md → Q1
    """).lstrip())
    assert check_no_internal_scaffolding_in_ticket_prose(p) == []


def test_check_no_internal_scaffolding_allows_frontmatter(tmp_path):
    """cluster_id: C3 in frontmatter is fine — that's where it belongs."""
    from check_invariants import check_no_internal_scaffolding_in_ticket_prose

    p = tmp_path / "ticket.md"
    p.write_text(textwrap.dedent("""
        ---
        type: feature
        priority_hint: medium
        source_meeting: x
        cluster_id: C7
        ---

        # Title

        ## Business goal
        Strategic outcome.

        ## Description
        Clean.

        > Speaker: "verbatim"

        ## Acceptance criteria
        - [ ] Criterion.

        ## Evidence
        - qa.md → Q1
    """).lstrip())
    assert check_no_internal_scaffolding_in_ticket_prose(p) == []


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
