"""Deterministic transcript intake — Path A of the normalization plan.

Replaces the LLM-driven transcript-intake skill with a Python script:
- Detects format (vtt | srt | bracketed-ts | labeled | unknown)
- Parses the header for date / participants
- Converts each utterance to `Speaker: text` with a `<!-- t=MM:SS -->` comment
- Chunks at utterance boundaries when the body exceeds a soft budget,
  with a 1-utterance overlap between chunks
- Emits `meetings/<slug>/normalized.md` with the canonical frontmatter

This module is the Phase-2 backend boundary the design doc described — the
mechanical rules now live in code, not in a prompt.

Usage:
    python scripts/intake.py meetings/<slug>/
"""
from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import sys
from typing import Iterable


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# Chunk soft budget in characters. ~4 chars/token, so 32_000 chars ≈ 8000 tokens.
# Single source of truth for downstream stages and tests.
DEFAULT_CHUNK_CHAR_BUDGET = 32_000

# Overlap between consecutive chunks, in number of trailing utterances.
DEFAULT_CHUNK_OVERLAP = 1

# Leading filler tokens collapsed from the start of an utterance only.
LEADING_FILLERS = ("um", "uh", "you know", "like")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Utterance:
    timestamp: str | None  # "MM:SS" or None when source has no timestamps
    speaker: str
    text: str


@dataclasses.dataclass(frozen=True)
class Header:
    date: str | None  # "YYYY-MM-DD"
    participants: list[str]  # may be empty if not in header


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


_BRACKETED_TS_RE = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]", re.MULTILINE)
_PAREN_TS_RE = re.compile(r"^\((\d{1,2}:\d{2})\)", re.MULTILINE)
_LABEL_AT_START_RE = re.compile(r"^([A-Z][A-Za-z .'-]*):", re.MULTILINE)
_SRT_CUE_RE = re.compile(
    r"^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}",
    re.MULTILINE,
)

# Header keys we never treat as a speaker label, regardless of capitalization.
_HEADER_KEYS = {
    "date",
    "participants",
    "participant",
    "time",
    "duration",
    "meeting",
    "title",
    "subject",
    "recording",
    "transcript",
}


def _is_header_key(label: str) -> bool:
    return label.strip().lower().rstrip(":") in _HEADER_KEYS


def detect_format(text: str) -> str:
    """Return one of: vtt, srt, bracketed-ts, labeled, unknown."""
    stripped = text.lstrip()
    if stripped.startswith("WEBVTT"):
        return "vtt"
    if _SRT_CUE_RE.search(text):
        return "srt"
    if _BRACKETED_TS_RE.search(text) or _PAREN_TS_RE.search(text):
        return "bracketed-ts"
    # "labeled" requires at least one non-header-key Speaker: line.
    for m in _LABEL_AT_START_RE.finditer(text):
        if not _is_header_key(m.group(1)):
            return "labeled"
    return "unknown"


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------


_DATE_LINE_RE = re.compile(r"^\s*Date\s*:\s*(\d{4}-\d{2}-\d{2})\b", re.MULTILINE)
# Same-line content only — `[ \t]*` does NOT consume the newline, so if the
# Participants line has only a colon on it, group(1) is empty and we walk
# the next lines as a bulleted block.
_PARTICIPANTS_LINE_RE = re.compile(
    r"^[ \t]*Participants?[ \t]*:[ \t]*(.*)$", re.MULTILINE
)
_PARTICIPANT_ITEM_RE = re.compile(r"^\s*[-*]\s*(.+?)\s*$")


def _strip_role(name: str) -> str:
    """`Priya (Office Manager)` → `Priya`."""
    return re.sub(r"\s*\(.*\)\s*$", "", name).strip()


def parse_header(text: str) -> Header:
    """Best-effort extraction of meeting date and participants from the top of
    the source file. Both fields are optional — when absent, downstream stages
    receive `None` and `[]`."""

    date_match = _DATE_LINE_RE.search(text)
    date = date_match.group(1) if date_match else None

    participants: list[str] = []
    parts_match = _PARTICIPANTS_LINE_RE.search(text)
    if parts_match:
        inline_rest = parts_match.group(1).strip()
        if inline_rest:
            # Inline form: "Alice, Bob"
            for raw in inline_rest.split(","):
                name = _strip_role(raw.strip())
                if name:
                    participants.append(name)
        else:
            # Block form: walk consecutive bullet lines on subsequent lines.
            after = text[parts_match.end() :]
            for line in after.splitlines():
                if not line.strip():
                    if participants:
                        break
                    # Skip a single leading blank between the colon and the
                    # first bullet, but stop after we've started collecting.
                    continue
                m = _PARTICIPANT_ITEM_RE.match(line)
                if not m:
                    break
                participants.append(_strip_role(m.group(1)))

    return Header(date=date, participants=participants)


