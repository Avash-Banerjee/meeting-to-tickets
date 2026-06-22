---
name: transcript-intake
description: Normalize a meeting transcript file at meetings/<slug>/source.* into meetings/<slug>/normalized.md by invoking scripts/intake.py — deterministic Python intake, no LLM in the loop.
---

# transcript-intake

This skill no longer asks the LLM to do the normalization. The mechanical rules now live in `scripts/intake.py` — that's the Phase-2 backend boundary realized in code.

## Inputs
A path to a meeting folder, e.g. `meetings/2026-06-19-acme-discovery/`. The folder must contain exactly one `source.*` file (`.txt`, `.vtt`, `.srt`, `.md`).

## Output
The script writes `<meeting_folder>/normalized.md`. No other files.

## How to invoke

```bash
cd meeting-to-tickets
./.venv/bin/python scripts/intake.py <meeting_folder>
```

Optional flags:
- `--budget-chars N` — soft chunk budget in characters. Default `32000` (≈8000 tokens). Lower for tighter chunking; higher to keep the whole transcript in one chunk.
- `--overlap N` — utterances of overlap between consecutive chunks. Default `1`.

## What the script does (single source of truth)

- **Format detection** — `vtt` (WEBVTT header), `srt` (cue index + comma-millisecond timestamps), `bracketed-ts` (`[MM:SS]` or `[HH:MM:SS]` line prefix), `labeled` (`Speaker:` line prefix with no timestamps), or `unknown` (fallback).
- **Header parsing** — pulls `date:` and `participants:` from a `Date: YYYY-MM-DD` line and an inline-or-bulleted `Participants:` block. Roles in parens (`Priya (Office Manager)`) are stripped. Header keys (`Date`, `Duration`, `Meeting`, etc.) are never treated as speakers.
- **Per-utterance emission** — `<!-- t=MM:SS -->` HTML comment on its own line, then `Speaker: text`. Hour-form timestamps (`01:05:00`) collapse to total minutes (`65:00`).
- **Multi-speaker cue handling (VTT/SRT)** — a single cue containing `Alice: ...\nPriya: ...` produces two utterances sharing the cue's start timestamp.
- **Leading filler collapse** — `um`, `uh`, `you know`, `like` only at the start of an utterance. Mid-utterance fillers preserved.
- **Chunking** — utterance boundaries only; soft budget; 1-utterance overlap between consecutive chunks; never splits inside an utterance even when it exceeds budget.
- **Frontmatter** — `meeting_slug`, `date` (only if found in source), `participants` (header > inferred order of first appearance > `[Unknown]`), `chunks`, `format_warning`.
- **format_warning** — `no_speaker_labels` when all utterances ended up under `Unknown:`; `unknown_format` only when the source is empty or truly unrecognizable; otherwise `null`.

## Why this is now Python, not a prompt

The intake stage has always been mechanical — regex, parsing, chunking. The original LLM-driven version paid LLM cost per call for deterministic work and risked silent content loss the rigor check couldn't catch. Moving it to `scripts/intake.py`:
- **Deterministic** — same input always produces the same output.
- **Free** — no LLM tokens.
- **Fast** — sub-second on 36-minute transcripts.
- **Testable** — 35 pytest tests cover the per-format parsers, header parse, chunking, and end-to-end shape.
- **Backend-portable** — this *is* the Phase-2 backend service. Wrap it in an HTTP endpoint and the rest of the pipeline keeps working unchanged.

## The deterministic gate that catches intake errors

`scripts/check_invariants.py` runs a word-count round-trip on every invocation: the body of `normalized.md` must contain ≥95% of the meaningful words from `source.*` (after stripping headers, decorative separators, and HTML comments). Silent content loss during intake is what this catches. The deterministic check is free and runs every time, so the LLM-reviewer-on-every-run question is moot.

## Acceptance test
After running on `fixtures/clean-short.txt` placed at `meetings/clean-short/source.txt`, the produced `meetings/clean-short/normalized.md` matches `fixtures/expected/clean-short/normalized.md` byte-for-byte. Same for `compliments-only` and `no-speaker-labels`. `long-noisy` is also byte-for-byte after the snapshot was regenerated to match the canonical no-blank-line style.
