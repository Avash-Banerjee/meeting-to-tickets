---
name: ticket-drafting
description: For each cluster in meetings/<slug>/clusters.md, write a DevRev-ready markdown ticket at meetings/<slug>/tickets/<NN>-<slug>.md. Refuse to draft when no grounded evidence exists; append refused clusters to dropped.md.
---

# ticket-drafting

You are turning themed clusters of Mom's-Test Q&As into ticket drafts a reviewer can push to DevRev with minimal edits.

## Inputs
A path to a meeting folder. The folder must already contain `clusters.md` and `qa.md`.

## Output
- One markdown file per cluster at `<meeting_folder>/tickets/<NN>-<slug>.md`. `<NN>` is the two-digit cluster index (`01`, `02`, ...). `<slug>` is a short kebab-case slug derived from the theme name.
- For any cluster where every member Q&A is `inferred` (no grounded evidence), do not write a ticket. Append a line to `<meeting_folder>/dropped.md` instead:

```
- C<n> (<theme>) — every member Q&A is inferred; no grounded evidence to support a ticket.
```

- Write nothing else.

## Ticket template

````markdown
---
type: feature | task | problem
priority_hint: low | medium | high
component: <short slug, optional — omit if transcript doesn't name a product surface>
source_meeting: <meeting_slug>
cluster_id: C<n>
---

# <Ticket title — same as cluster theme name>

## Business goal
<One short paragraph naming the strategic outcome this ticket exists to move. Required for every ticket; use the framing that matches the ticket's `type`:
- **feature** — the strategic outcome this capability moves, distinct from the per-feature operational cost in Description.
  Example: "Stop bleeding long-term-patient revenue to competitors with 7-day phone coverage."
- **task** (engineering precondition) — what downstream feature this unblocks, and why that feature matters strategically.
  Example: "Unblock the 24/7 call answering feature, which is the project's headline revenue driver."
- **problem** (strategic case ticket) — what makes this problem worth tracking at the backlog level; what decision-making the visibility enables.
  Example: "Make front-desk attrition risk quantitatively visible so feature trims can be evaluated against retention impact, not just per-feature ROI."

Keep it to 2-4 sentences. Trace it to a Q&A or to an outline entity/commitment; do not invent strategic context the call did not establish.>

## Description

**The problem in context.**
<2–4 sentences describing the pain in the client's life. Use lens 1 (problem in life) and lens 6 (frequency/scope).>

**What they've already tried.**
<Workarounds, past tools, abandoned attempts. Use lens 2.>

> Speaker: "verbatim quote from qa.md / normalized.md"
> Speaker: "another verbatim quote"

**Cost of doing nothing.**
<Quantified or qualitative cost. Use lens 3.>

> Speaker: "verbatim quote"

**Stated ask vs. underlying need.**
<Separate what they asked for from what they need. Use lens 4.>

> Speaker: "verbatim quote"

**Constraints / signals from the call.**
- <bullet>
- <bullet>

## Acceptance criteria
- [ ] <Concrete "done when" criterion, traced to a quote.>
- [ ] <Another criterion.>
- [ ] (inferred) <Criterion not directly supported by a quote — flag so reviewer can challenge.>

## Priority hint
**<low | medium | high>** — <one-line rationale based on how the client framed urgency, frequency, or blocking effect.>

## Open questions
- <Question the transcript could not answer.>
- <Another open question.>

## Evidence
- qa.md → Q<i>, Q<j>, ...
- normalized.md chunk <n> [(MM:SS–MM:SS) if timestamps exist]
````

## Rules
- A sub-section under `## Description` is **omitted entirely** when the transcript has nothing for that lens. Do not pad with filler.
- `## Business goal` is **required** for every ticket (feature, task, or problem). Use the framing that matches the ticket type per the template above. Tracing back to a Q&A or to an outline entity/commitment is mandatory — no invented strategic context. If the transcript truly establishes no strategic motivation, the cluster probably shouldn't be a ticket at all.
- **No internal scaffolding in user-readable prose.** Cluster ids (`C1`, `C2`, ...), Q-ids (`Q1`, `Q12`, ...), and chunk indices (`chunk 1`, `chunk 2`) appear ONLY in two places: the YAML frontmatter (`cluster_id: C3`) and the `## Evidence` section (`qa.md → Q1, Q2`). They MUST NOT appear in the Business goal, Description, Acceptance criteria, Priority hint, or Open questions. When cross-referencing another ticket, use its full title ("the DentalDesk integration discovery ticket"), not its cluster id. The invariant checker enforces this.
- Every quote is **verbatim**, copied exactly from `qa.md` (which copied from `normalized.md`). No paraphrase, no ellipsis-rewrite.
- Acceptance criteria that don't trace to a quote are prefixed `(inferred)`.
- Infer `component` from the cluster theme when the transcript names a product surface (e.g. "reporting", "onboarding", "billing"). Omit the field when no component is clearly identifiable — do not guess.
- Validate your own YAML frontmatter before writing. If invalid, write to `<NN>-<slug>.md.draft` instead and log an error to the run log.
- If every member Q&A of a cluster is `inferred`, **do not** write a ticket. Append to `dropped.md` per the rule above.

## Constraints
- Do not modify `qa.md`, `clusters.md`, or `normalized.md`.
- Do not write any files outside `<meeting_folder>/tickets/` and `<meeting_folder>/dropped.md`.

## Acceptance test
Against `meetings/clean-short/`, the produced `tickets/01-reporting-export.md` (filename may vary by slug) should match `fixtures/expected/clean-short/tickets/01-reporting-export.md` in structure, frontmatter fields, set of quotes, and acceptance criteria. Wording in prose sub-sections may vary slightly.