# ---------------------------------------------------------------------------
# Parsers per format
# ---------------------------------------------------------------------------


_LINE_BRACKETED_RE = re.compile(
    r"^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s+([^:]+?):\s*(.*)$"
)
_LINE_PAREN_RE = re.compile(r"^\((\d{1,2}:\d{2})\)\s+([^:]+?):\s*(.*)$")
_LINE_LABELED_RE = re.compile(r"^([A-Z][A-Za-z .'-]*):\s*(.+)$")


def _to_mm_ss(ts: str) -> str:
    """Normalize "H:MM:SS" or "HH:MM:SS" timestamps to "MM:SS" (mod 60 minutes).

    Single-bracket forms like "[02:21]" pass through unchanged. Hour-form
    timestamps collapse to total minutes ":SS" so MM may exceed 59 — that
    is intentional and matches how meeting transcripts are typically read
    in chunk references (e.g. "minute 73").
    """
    parts = ts.split(":")
    if len(parts) == 2:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    if len(parts) == 3:
        minutes = int(parts[0]) * 60 + int(parts[1])
        seconds = int(parts[2])
        return f"{minutes:02d}:{seconds:02d}"
    return ts


def parse_bracketed_ts(text: str) -> list[Utterance]:
    """`[MM:SS] Speaker: text` or `[HH:MM:SS] Speaker: text` per line.

    Skips bracketed markers like `[End of recording]` that match the regex
    structurally but are clearly not real utterances (empty body + bracketed
    pseudo-speaker)."""
    out: list[Utterance] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = _LINE_BRACKETED_RE.match(line) or _LINE_PAREN_RE.match(line)
        if not m:
            continue
        ts, speaker, body = m.group(1), m.group(2).strip(), m.group(3).strip()
        # Drop transcript markers like `[End of recording]: ` (empty body,
        # bracketed pseudo-speaker).
        if speaker.startswith("[") and speaker.endswith("]") and not body:
            continue
        if speaker.lower() in {"end of recording"}:
            continue
        out.append(Utterance(timestamp=_to_mm_ss(ts), speaker=speaker, text=body))
    return out


def parse_labeled(text: str) -> list[Utterance]:
    """`Speaker: text` per line, no timestamps. Multi-line utterances are
    glued onto the most recent speaker. Header keys (`Date:`, `Participants:`,
    etc.) are skipped — they are not utterances."""
    out: list[Utterance] = []
    current: tuple[str, list[str]] | None = None  # (speaker, lines)
    in_body = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not in_body:
            m = _LINE_LABELED_RE.match(line.lstrip())
            if m and not _is_header_key(m.group(1)):
                in_body = True
            else:
                continue
        m = _LINE_LABELED_RE.match(line.lstrip())
        if m and not _is_header_key(m.group(1)):
            if current is not None:
                speaker, lines = current
                out.append(Utterance(None, speaker, " ".join(lines).strip()))
            current = (m.group(1).strip(), [m.group(2).strip()])
        elif current is not None and line.strip():
            current[1].append(line.strip())
    if current is not None:
        speaker, lines = current
        out.append(Utterance(None, speaker, " ".join(lines).strip()))
    return out


_VTT_CUE_HEAD_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}"
)


def _split_multi_speaker_body(body_lines: list[str]) -> list[tuple[str, str]]:
    """Walk body lines and return [(speaker, text), ...]. Multiple Speaker:
    lines inside a single cue become multiple utterances. Continuation lines
    are glued to the most recent speaker."""
    out: list[tuple[str, str]] = []
    current: tuple[str, list[str]] | None = None
    for line in body_lines:
        m = _LINE_LABELED_RE.match(line)
        if m and not _is_header_key(m.group(1)):
            if current is not None:
                spk, lines = current
                out.append((spk, " ".join(lines).strip()))
            current = (m.group(1).strip(), [m.group(2).strip()])
        elif current is not None:
            current[1].append(line.strip())
    if current is not None:
        spk, lines = current
        out.append((spk, " ".join(lines).strip()))
    if not out:
        # No speaker labels at all → one Unknown utterance with the joined body.
        return [("Unknown", " ".join(body_lines).strip())]
    return out


