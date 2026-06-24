---
name: fast-evidence
description: Single-pass replacement for the outline → moms-test-extraction → qa-reconciler chain, valid only when normalized.md has chunks: 1. Produces outline.md, qa.md, and qa-chunks/qa-1.md in one LLM call instead of three sequential ones. Used automatically by the meeting-to-tickets orchestrator for single-chunk transcripts. Do not invoke directly for multi-chunk transcripts — use the full pipeline instead.
---

# fast-evidence

You are collapsing three pipeline stages — outline, extraction, and reconciliation — into one pass over a single-chunk transcript.

This skill is only valid when `normalized.md` has `chunks: 1` in its frontmatter. For multi-chunk transcripts, each of those three stages exists separately because cross-chunk references, walk-back detection, and deduplication require seeing multiple chunks in sequence. None of that complexity applies when there is only one chunk — so there is no reason to pay for three LLM calls.

Your output files must be format-identical to what the three separate skills produce. Downstream stages (theme-clustering, requirements-drafting) and the invariant checker read these files and cannot tell the difference between a fast-evidence run and a full pipeline run.

## Inputs

A path to a meeting folder. Must contain `normalized.md` with `chunks: 1` in frontmatter.

**If `chunks` is anything other than `1`, stop immediately and tell the caller to use the full pipeline.**

## What to do in one pass

Read `normalized.md` in full. Then do all of this together:

### 1. Build the outline

Same rules as the `meeting-outline` skill:
- **Themes** — recurring topics, with chunk reference `[1]` for all (only one chunk).
- **Named entities** — people, systems, vendors, products, prior incidents referenced more than once or with notable context.
- **Named costs** — specific quantities: money, time, headcount, percentages.
- **Commitments** — decisions made or actions agreed during the call.
- **Walk-backs** — where the client stated an ask and then retracted or rescoped it. Only include when you can cite both the original ask AND the retraction verbatim. Walk-backs here are a contract: `qa.md` must cover each one as a single Q&A with both quotes.

### 2. Extract Q&As with Mom's Test discipline

Same rules as the `moms-test-extraction` skill, applied to the full transcript:
- Seven lenses: problem in life, what they've tried, cost of doing nothing, stated ask vs. underlying need, compliment vs. evidence, frequency and scope, commitment vs. hedge.
- Every Q&A needs at least one verbatim quote with speaker attribution.
- Confidence: `grounded` (quote directly answers the lens) or `inferred` (synthesized from context).
- Compliments without concrete past behavior go to `## Dropped`, not into a Q&A.
- Walk-backs from the outline each get exactly one Q&A under the "stated ask vs. underlying need" lens, with both the ask quote and the retraction quote in `**Quotes:**`.

**Single-mention grounded asks (discipline rule).** The seven lenses naturally catch recurring themes. They under-catch single-mention asks where a client speaker takes explicit ownership of a specific concern or follow-up. A single client utterance IS a grounded Q&A — not a dropped compliment — when ALL three hold:

1. **The CLIENT said it** (not the vendor/solution-provider). The vendor frames themselves as "we will build", "our methodology", "our approach". The client is the participant whose problems are being solved.
2. **It carries one of these linguistic patterns** (pattern matters, not exact vocabulary): **inclusion ask** ("include X in the proposal", "add X to the SOW", "cover X"); **importance flag** ("this is important", "we want to track X", "X matters", "make a note of X"); **stakeholder ownership** ("our compliance team will need X", "our legal team flagged X", "I'll need to check with [team]"); **concern surfacing** ("what about X?", "I'm worried about X", "how do you handle X?").
3. **The substance is concrete enough to act on** — names a topic, capability, constraint, or stakeholder with enough specificity to become an AC or open question. Pure emotional reassurance ("we want this to work", "we're excited") still goes to `## Dropped`.

When all three hold, extract as a Q&A under the most appropriate lens (usually 4, 6, or 7). Anchor on the single client quote. Discovery calls routinely surface compliance / ethics / training / mobile / stakeholder-specific concerns once with explicit ownership — these are grounded signals, not noise.

### 3. Write outputs

Write three files. Formats below are the exact schemas downstream tools expect — do not deviate.

---

## Output 1: `outline.md`

