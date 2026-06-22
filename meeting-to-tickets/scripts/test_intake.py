"""Tests for scripts/intake.py — deterministic transcript normalization."""
from __future__ import annotations

import pathlib
import textwrap

import pytest

from intake import (
    Utterance,
    canonicalize_utterances,
    chunk_utterances,
    detect_format,
    infer_participants,
    normalize_text,
    parse_bracketed_ts,
    parse_header,
    parse_labeled,
    parse_srt,
    parse_unknown,
    parse_vtt,
)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


def test_detect_vtt():
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nAlice: hi\n"
    assert detect_format(text) == "vtt"


def test_detect_srt():
    text = "1\n00:00:00,000 --> 00:00:02,000\nAlice: hi\n"
    assert detect_format(text) == "srt"


def test_detect_bracketed_ts_mm_ss():
    text = "[02:21] Priya: hello\n"
    assert detect_format(text) == "bracketed-ts"


def test_detect_bracketed_ts_hh_mm_ss():
    text = "[00:02:21] Priya: hello\n"
    assert detect_format(text) == "bracketed-ts"


def test_detect_labeled_no_timestamps():
    text = "Alice: hello there\nBob: hi back\n"
    assert detect_format(text) == "labeled"


def test_detect_unknown():
    text = "just a paragraph with no structure at all\n"
    assert detect_format(text) == "unknown"


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------


def test_parse_header_inline_participants():
    text = textwrap.dedent("""
        Date: 2026-06-18
        Participants: Alice, Bob, Priya

        Alice: hello
    """).lstrip()
    h = parse_header(text)
    assert h.date == "2026-06-18"
    assert h.participants == ["Alice", "Bob", "Priya"]


def test_parse_header_bulleted_participants_with_roles():
    text = textwrap.dedent("""
        Discovery Call
        Date: 2026-06-18
        Participants:
          - Dr. Mehta (Principal Dentist)
          - Priya (Office Manager)
          - Arjun (Founder)

        Arjun: hi
    """).lstrip()
    h = parse_header(text)
    assert h.date == "2026-06-18"
    assert h.participants == ["Dr. Mehta", "Priya", "Arjun"]


def test_parse_header_no_date_no_participants():
    text = "Alice: hello\n"
    h = parse_header(text)
    assert h.date is None
    assert h.participants == []


# ---------------------------------------------------------------------------
# Bracketed-timestamp parser (the dental clinic shape)
# ---------------------------------------------------------------------------


def test_bracketed_ts_basic():
    text = textwrap.dedent("""
        [00:00] Alice: hello there
        [00:04] Bob: hi
    """).lstrip()
    utts = parse_bracketed_ts(text)
    assert len(utts) == 2
    assert utts[0] == Utterance("00:00", "Alice", "hello there")
    assert utts[1] == Utterance("00:04", "Bob", "hi")


def test_bracketed_ts_drops_end_of_recording_marker():
    text = "[00:00] Alice: hi\n[00:05] [End of recording]: \n"
    utts = parse_bracketed_ts(text)
    assert len(utts) == 1


def test_bracketed_ts_hh_mm_ss_collapses_to_minutes():
    text = "[01:02:21] Alice: late in the call\n"
    utts = parse_bracketed_ts(text)
    # 1 hour 2 minutes = 62 minutes
    assert utts[0].timestamp == "62:21"


# ---------------------------------------------------------------------------
# Labeled (no timestamps) parser
# ---------------------------------------------------------------------------


def test_labeled_basic():
    text = textwrap.dedent("""
        Date: 2026-06-19

        Alice: hello there
        Bob: hi
    """).lstrip()
    utts = parse_labeled(text)
    assert len(utts) == 2
    assert utts[0] == Utterance(None, "Alice", "hello there")
    assert utts[1] == Utterance(None, "Bob", "hi")


