---
name: qa-reconciler
description: Merge per-chunk Q&A files in meetings/<slug>/qa-chunks/*.md into a single consolidated meetings/<slug>/qa.md. Dedupes semantically-equivalent Q&As across chunks, merges cross-chunk walk-backs declared in outline.md, accumulates evidence quotes, consolidates Dropped sections, and renumbers Q-ids globally.
---

# qa-reconciler

You are merging multiple per-chunk Q&A files into a single consolidated `qa.md`. The per-chunk extractor produced one file per chunk; your job is to:

1. Dedupe — when chunk A's Q3 and chunk B's Q7 are about the same thing, merge them into one Q&A with both evidence quote sets.
2. Resolve walk-backs — when the per-chunk extractor flagged `**Walk-back:** pending merge with chunk <N>`, find the matching Q&A in chunk N and merge into one walk-back Q&A.
3. Accumulate evidence — a single theme that drew multiple quoted moments across chunks should consolidate them under one Q&A with all quotes preserved.
4. Renumber Q1, Q2, … globally after merging.
5. Consolidate `## Dropped` sections from all chunks into one.

## Inputs
A path to a meeting folder. The folder must contain:
- `outline.md` (produced by `meeting-outline`)
- `qa-chunks/qa-1.md`, `qa-chunks/qa-2.md`, … (produced by `moms-test-extraction`, one per chunk)

## Output
Write `<meeting_folder>/qa.md`. Do not write anything else. Do not modify the per-chunk files.

## Dedup rules

Two Q&As from different chunks should be merged when EITHER:
- They share the same primary lens AND describe substantially the same theme (entity or topic from the outline), OR
- They're both about the same named entity from the outline (Mrs. Banerjee, DentalDesk, etc.), OR
- They're parts of the same walk-back declared in `outline.md`.

When merging:
- Concatenate the evidence quotes. Preserve all verbatim quotes from both source Q&As, in chunk order. Each quote retains its speaker attribution.
- Synthesize a single `**Answer:**` that fairly reflects the combined evidence — don't drop signal from either source.
- Set `**Chunks:**` (plural) to list all source chunks: `**Chunks:** 1, 2`.
- Set `**Confidence:**` to `grounded` if any source Q&A was `grounded`.
- The merged Q&A's lens is the primary lens; secondary lenses can be listed in parentheses: `(lens: cost of doing nothing; also: frequency and scope)`.

When NOT to merge:
- Two Q&As about distinct aspects of the same theme (e.g., "phone gap" and "WhatsApp decay" — both about inbound channels but distinct mechanisms). Keep separate.
- Two Q&As that share a speaker or a single quote in common but address different lenses. Keep separate.
- When in doubt, keep separate. Over-merging loses signal; under-merging is fixed at clustering.

## Walk-back resolution

For each walk-back declared in `outline.md`:
1. Find the per-chunk Q&A(s) that carry the ask or retraction. They'll be flagged with `**Walk-back:** pending merge with chunk <N>` OR (if both quotes are in the same chunk) already merged into a single Q&A by the extractor.
2. If you find two pending entries (ask in one chunk, retraction in another), merge them into a single Q&A under the "Stated ask vs underlying need" lens with both quotes in `**Quotes:**` in chunk order.
3. Verify: the merged walk-back Q&A's quotes include BOTH (a) the original ask verbatim and (b) the retraction verbatim. If either is missing, flag in the output (see "Walk-back coverage flag" below).

## Output shape

```markdown
---
source: qa-chunks/
chunks_merged: <int>
qa_before_dedup: <int>          # sum across input chunk files
qa_after_dedup: <int>           # count in this output
dropped: <int>                  # total drops carried over from all chunks
walk_backs_resolved: <int>      # how many outline-declared walk-backs are covered by a single Q&A here
---

### Q1 — <title> (lens: <primary>[; also: <secondary>])
**Answer:** <synthesized>
**Confidence:** grounded | inferred
**Chunks:** <int>[, <int>...]
**Quotes:**
- Speaker: "verbatim from source chunk"
- Speaker: "verbatim from same or different chunk"

### Q2 — ...

## Dropped
- (consolidated from all chunks; entries carry their original chunk source if useful)
```

## Constraints
- Do not invent new quotes. Every quote in the output must come verbatim from a per-chunk file (which means it traces to `normalized.md`).
- Do not modify `outline.md` or any `qa-chunks/*.md` file.
- Do not skip dropped entries — consolidate them all.
- Per-chunk Q-ids (Q1 of chunk 1, Q1 of chunk 2) are local to each chunk; your output renumbers globally starting at Q1.

## Walk-back coverage flag

After producing the merged `qa.md`, scan it: for every walk-back declared in `outline.md`, there should be at least one Q&A whose quote set includes both the ask and the retraction (as identified by the timestamps in the outline). If any walk-back is uncovered, append to the end of the file:

```markdown
## Walk-back coverage gaps
- <walk-back name> — ask at <chunk/timestamp> found, retraction at <chunk/timestamp> not found in any output Q&A
```

The invariant checker reads this section and flags any gap as a violation.

## Acceptance test
Against `meetings/mehta-dental-discovery/` with chunks 1 and 2 already extracted:
- `chunks_merged: 2`, `qa_before_dedup: ≈32` (18 from chunk 1 + 14 from chunk 2), `qa_after_dedup: ≈22-26` (after merging burnout, festival/holiday, and any other cross-chunk themes)
- `walk_backs_resolved: 3` (Marathi, Insurance Q&A, Payments — all three were resolved intra-chunk by the extractor)
- No `## Walk-back coverage gaps` section
- The merged Q&A for staff burnout contains quotes from both chunk 1 (the two-people-quit and lunch-break lines) and chunk 2 (Priya-is-third-in-three-years and offload-half-the-work lines)
- The merged Q&A for festival/holiday-closure contains quotes from chunk 1 (120 WhatsApp + 60 missed calls) and chunk 2 (holiday handling commitment)