```markdown
---
source: normalized.md
chunks_covered: 1
themes: <int>
entities: <int>
costs: <int>
commitments: <int>
walk_backs: <int>
---

## Themes
- T1: <Theme name> — chunks [1]
- T2: ...

## Named entities
- <Name> — <role/context>; intro chunk 1 (t=MM:SS)

## Named costs
- <amount/unit> <what this measures> (<speaker>, t=MM:SS)

## Commitments
- <decision or agreed action> (t=MM:SS)

## Walk-backs
- <Name> — asked at chunk 1 (t=MM:SS) — walked back to "<short quote>" at chunk 1 (t=MM:SS)
```

Omit any section that has no material. Frontmatter counts must match the bullet counts in each section.

---

## Output 2: `qa-chunks/qa-1.md`

Write this **before** `qa.md`. It is a pass-through that keeps the invariant checker satisfied — the checker expects one `qa-chunks/qa-<N>.md` per chunk in `normalized.md`.

```markdown
---
source: normalized.md
chunk_index: 1
total_qa: <int>
dropped: <int>
---

### Q1 — <title> (lens: <lens name>)
**Answer:** <synthesized answer>
**Confidence:** grounded | inferred
**Chunk:** 1
**Quotes:**
- Speaker: "verbatim quote"

...

## Dropped
- Q (proposed): "<label>" — <reason>
```

`total_qa` is the count of Q&A items in this file. `dropped` is the count of entries in `## Dropped`.

---

## Output 3: `qa.md`

Since there is only one chunk, there is nothing to merge or dedup — `qa_before_dedup` equals `qa_after_dedup`. **Do not regenerate the Q&A content.** The body of `qa.md` is identical to `qa-chunks/qa-1.md` with two mechanical changes: replace `**Chunk:** 1` with `**Chunks:** 1` on every Q&A block, and remap the frontmatter (`chunk_index` → `chunks_merged`, add `qa_before_dedup`/`qa_after_dedup`/`walk_backs_resolved`). Consolidate the Dropped section verbatim.

```markdown
---
source: qa-chunks/
chunks_merged: 1
qa_before_dedup: <int>
qa_after_dedup: <int>
dropped: <int>
walk_backs_resolved: <int>
---

### Q1 — <title> (lens: <lens name>)
**Answer:** <synthesized answer>
**Confidence:** grounded | inferred
**Chunks:** 1
**Quotes:**
- Speaker: "verbatim quote"

...

## Dropped
- <consolidated entries from qa-chunks/qa-1.md>
```

`walk_backs_resolved` must equal `walk_backs` in `outline.md`. If any walk-back from the outline is missing from `qa.md`, append a `## Walk-back coverage gaps` section naming the missing one — same contract as the `qa-reconciler` skill.

---

## Rules

- **Do not invent quotes.** Every quote in every output must come verbatim from `normalized.md`.
- **Timestamps in outline must trace to `<!-- t=MM:SS -->` markers in `normalized.md`.** Do not invent timestamps.
- **PARALLEL WRITES — STRICT.** Emit all three `Write` calls as separate tool_use blocks inside ONE assistant response. They MUST appear in the SAME response, not split across three response turns. Splitting them is wrong: it costs 3× the round-trips, triggers 3 separate permission prompts, and defeats the purpose of collapsing this stage. The invariant checker reads files in dependency order but does not require them written in that order — all content is resolved in one LLM pass before any Write fires, so there is no ordering dependency at write time. If you find yourself writing a brief acknowledgement between files, you are doing it wrong; revert and batch.
- **Stop and fail if `chunks` ≠ 1.** Do not attempt a fast-evidence run on a multi-chunk transcript.

## Constraints
- Do not modify `normalized.md`.
- Do not write any file other than `outline.md`, `qa-chunks/qa-1.md`, and `qa.md`.

## Acceptance test
After running on any single-chunk meeting folder:
- `outline.md` frontmatter counts match section bullet counts.
- `qa-chunks/qa-1.md` exists with `chunk_index: 1`.
- `qa.md` has `chunks_merged: 1` and `walk_backs_resolved` equal to `outline.md`'s `walk_backs`.
- Every quote in `qa.md` appears verbatim in `normalized.md`.
- `theme-clustering` and `requirements-drafting` run successfully on the output with no errors — they cannot tell this was a fast-evidence run vs. a full pipeline run.
