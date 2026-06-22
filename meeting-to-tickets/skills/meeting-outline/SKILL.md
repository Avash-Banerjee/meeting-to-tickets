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

A theme is NOT a Q&A pair. It's a topical grouping that the downstream extractor uses to anticipate cross-chunk references. The right number of themes scales with the meeting: a 15-minute check-in might have 2-3; a 60-minute discovery call typically 6-10; a multi-hour deep-dive can have 15+. Don't pad and don't compress — track what the transcript actually surfaces.

### Named entities
People (other than meeting participants), places, products, prior incidents, named systems, competitors, vendors, customers — anything referenced more than once OR introduced with notable context. Each entry: name — one-line role/context — `intro chunk N (t=MM:SS)`.

```
- <PersonName> — <role/relationship>; intro chunk N (t=MM:SS)
- <ProductOrSystemName> — <one-line description>; intro chunk N (t=MM:SS)
- <CompetitorOrVendor> — <relevance>; intro chunk N (t=MM:SS)
```

When the same entity is described differently across chunks ("the <Name> case" in chunk 1, "that situation" in chunk 3), the entity belongs here so downstream stages can resolve the reference. Meeting participants themselves go in `normalized.md`'s `participants:` frontmatter, not here.

### Named costs
Specific quantified costs the client mentioned (currency amounts, hours, days, percentages, headcount). Each entry: cost — context — `(speaker, t=MM:SS)`.

```
- <amount/unit> <what this measures> (<speaker>, t=MM:SS)
- <hours/period> spent on <activity> (<speaker>, t=MM:SS)
```

These are evidence the reconciler uses to accumulate cost-of-doing-nothing evidence under a single Q&A even when the cost numbers span chunks.

### Commitments
Decisions explicitly made or actions agreed during the call. Each entry: decision — `(t=MM:SS)`.

```
- <date/time> follow-up <type> (t=MM:SS)
- <scope decision or commitment> (t=MM:SS)
```

### Walk-backs (Mom's-Test pivots — critical)

A *walk-back* is a Mom's-Test pattern where the client states an ask, and either the client themselves or the interviewer's probing leads to retracting or rescoping it. These are easy to miss when the ask and the retraction sit in different chunks.

Each walk-back: short name — original ask (chunk and timestamp) — walked-back scope (chunk and timestamp).

```
- <Feature or scope name> — asked at chunk N (t=MM:SS) — walked back to "<short quote of new scope>" at chunk M (t=MM:SS)
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
- Size scales with the meeting — there is no fixed length. As a rough sanity check, a 60-minute discovery call typically produces an outline of ~80-150 lines. Much shorter for a 15-minute check-in; much longer for a multi-hour deep-dive. Don't pad to hit a target; don't compress away real signal.

## Acceptance test
Against `fixtures/expected/clean-short/normalized.md` (the canonical short-call fixture), the produced `outline.md` should declare counts in frontmatter that match the bullet counts in each section, name every recurring entity/cost/commitment grounded in the transcript, and surface every Mom's-Test walk-back that occurred in the call. Against `fixtures/expected/long-noisy/normalized.md`, themes should span both stated topics and the recurring entities should include any that re-appear across chunks. Against `fixtures/expected/compliments-only/normalized.md` the outline may be near-empty in every section — that is the correct outcome when the call contains no grounded material.
