---
name: requirements-drafting
description: For each cluster in meetings/<slug>/clusters.md, write a neutral requirements brief at meetings/<slug>/requirements/<NN>-<slug>.md. Tool-agnostic — no DevRev/Jira/GitHub fields. One file per theme, structured for human review before any export. Use whenever clusters.md exists and you need reviewable requirements artifacts from a meeting. Replaces ticket-drafting when the goal is a neutral, exportable-to-anything artifact rather than a DevRev-ready ticket.
---

# requirements-drafting

You are turning themed clusters of Mom's-Test Q&As into neutral requirements briefs — reviewable markdown artifacts that a PM or stakeholder can approve before any tool commitment.

The output is deliberately tool-agnostic. No DevRev fields, no Jira IDs, no GitHub labels. The brief captures what the problem is and what done looks like; export adapters (DevRev, Jira, GitHub) are a separate downstream step.

## Inputs
A path to a meeting folder. The folder must already contain `clusters.md` and `qa.md`.

## Output
- One markdown file per cluster at `<meeting_folder>/requirements/<NN>-<slug>.md`. `<NN>` is the two-digit cluster index; `<slug>` is kebab-case from the theme name.
- For any cluster where every member Q&A is `inferred` (no grounded evidence), do not write a brief. Append to `<meeting_folder>/dropped.md`:
  ```
  - C<n> (<theme>) — every member Q&A is inferred; no grounded evidence to support a requirement.
  ```
- **PARALLEL WRITES — STRICT.** Emit all brief `Write` calls as separate tool_use blocks inside ONE assistant response. They MUST appear in the SAME response, not split across N response turns. Splitting them is wrong: it costs N× the round-trips, triggers N separate permission prompts for the user, and serialises a workload that has zero data dependencies. Each brief is independent; all inputs are already resolved in `clusters.md` and `qa.md` before this stage starts. If you find yourself acknowledging or summarising between writes, you are doing it wrong; revert and batch.
- Write nothing else.

## Brief template

```markdown
---
type: problem | capability_gap | constraint
priority: low | medium | high
status: draft
source_meeting: <meeting_slug>
cluster_id: C<n>
---

# <Theme name — plain language, no jargon>

## Problem statement
<2–3 sentences. What is broken or missing in their life right now? Problem-first, not solution-first. No mention of what to build — only what hurts and why it matters.>

## Evidence

> Speaker: "verbatim quote"

> Speaker: "verbatim quote"

**Who has this problem:** <the person(s) affected and how often>
**Cost of doing nothing:** <quantified or qualitative — time lost, revenue, frustration, risk>
**What they've already tried:** <workarounds, manual processes, past tools — or "none mentioned">

## Underlying need
<One short paragraph. Separate what they asked for from what they actually need. If there was a walk-back in the transcript, note it here: "Initially asked for X; rescoped to Y when Z became clear.">

## Acceptance criteria
- [ ] <Concrete "done when" criterion, traceable to evidence.>
- [ ] <Another criterion.>
- [ ] (inferred) <Criterion not directly supported by a quote — flagged for reviewer to challenge.>

## Dependencies
- <What must exist before this can be built — only if the transcript named it explicitly. Omit section entirely if none mentioned.>

## Open questions
- <What the transcript could not answer — needed before building starts.>

## Priority signal
**<low | medium | high>** — <one line: how the client framed urgency, frequency, or blocking effect>

## Source
- `qa.md` → Q<i>, Q<j>, ...
- Cluster: C<n>
```

## Type definitions

Choose the type that best describes the cluster's nature:

- **problem** — something is actively broken or painful right now. The solution is not yet defined. Most discovery-call clusters are this type.
  *Reviewer action:* Ask "have we explored at least 2–3 solution directions before committing to one?" This brief should go to a design or scoping session before estimation.

- **capability_gap** — a workaround exists but it doesn't scale, breaks under load, or causes regular downstream pain. Buildable now; the workaround tells you what the MVP needs to beat.
  *Reviewer action:* Ask "is the workaround good enough to delay this, and what's the breaking point?" The current workaround described in Evidence is the baseline the solution must demonstrably improve on.

- **constraint** — a hard boundary the solution must satisfy before dependent work can start. Not a thing to build — a thing to confirm and design around. Common sources: a third-party API that must exist, a regulatory requirement, a trust condition set by the client.
  *Reviewer action:* Identify which other briefs list this as a dependency. Sequence this before those briefs. The first acceptance criterion of a constraint brief is usually a discovery or confirmation task, not a build task.

When in doubt, use `problem`. Over-labelling as `capability_gap` or `constraint` is a common mistake; reserve those for clusters that are clearly not about pain but about limits or prerequisites.

## Rules

- **Problem statement is solution-free.** Never mention a feature, system, or fix in the Problem statement section. Only what hurts. The acceptance criteria are where solutions get defined.
- **Verbatim quotes stay verbatim.** Copy exactly from `qa.md` (which copied from `normalized.md`). No paraphrase, no compression.
- **No internal scaffolding in prose.** Cluster IDs (`C1`), Q-IDs (`Q5`), and chunk indices appear only in frontmatter and the Source section — never in the brief body.
- **Inferred criteria are flagged.** Acceptance criteria that don't trace to a quote get `(inferred)` prefix so reviewers know to challenge them.
- **Clusters with only inferred Q&As are dropped.** No grounded evidence = no brief. Append to `dropped.md`.
- **Open questions are real gaps.** Only list questions the transcript genuinely could not answer — questions the reviewer needs to resolve before work begins.

## What makes a good brief

A reviewer who has never read the transcript should be able to:
1. Understand the problem in one read of the Problem statement
2. Verify the problem is real by reading the Evidence quotes
3. Know what done looks like from the Acceptance criteria
4. Know what's still unknown from Open questions

If the brief requires the reader to go open the transcript to understand the problem, rewrite the Problem statement.

## Acceptance test
For a meeting folder with N clusters (minus any all-inferred drops), `requirements/` contains exactly N files with matching `<NN>-<slug>.md` names. Each brief's Evidence quotes appear verbatim in `qa.md`. No cluster IDs or Q-IDs appear outside frontmatter and the Source section.
