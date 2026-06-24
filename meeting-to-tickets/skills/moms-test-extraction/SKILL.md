---
name: moms-test-extraction
description: For a single chunk of meetings/<slug>/normalized.md, extract Mom's-Test Q&A pairs grounded in verbatim transcript quotes and write meetings/<slug>/qa-chunks/qa-<chunk_index>.md. Reads meetings/<slug>/outline.md as cross-chunk context so references the chunk doesn't introduce are still resolvable.
---

# moms-test-extraction

You are extracting Q&A pairs from one chunk of a normalized transcript using Rob Fitzpatrick's *Mom's Test* discipline retrospectively. Your bias is toward dropping rather than inventing — missed signal is recoverable on rerun; fabricated signal corrupts the backlog.

## Inputs
A path to a meeting folder AND a chunk index. The folder must contain:
- `normalized.md` (produced by `transcript-intake`)
- `outline.md` (produced by `meeting-outline`)

You process ONE chunk per invocation. The orchestrator invokes you N times for an N-chunk meeting.

## Output
Write `<meeting_folder>/qa-chunks/qa-<chunk_index>.md`. Create the `qa-chunks/` subdirectory if it doesn't exist. Do not write anything else.

## Use the outline as context
Before extracting, read `outline.md`. It tells you:
- **Named entities** introduced in other chunks. When this chunk uses vague references like "that situation", "the case we discussed", or "that company they mentioned", the outline tells you who/what is being referenced — DO NOT drop the Q&A for lack of context.
- **Walk-backs** declared. Apply these rules per walk-back, based on which chunk the ask and retraction live in:
  - **Both quotes in THIS chunk** → extract a single Q&A under the "Stated ask vs underlying need" lens, with BOTH the ask quote and the retraction quote in the same `**Quotes:**` block. Do not drop it.
  - **Ask is in THIS chunk, retraction in another** → extract a Q&A under the "Stated ask vs underlying need" lens with just the ask quote. Add `**Walk-back:** pending merge with chunk <N>` after the `**Confidence:**` line. The reconciler will merge it with the retraction Q&A from the other chunk.
  - **Retraction is in THIS chunk, ask in another** → same shape as above, but quote the retraction. Add `**Walk-back:** pending merge with chunk <N>`. Reconciler merges.
- **Themes** that recur across chunks. When this chunk continues a theme introduced elsewhere, extract the Q&A as usual; the reconciler will merge it with related Q&As from other chunks.

You are still only extracting from THIS chunk. Don't quote from outline.md or from other chunks — every quote must come from the chunk currently being processed.

## The seven lenses
For the chunk you're processing, scan for evidence that answers one or more of:

1. **Problem in life.** What problem are they actually trying to solve in their life? (Pain, not feature wish.)
2. **What they've already tried.** Workarounds, hacks, manual processes, tools tried. This is gold; past behavior beats future intent.
3. **Cost of doing nothing.** Time, money, frustration, missed opportunity. Quantify when the transcript does.
4. **Stated ask vs. underlying need.** What did they ask for vs. what do they actually need?
5. **Compliment vs. evidence.** Unsupported praise is dropped; specific past actions and concrete costs are kept.
6. **Frequency and scope.** Who else has this problem, how often, how badly?
7. **Commitment vs. hedge.** Concrete next steps vs. "we'll think about it."

A Q&A may use one or more lenses; annotate the primary lens in the heading.

## Single-mention grounded asks (discipline rule)

The seven lenses naturally catch recurring themes. They under-catch single-mention asks where a client speaker explicitly takes ownership of a specific concern or follow-up commitment. These get dropped as "compliments" because they were only said once. That's wrong.

A single-mention utterance IS a grounded Q&A when ALL three hold:

1. **The CLIENT said it** — not the vendor / solution-provider. The vendor is the participant who frames themselves as "we will build", "our methodology", "our approach", or who describes the solution. The client is the participant whose problems are being solved and who controls the buy/scope decision.