def test_labeled_glues_multiline_utterance_to_speaker():
    text = textwrap.dedent("""
        Alice: hello there
        I am continuing the same thought
        Bob: hi
    """).lstrip()
    utts = parse_labeled(text)
    assert len(utts) == 2
    assert utts[0].text == "hello there I am continuing the same thought"


# ---------------------------------------------------------------------------
# VTT parser
# ---------------------------------------------------------------------------


def test_vtt_extracts_speaker_when_inline():
    text = textwrap.dedent("""
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        Alice: hello there

        00:00:05.000 --> 00:00:10.000
        Bob: hi
    """).lstrip()
    utts = parse_vtt(text)
    assert len(utts) == 2
    assert utts[0] == Utterance("00:00", "Alice", "hello there")
    assert utts[1] == Utterance("00:05", "Bob", "hi")


def test_vtt_falls_back_to_unknown_when_no_inline_speaker():
    text = textwrap.dedent("""
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        just text with no speaker label
    """).lstrip()
    utts = parse_vtt(text)
    assert len(utts) == 1
    assert utts[0].speaker == "Unknown"


def test_vtt_hour_collapses_to_minutes_in_timestamp():
    text = textwrap.dedent("""
        WEBVTT

        01:05:00.000 --> 01:05:05.000
        Alice: late
    """).lstrip()
    utts = parse_vtt(text)
    assert utts[0].timestamp == "65:00"


# ---------------------------------------------------------------------------
# SRT parser
# ---------------------------------------------------------------------------


def test_srt_basic():
    text = textwrap.dedent("""
        1
        00:00:00,000 --> 00:00:05,000
        Alice: hi

        2
        00:00:05,000 --> 00:00:10,000
        Bob: hello
    """).lstrip()
    utts = parse_srt(text)
    assert len(utts) == 2
    assert utts[0] == Utterance("00:00", "Alice", "hi")
    assert utts[1] == Utterance("00:05", "Bob", "hello")


# ---------------------------------------------------------------------------
# Unknown-format fallback
# ---------------------------------------------------------------------------


def test_unknown_dumps_under_one_unknown_speaker():
    text = "just some prose with no structure at all here"
    utts = parse_unknown(text)
    assert len(utts) == 1
    assert utts[0].speaker == "Unknown"
    assert "just some prose" in utts[0].text


def test_unknown_strips_leading_header_block():
    text = textwrap.dedent("""
        Date: 2026-06-19

        just some prose without speaker labels
    """).lstrip()
    utts = parse_unknown(text)
    assert utts[0].text.startswith("just some prose")
    assert "Date:" not in utts[0].text


# ---------------------------------------------------------------------------
# Filler collapse
# ---------------------------------------------------------------------------


def test_filler_collapse_leading_only():
    utts = [Utterance("00:00", "Alice", "um hello there")]
    out = canonicalize_utterances(utts)
    assert out[0].text == "hello there"


def test_filler_collapse_does_not_touch_mid_utterance_fillers():
    utts = [Utterance("00:00", "Alice", "hello, um, there")]
    out = canonicalize_utterances(utts)
    assert out[0].text == "hello, um, there"


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def test_chunk_returns_single_chunk_when_under_budget():
    utts = [Utterance("00:00", "A", "hello"), Utterance("00:05", "B", "there")]
    chunks = chunk_utterances(utts, budget_chars=10_000)
    assert len(chunks) == 1
    assert chunks[0] == utts


def test_chunk_splits_at_budget_with_overlap():
    long = "x" * 9_000  # each utterance ~9k chars
    utts = [Utterance("00:00", "A", long), Utterance("00:01", "B", long), Utterance("00:02", "C", long)]
    chunks = chunk_utterances(utts, budget_chars=10_000, overlap=1)
    # Each chunk holds one utterance; overlap means chunk 2 starts with the
    # trailing utterance of chunk 1.
    assert len(chunks) >= 2
    # Overlap: last utterance of chunk N is first utterance of chunk N+1
    for i in range(len(chunks) - 1):
        assert chunks[i][-1] == chunks[i + 1][0]


