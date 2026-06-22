---
name: meeting-outline
description: Read meetings/<slug>/normalized.md and write meetings/<slug>/outline.md — a cross-chunk reference index of themes, named entities, costs, commitments, and Mom's-Test walk-backs that downstream stages use as context.
---

# meeting-outline

You are producing a cross-chunk reference index for a meeting. Every downstream stage (per-chunk extraction, reconciler) reads this file as context so they can resolve references that span chunks ("that situation we discussed earlier"), detect walk-backs whose ask and retraction sit in different chunks, and avoid duplicate Q&As about the same theme.

This is a single, cheap LLM pass over the whole `normalized.md`. You read everything; you produce one consolidated outline.

## Inputs
A path to a meeting folder. The folder must contain `normalized.md`.

## Output
Write `<meeting_folder>/outline.md`. Do not write anything else.

## What goes in the outline

Five sections. Each one is omitted entirely if the transcript has no material for it.

### Themes
A *theme* is a topic that recurs or spans multiple utterances. Group related discussion under a short theme name. List the chunk indices each theme appears in (cross-reference the `<!-- chunk N/M -->` markers in normalized.md).

```
- T1: <Theme name> — chunks [N, M, ...]
- T2: ...
```

A theme is NOT a Q&A pair. It's a topical grouping that the downstream extractor uses to anticipate cross-chunk references.

### Named entities
People, places, products, prior incidents that are referenced more than once OR introduced with notable context. Each entry: name — one-line role/context — `intro chunk N (t=MM:SS)`.

```
- Mrs. Banerjee — 10-year patient lost to Smile Hub competitor; intro chunk 1 (t=03:11)
- DentalDesk — Pune-vendor clinic calendar software; intro chunk 1 (t=07:40)
```

When the same entity is described differently across chunks ("the Banerjee case" in chunk 1, "that situation" in chunk 3), the entity belongs here so downstream stages can resolve the reference.

### Named costs
Specific quantified costs the client mentioned (₹ amounts, hours, days, percentages). Each entry: cost — context — `(speaker, t=MM:SS)`.

```
- ₹1 lakh/month minimum revenue loss (Priya, t=04:21)
- 1 hour/evening on confirmation calls (Priya, t=06:44)
```

These are evidence the reconciler uses to accumulate cost-of-doing-nothing evidence under a single Q&A even when the cost numbers span chunks.

### Commitments
Decisions explicitly made or actions agreed during the call. Each entry: decision — `(t=MM:SS)`.

```
- Thursday 4 PM follow-up call (t=35:54)
- Narrow v1 in 6 weeks; full system in 3-4 months (t=31:46)
```

### Walk-backs (Mom's-Test pivots — critical)

A *walk-back* is a Mom's-Test pattern where the client states an ask, and either the client themselves or the interviewer's probing leads to retracting or rescoping it. These are easy to miss when the ask and the retraction sit in different chunks.

Each walk-back: short name — original ask (chunk and timestamp) — walked-back scope (chunk and timestamp).

```
- Marathi support — asked at chunk 1 (t=10:04) — walked back to "Hindi covers them" at chunk 1 (t=10:30)
- Insurance Q&A — asked at chunk 1 (t=14:55) — walked back to triage-only at chunk 1 (t=16:24)
- Payments — asked at chunk 1 (t=16:41) — walked back to "the payment part works fine" at chunk 1 (t=17:07)
```

Walk-backs declared here are a contract: the reconciler's `qa.md` must contain a Q&A covering each walk-back as a SINGLE Q&A under the "Stated ask vs. underlying need" lens, with BOTH the original ask quote AND the walked-back quote as evidence. The invariant checker enforces this.

## Output frontmatter

```yaml
---
source: normalized.md
chunks_covered: <int>
themes: <int>
entities: <int>
costs: <int>
commitments: <int>
walk_backs: <int>
---
```

## Rigor rules

- Use only chunk indices that exist in `normalized.md`'s `<!-- chunk N/M -->` markers.
- Timestamps cited must come from `<!-- t=MM:SS -->` comments in `normalized.md` — don't invent.
- Entity entries must cite a verbatim phrase from normalized.md OR be skipped. The entity name itself doesn't need to be quoted, but the role/context description must trace to actual transcript content.
- Walk-back entries are the highest-precision section — only include them when BOTH the ask quote and the retraction quote can be cited verbatim from `normalized.md`. False walk-backs are worse than missed ones; the checker will flag missing walk-back coverage downstream, so under-claiming is safer than over-claiming.
- Compliments-only meetings or one-chunk meetings still get an outline file (possibly with empty sections); never refuse to produce output.

## Constraints
- Do not modify `normalized.md`.
- Do not write any file other than `outline.md`.
- Do not exceed ~120 lines total output for a typical 60-minute meeting; this is a reference index, not a summary essay.

## Acceptance test
Against `meetings/mehta-dental-discovery/normalized.md`, the produced `outline.md` should include themes for after-hours phone gap, WhatsApp inbox decay, no-shows, multilingual coverage, emergency triage, prior chatbot failure, treatment-plan continuity, staff burnout, and DPDP; named entities for Mrs. Banerjee, DentalDesk, Smile Hub, Dr. Roy, Sunita; named costs for ₹1 lakh/month and ₹80K prior vendor; commitments for the Thursday 4 PM follow-up and 6-week v1; walk-backs for Marathi, insurance Q&A, and payments. Counts in frontmatter should match the section bullet counts.
