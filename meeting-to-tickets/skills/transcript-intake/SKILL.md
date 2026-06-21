---
name: transcript-intake
description: Normalize a meeting transcript file at meetings/<slug>/source.* into meetings/<slug>/normalized.md. Detect format (txt, vtt, srt, md), preserve timestamps as HTML comments, use existing speaker labels or fall back to Unknown:, collapse leading filler words, and chunk if over the token budget.
---

# transcript-intake

You are normalizing a meeting transcript so the rest of the pipeline can operate on a single canonical shape.

## Inputs
A path to a meeting folder, e.g. `meetings/2026-06-19-acme-discovery/`. The folder contains a `source.*` file.

## Output
Write `<meeting_folder>/normalized.md`. Do not write anything else.

## Format detection
Look at the file extension and first few lines.
- `.vtt` / `.srt` → timestamped format. Strip the cue indices and convert timestamps to `<!-- t=MM:SS -->` HTML comments on their own line, immediately before the utterance.
- `.txt` / `.md` → plain text. If `Speaker:` patterns are present at line starts, use them. If lines begin with `[HH:MM:SS]` or `(MM:SS)`, convert to `<!-- t=MM:SS -->` and continue.
- Anything else → set `format_warning: unknown_format` in frontmatter and emit the raw text under a single `Unknown:` speaker block. Do not abort.

## Speaker labels
- Use existing labels at line starts when present (regex match: `^[A-Z][A-Za-z .'-]+:` ).
- Optional header block at the top of the file like `Participants: Alice, Bob` is parsed and copied into frontmatter as `participants: [Alice, Bob]`.
- If no labels can be inferred anywhere, use `Unknown:` for all utterances and set `format_warning: no_speaker_labels`.

## Filler
Collapse a leading filler token only if it appears as the first word of an utterance: `um`, `uh`, `you know`, `like`. Do not touch mid-utterance fillers.

## Chunking
Aim for ~8000 tokens per chunk (≈32000 characters). If the normalized output exceeds the budget, split at utterance boundaries with 1–2 utterances of overlap. Mark each chunk with `<!-- chunk N/M -->` on its own line at the chunk's start.

## Frontmatter
Always include these keys:
- `meeting_slug` — the folder name.
- `date` — parsed from a header line if present (e.g. `Date: 2026-06-19`); otherwise omit (do not invent).
- `participants` — list parsed from header or inferred from speaker labels in order of first appearance.
- `chunks` — integer count.
- `format_warning` — `null` if everything is clean; otherwise a short string identifier.

## Constraints
- Do not invent content. Do not paraphrase. Preserve original wording exactly.
- Write only the normalized markdown file. Do not touch any other files.

## Acceptance test
After running on `fixtures/clean-short.txt` placed at `meetings/clean-short/source.txt`, the produced `meetings/clean-short/normalized.md` must match `fixtures/expected/clean-short/normalized.md` byte-for-byte (except trailing whitespace differences).