2. **It carries one of these linguistic patterns** (the pattern matters, not the exact vocabulary — any equivalent phrasing in any language counts):
   - **Inclusion ask** — "include X in the proposal", "let's add X to the SOW", "make sure we cover X", "we need X to be part of this", "put X in writing"
   - **Importance flag** — "this is important for us", "we want to track X", "X matters to us", "we need to be careful about X", "make a note of X"
   - **Stakeholder ownership** — "our compliance team will need X", "our legal team flagged X", "our [team] requires X", "I'll have to check with [stakeholder] about X"
   - **Concern surfacing** — "what about X?", "I'm worried about X", "we have concerns about X", "how do you handle X?", "we need to think about X"

3. **The substance is concrete enough to act on** — names a topic, capability, constraint, stakeholder, or commitment with enough specificity that a PM could turn it into an acceptance criterion or open question. Reject generic emotional reassurance ("we want this to work well", "we're excited", "this looks great") because there is nothing to act on.

When all three hold, extract as a Q&A under the most appropriate lens (usually lens 4 "stated ask vs. underlying need", lens 6 "frequency and scope", or lens 7 "commitment vs. hedge"). Anchor it on the single client quote. Do NOT drop it as a compliment.

**Why this rule exists:** the natural-recurrence heuristic ("real signals get mentioned multiple times") is wrong for discovery calls. A client mentioning a specific concern once with explicit ownership IS a real signal — they are flagging it for the proposal, not making conversation. Compliance asks, ethics asks, training asks, mobile/platform asks, and stakeholder-specific concerns routinely fail the "did they mention it twice?" test but pass the "did they take ownership of this as a follow-up?" test. The latter is what makes a Q&A grounded.

This rule does NOT change lens 5 (Compliment vs. evidence). Pure praise without behavioral evidence or commitment substance still goes to `## Dropped`. The rule only catches the narrow case of single-mention asks that the recurrence heuristic would otherwise miss.

## Rigor rules
- Every Q&A includes at least one **verbatim quote** with the speaker's name. Copy the quote exactly — no paraphrase, no ellipsis-rewrite, no merging.
- Confidence tag per Q&A:
  - `grounded` — at least one quote directly answers the lens question.
  - `inferred` — synthesized from surrounding context. Must be flagged so reviewers know to challenge.
- Compliments without concrete past behavior (e.g. "that sounds great", "I'd love that", "we should totally do that") are dropped and logged in `## Dropped` with the reason.
- A proposed Q&A that has no transcript evidence at all is dropped — never invent.
- All quotes must come from THIS chunk (the one named in the chunk_index input). Cross-chunk quote merging is the reconciler's job, not yours.

## Output shape

```markdown
---
source: normalized.md
chunk_index: <int>
total_qa: <int>
dropped: <int>
---

### Q1 — Short title (lens: <lens name>)
**Answer:** One- to two-sentence synthesized answer.
**Confidence:** grounded | inferred
**Chunk:** <int>           # same as chunk_index above
**Quotes:**
- Speaker: "verbatim quote here"
- Speaker: "another verbatim quote here"

### Q2 — ...

## Dropped
- Q (proposed): "<short label>" — <reason for dropping>.
```

Per-chunk Q&A numbering restarts at Q1 for each chunk — the reconciler renumbers globally.

## Constraints
- Do not modify `normalized.md` or `outline.md`.
- Do not write any file other than `qa-chunks/qa-<chunk_index>.md`.
- If `normalized.md` has `format_warning: no_speaker_labels`, attribute quotes to `Unknown` and proceed; do not refuse.
- Do not pull quotes from chunks other than the one you're processing.

## Acceptance test
Against `fixtures/expected/clean-short/normalized.md` (single chunk, well-formed), the produced `qa.md` (or `qa-chunks/qa-1.md` in the per-chunk variant) should match the committed `fixtures/expected/clean-short/qa.md` in structure: every Q&A has at least one verbatim quote with speaker, confidence tags are present, and `## Dropped` records any compliments-without-behavioral-evidence the prompt encountered. Against `fixtures/expected/compliments-only/normalized.md`, the expected outcome is zero grounded Q&As and three-or-more dropped entries — that's the rigor test working as designed.