def test_chunk_never_splits_inside_an_utterance_even_when_oversized():
    huge = "x" * 100_000
    utts = [Utterance("00:00", "A", huge)]
    chunks = chunk_utterances(utts, budget_chars=10_000)
    # Still exactly one chunk containing the one huge utterance.
    assert len(chunks) == 1
    assert chunks[0][0].text == huge


def test_chunk_empty_input():
    chunks = chunk_utterances([], budget_chars=10_000)
    assert chunks == [[]]


# ---------------------------------------------------------------------------
# Participant inference
# ---------------------------------------------------------------------------


def test_infer_participants_preserves_order_of_first_appearance():
    utts = [
        Utterance("00:00", "Bob", "hi"),
        Utterance("00:05", "Alice", "hello"),
        Utterance("00:10", "Bob", "again"),
    ]
    assert infer_participants(utts) == ["Bob", "Alice"]


def test_infer_participants_skips_unknown():
    utts = [Utterance("00:00", "Unknown", "x")]
    assert infer_participants(utts) == ["Unknown"]


def test_infer_participants_handles_mixed():
    utts = [
        Utterance("00:00", "Unknown", "x"),
        Utterance("00:05", "Alice", "y"),
    ]
    assert infer_participants(utts) == ["Alice"]


# ---------------------------------------------------------------------------
# End-to-end normalize_text
# ---------------------------------------------------------------------------


def test_end_to_end_bracketed_ts_produces_canonical_shape():
    text = textwrap.dedent("""
        Date: 2026-06-18
        Participants: Alice, Bob

        [00:00] Alice: hello there
        [00:05] Bob: hi
    """).lstrip()
    out = normalize_text("smoke", text)
    assert out.startswith("---\nmeeting_slug: smoke\n")
    assert "date: 2026-06-18" in out
    assert "participants: [Alice, Bob]" in out
    assert "chunks: 1" in out
    assert "format_warning: null" in out
    assert "<!-- chunk 1/1 -->" in out
    assert "<!-- t=00:00 -->\nAlice: hello there" in out
    assert "<!-- t=00:05 -->\nBob: hi" in out


def test_end_to_end_prose_without_speaker_labels_sets_no_speaker_labels_warning():
    text = "raw prose without any structure at all"
    out = normalize_text("smoke", text)
    # No speaker labels = no_speaker_labels (more specific than unknown_format).
    assert "format_warning: no_speaker_labels" in out
    assert "Unknown: raw prose" in out


def test_end_to_end_labeled_no_timestamps_omits_date_when_absent():
    text = "Alice: hello there\nBob: hi back\n"
    out = normalize_text("smoke", text)
    # No date line in frontmatter when source has no Date: header
    assert "date:" not in out
    assert "Alice: hello there" in out


def test_end_to_end_no_speaker_labels_sets_warning():
    text = "Date: 2026-06-19\n\nrandom prose with no Speaker prefix"
    out = normalize_text("smoke", text)
    # When the body is prose with no recognizable speaker labels, prefer the
    # specific "no_speaker_labels" warning over the broader "unknown_format".
    assert "format_warning: no_speaker_labels" in out
    assert "Unknown: random prose" in out


def test_end_to_end_empty_input_sets_unknown_format_warning():
    # Empty source → no utterances + format unknown → unknown_format warning.
    text = ""
    out = normalize_text("smoke", text)
    assert "format_warning: unknown_format" in out


def test_vtt_multi_speaker_cue_splits_into_two_utterances():
    text = textwrap.dedent("""
        WEBVTT

        00:00:15.000 --> 00:00:24.000
        Alice: Got it. And how often does that come up?
        Priya: Every export.
    """).lstrip()
    utts = parse_vtt(text)
    assert len(utts) == 2
    assert utts[0].speaker == "Alice"
    assert utts[0].timestamp == "00:15"
    assert utts[1].speaker == "Priya"
    assert utts[1].timestamp == "00:15"
