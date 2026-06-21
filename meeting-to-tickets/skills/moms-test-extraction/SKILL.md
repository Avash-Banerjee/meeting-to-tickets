---
name: moms-test-extraction
description: Read meetings/<slug>/normalized.md and write meetings/<slug>/qa.md as Mom's-Test-shaped Q&A pairs grounded in verbatim transcript quotes. Drop anything not supported by behavioral evidence.
---

# moms-test-extraction

You are extracting Q&A pairs from a normalized transcript using Rob Fitzpatrick's *Mom's Test* discipline retrospectively. Your bias is toward dropping rather than inventing — missed signal is recoverable on rerun; fabricated signal corrupts the backlog.

## Inputs
A path to a meeting folder, e.g. `meetings/2026-06-19-acme-discovery/`. The folder must already contain `normalized.md` (produced by `transcript-intake`).

## Output
Write `<meeting_folder>/qa.md`. Do not write anything else.

## The seven lenses
For each chunk in `normalized.md`, scan for evidence that answers one or more of:

1. **Problem in life.** What problem are they actually trying to solve in their life? (Pain, not feature wish.)
2. **What they've already tried.** Workarounds, hacks, manual processes, tools tried. This is gold; past behavior beats future intent.
3. **Cost of doing nothing.** Time, money, frustration, missed opportunity. Quantify when the transcript does.
4. **Stated ask vs. underlying need.** What did they ask for vs. what do they actually need?
5. **Compliment vs. evidence.** Unsupported praise is dropped; specific past actions and concrete costs are kept.
6. **Frequency and scope.** Who else has this problem, how often, how badly?
7. **Commitment vs. hedge.** Concrete next steps vs. "we'll think about it."

A Q&A may use one or more lenses; annotate the primary lens in the heading.

## Rigor rules
- Every Q&A includes at least one **verbatim quote** with the speaker's name. Copy the quote exactly — no paraphrase, no ellipsis-rewrite, no merging.
- Confidence tag per Q&A:
  - `grounded` — at least one quote directly answers the lens question.
  - `inferred` — synthesized from surrounding context. Must be flagged so reviewers know to challenge.
- Compliments without concrete past behavior (e.g. "that sounds great", "I'd love that", "we should totally do that") are dropped and logged in `## Dropped` with the reason.
- A proposed Q&A that has no transcript evidence at all is dropped — never invent.

## Output shape

```markdown
---
source: normalized.md
chunks_processed: <int>
total_qa: <int>
dropped: <int>
---

### Q1 — Short title (lens: <lens name>)
**Answer:** One- to two-sentence synthesized answer.
**Confidence:** grounded | inferred
**Chunk:** <int>
**Quotes:**
- Speaker: "verbatim quote here"
- Speaker: "another verbatim quote here"

### Q2 — ...

## Dropped
- Q (proposed): "<short label>" — <reason for dropping>.
```

## Constraints
- Do not modify `normalized.md`.
- Do not write any file other than `qa.md`.
- If `normalized.md` has `format_warning: no_speaker_labels`, attribute quotes to `Unknown` and proceed; do not refuse.

## Acceptance test
After running on `meetings/clean-short/normalized.md`, the produced `meetings/clean-short/qa.md` should match `fixtures/expected/clean-short/qa.md` in structure and content. Exact text in the synthesized answers may vary slightly across runs; verbatim quotes and the set of grounded Q&As must match.