def parse_vtt(text: str) -> list[Utterance]:
    """WebVTT cues. Each cue may carry one or more `Speaker:` lines in its
    body; we emit one utterance per speaker, all sharing the cue's start
    timestamp. Cues with no speaker label fall back to `Unknown`."""
    out: list[Utterance] = []
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        head_match = _VTT_CUE_HEAD_RE.search(block)
        if not head_match:
            continue
        start_ts = head_match.group(1)
        lines_after = block[head_match.end() :].splitlines()
        body_lines = [ln.strip() for ln in lines_after if ln.strip()]
        if not body_lines:
            continue
        hh, mm, ss_ms = start_ts.split(":")
        minutes = int(hh) * 60 + int(mm)
        seconds = int(ss_ms.split(".")[0])
        ts_str = f"{minutes:02d}:{seconds:02d}"
        for speaker, text_body in _split_multi_speaker_body(body_lines):
            out.append(Utterance(timestamp=ts_str, speaker=speaker, text=text_body))
    return out


_SRT_BLOCK_RE = re.compile(
    r"(\d+)\s*\n(\d{2}:\d{2}:\d{2}),\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}\s*\n(.+?)(?=\n\s*\n|\Z)",
    re.DOTALL,
)


def parse_srt(text: str) -> list[Utterance]:
    """SubRip subtitle file. Same speaker-handling as VTT."""
    out: list[Utterance] = []
    for m in _SRT_BLOCK_RE.finditer(text):
        start_ts = m.group(2)
        body_lines = [ln.strip() for ln in m.group(3).splitlines() if ln.strip()]
        if not body_lines:
            continue
        body = " ".join(body_lines)
        speaker_match = _LINE_LABELED_RE.match(body)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            text_body = speaker_match.group(2).strip()
        else:
            speaker = "Unknown"
            text_body = body.strip()
        hh, mm, ss = start_ts.split(":")
        minutes = int(hh) * 60 + int(mm)
        seconds = int(ss)
        out.append(
            Utterance(
                timestamp=f"{minutes:02d}:{seconds:02d}",
                speaker=speaker,
                text=text_body,
            )
        )
    return out


def parse_unknown(text: str) -> list[Utterance]:
    """No recognizable structure — dump the whole non-header body under a
    single `Unknown:` speaker. Sets `format_warning: unknown_format`."""
    # Strip a leading header block (anything up to the first blank line if it
    # contains "Date:" or "Participants:") so we don't double-include it in
    # the body.
    body = text
    blank_idx = text.find("\n\n")
    if blank_idx != -1:
        head = text[:blank_idx]
        if "Date:" in head or "Participants:" in head:
            body = text[blank_idx + 2 :]
    body = body.strip()
    if not body:
        return []
    return [Utterance(timestamp=None, speaker="Unknown", text=body)]


# ---------------------------------------------------------------------------
# Filler collapse + speaker canonicalization
# ---------------------------------------------------------------------------


_FILLER_RE = re.compile(
    r"^(?:" + "|".join(re.escape(f) for f in LEADING_FILLERS) + r")(?:[,.]|\s+)",
    re.IGNORECASE,
)


def _collapse_leading_filler(text: str) -> str:
    """Remove `um`, `uh`, `you know`, `like` only when they begin the
    utterance. Mid-utterance fillers are preserved."""
    return _FILLER_RE.sub("", text, count=1).lstrip()


def canonicalize_utterances(utts: list[Utterance]) -> list[Utterance]:
    """Apply leading-filler collapse and trim whitespace. Speakers are kept
    verbatim — speaker-name normalization is a separate, content-aware
    concern outside intake's scope."""
    out: list[Utterance] = []
    for u in utts:
        text = _collapse_leading_filler(u.text).strip()
        out.append(Utterance(timestamp=u.timestamp, speaker=u.speaker.strip(), text=text))
    return out


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _utterance_size(u: Utterance) -> int:
    """Rough character cost of an utterance once rendered with HTML comment
    + speaker line + newline."""
    base = len(u.text) + len(u.speaker) + 4  # ": " + "\n"
    if u.timestamp is not None:
        base += len("<!-- t=") + len(u.timestamp) + len(" -->\n")
    return base


