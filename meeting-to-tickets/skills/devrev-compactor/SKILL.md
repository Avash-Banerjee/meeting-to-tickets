---
name: devrev-compactor
description: For each PM-review ticket in meetings/<slug>/tickets/, produce a sibling meetings/<slug>/devrev/<NN>-<slug>.md that is compact, field-mapped to DevRev's data model, and ready to copy-paste or push via the DevRev API. The original ticket is preserved as the PM-review artifact; the devrev version is the engineering-handoff artifact.
---

# devrev-compactor

You are turning epic-shaped PM-review tickets into compact DevRev-canonical items. Same scope per ticket (one input → one output), different shape: shorter prose, field names mapped to DevRev's enums, frontmatter ready for either copy-paste or API push.

This is NOT a story-breakdown skill. It does not split an epic into multiple stories. It reshapes each epic ticket into a DevRev-canonical form 1:1. Story breakdown, if you want it, is a separate downstream stage.

## Inputs
A path to a meeting folder. The folder must already contain `tickets/*.md` (produced by `ticket-drafting`) and `outline.md` (for cross-meeting context).

## Output
- One markdown file per source ticket at `<meeting_folder>/devrev/<NN>-<slug>.md`. The `<NN>-<slug>` matches the source ticket's filename exactly.
- Write nothing else.

## Field mapping (single source of truth)

| Source ticket frontmatter | DevRev-canonical frontmatter | Notes |
|---|---|---|
| `type: feature` | `type: feature_request` | DevRev's enum name for new capability requests |
| `type: task` | `type: task` | Same name |
| `type: problem` | `type: improvement` | DevRev has no "problem" enum; "improvement" is closest |
| `priority_hint: high` | `severity: high` | DevRev uses `severity` on issues |
| `priority_hint: medium` | `severity: medium` | |
| `priority_hint: low` | `severity: low` | |
| `component: <slug>` | `applies_to_part: <slug>` | Slug carries through; resolved to a DevRev Part ID at push time |
| `source_meeting: <slug>` | `source_meeting: <slug>` | Carried through; becomes a custom field at push time |
| `cluster_id: C<n>` | (omitted) | Internal scaffolding — drop |

## DevRev-canonical body shape

Compact. Aim for 30-60 lines per ticket regardless of how long the source epic was.

```markdown
---
type: feature_request | task | improvement | bug
severity: blocker | high | medium | low
applies_to_part: <component-slug>
source_meeting: <meeting-slug>
source_ticket: ../tickets/<NN>-<slug>.md
tags: [meeting-to-tickets, <component-slug>]
---

# <Same title as source ticket>

## Summary
<One paragraph — 3-5 sentences. Compress the source ticket's Business goal AND the strategically-load-bearing parts of its Description into a single readable paragraph. State the problem in one sentence, the cost in one sentence, the stated ask in one sentence, the key constraint in one sentence. A DevRev reader who never opens the source ticket should still understand what the work is and why it matters.>

## Acceptance criteria
- [ ] <Same bullets as source ticket, copied verbatim. Preserve `(inferred)` prefix where present. Do not summarize criteria — they are the definition of done.>
- [ ] ...

## Top evidence
<Two to three most load-bearing verbatim quotes from the source ticket. Pick the quotes that most directly justify the work — typically the named-cost quote and the most concrete pain-evidence quote. Verbatim only; do not paraphrase.>

> Speaker: "..."
> Speaker: "..."

## Source
- PM-review ticket: `../tickets/<NN>-<slug>.md`
- Source meeting: `<meeting-slug>`
- Full evidence trail: `../qa.md`
```

## Rules

- **Compaction is mandatory.** The body must be a strict subset/summary of the source ticket. Do not introduce new claims, new acceptance criteria, or new quotes not in the source. If the source ticket said it, you can quote it; if the source didn't, you can't add it.
- **Verbatim quotes stay verbatim.** When carrying over quotes from the source ticket into Top evidence, copy them exactly. The invariant checker's verbatim-quote provenance check runs on devrev files too.
- **Acceptance criteria are copied, not summarized.** AC defines done; summarizing changes the definition. If the source ticket has 8 AC bullets, the devrev file has 8 AC bullets — same wording.
- **Drop the Business goal as a separate section** — its content folds into Summary. The DevRev reader doesn't need the strategic-vs-operational distinction the PM-review ticket draws.
- **Drop Open questions** — those belong on the PM-review epic, not the engineering item. If a question genuinely blocks the work, it should already be an acceptance criterion.
- **Internal scaffolding stays out of prose.** Same rule as the source ticket: no `C1`, `Q5`, `chunk 2` in user-facing sections. The `source_ticket` frontmatter field is the cross-link, not inline prose.

## Constraints
- Do not modify `tickets/*.md`, `qa.md`, `outline.md`, or any other upstream file.
- Do not write any files outside `<meeting_folder>/devrev/`.
- Produce exactly one devrev file per source ticket — no splitting, no merging, no skipping.

## When NOT to produce a devrev file

If a source ticket has no `applies_to_part`-able component (the `component:` field is omitted in the source), still emit the devrev file but omit `applies_to_part` from its frontmatter too. The push-time tooling will either prompt the human or default to a catch-all Part. Do not invent a component slug.

## Acceptance test
For any meeting folder where `tickets/` contains N tickets, after running this skill `devrev/` contains exactly N files with matching `<NN>-<slug>.md` names. Each devrev file's frontmatter validates against the field-mapping table above. Each devrev file's Top evidence section quotes only text that already appears verbatim in the source ticket. The invariant checker's `check_devrev_files` enforces all of this.