def chunk_utterances(
    utts: list[Utterance],
    budget_chars: int = DEFAULT_CHUNK_CHAR_BUDGET,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[list[Utterance]]:
    """Split utterances into chunks at utterance boundaries, with the
    requested overlap. Chunks may go slightly over budget when a single
    utterance is large — we never split mid-utterance."""
    if not utts:
        return [[]]
    chunks: list[list[Utterance]] = []
    cur: list[Utterance] = []
    cur_size = 0
    for u in utts:
        size = _utterance_size(u)
        if cur and cur_size + size > budget_chars:
            chunks.append(cur)
            # Seed next chunk with the trailing `overlap` utterances of this one
            seed = cur[-overlap:] if overlap > 0 else []
            cur = list(seed) + [u]
            cur_size = sum(_utterance_size(x) for x in cur)
        else:
            cur.append(u)
            cur_size += size
    if cur:
        chunks.append(cur)
    return chunks


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def render_normalized(
    meeting_slug: str,
    header: Header,
    chunks: list[list[Utterance]],
    format_warning: str | None,
    inferred_participants: list[str],
) -> str:
    """Emit the canonical `normalized.md` text."""
    # Participants: prefer explicit header list; otherwise inferred from
    # speaker labels in order of first appearance.
    participants = header.participants or inferred_participants

    fm_lines: list[str] = ["---", f"meeting_slug: {meeting_slug}"]
    if header.date:
        fm_lines.append(f"date: {header.date}")
    fm_lines.append(f"participants: {_yaml_list(participants)}")
    fm_lines.append(f"chunks: {len(chunks)}")
    fm_lines.append(f"format_warning: {format_warning if format_warning else 'null'}")
    fm_lines.append("---")

    body_lines: list[str] = [""]
    n = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        body_lines.append(f"<!-- chunk {i}/{n} -->")
        for u in chunk:
            if u.timestamp is not None:
                body_lines.append(f"<!-- t={u.timestamp} -->")
            body_lines.append(f"{u.speaker}: {u.text}")
        if i < n:
            body_lines.append("")

    return "\n".join(fm_lines + body_lines) + "\n"


# ---------------------------------------------------------------------------
# Inferred participants from speaker labels
# ---------------------------------------------------------------------------


def infer_participants(utts: Iterable[Utterance]) -> list[str]:
    seen: list[str] = []
    for u in utts:
        if u.speaker not in seen and u.speaker.lower() != "unknown":
            seen.append(u.speaker)
    if not seen:
        return ["Unknown"]
    return seen


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


_PARSERS = {
    "vtt": parse_vtt,
    "srt": parse_srt,
    "bracketed-ts": parse_bracketed_ts,
    "labeled": parse_labeled,
    "unknown": parse_unknown,
}


def normalize_text(
    meeting_slug: str,
    text: str,
    budget_chars: int = DEFAULT_CHUNK_CHAR_BUDGET,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> str:
    """Pure transformation: source text → normalized.md content. Useful for
    tests and for the backend wrapper."""
    fmt = detect_format(text)
    header = parse_header(text)
    utts = canonicalize_utterances(_PARSERS[fmt](text))

    format_warning: str | None = None
    if utts and all(u.speaker == "Unknown" for u in utts):
        # No speaker labels at all — common for header+prose source files.
        # Prefer the more specific warning over "unknown_format".
        format_warning = "no_speaker_labels"
    elif fmt == "unknown":
        format_warning = "unknown_format"

    chunks = chunk_utterances(utts, budget_chars=budget_chars, overlap=overlap)
    inferred = infer_participants(utts)
    return render_normalized(
        meeting_slug=meeting_slug,
        header=header,
        chunks=chunks,
        format_warning=format_warning,
        inferred_participants=inferred,
    )


def normalize_folder(folder: pathlib.Path, **kwargs) -> pathlib.Path:
    """Read `meetings/<slug>/source.*`, write `normalized.md`. Returns the
    destination path."""
    sources = sorted(p for p in folder.glob("source.*") if p.is_file())
    if not sources:
        raise FileNotFoundError(f"no source.* file in {folder}")
    if len(sources) > 1:
        raise RuntimeError(
            f"multiple source files in {folder}: {[s.name for s in sources]}"
        )
    source = sources[0]
    text = source.read_text()
    slug = folder.name
    rendered = normalize_text(slug, text, **kwargs)
    dest = folder / "normalized.md"
    dest.write_text(rendered)
    return dest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("meeting_folder", help="path to meetings/<slug>/")
    parser.add_argument(
        "--budget-chars",
        type=int,
        default=DEFAULT_CHUNK_CHAR_BUDGET,
        help="soft per-chunk character budget (default: %(default)s)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="utterance overlap between chunks (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    folder = pathlib.Path(args.meeting_folder)
    dest = normalize_folder(folder, budget_chars=args.budget_chars, overlap=args.overlap)
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
