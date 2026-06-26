---
name: requirements-drafting
description: For each cluster in meetings/<slug>/clusters.md, write a neutral requirements brief at meetings/<slug>/requirements/<NN>-<slug>.md. Tool-agnostic — no DevRev/Jira/GitHub fields. One file per theme, structured for human review before any export. Use whenever clusters.md exists and you need reviewable requirements artifacts from a meeting. Replaces ticket-drafting when the goal is a neutral, exportable-to-anything artifact rather than a DevRev-ready ticket.
---

# requirements-drafting

You are turning themed clusters of Mom's-Test Q&As into neutral requirements briefs — reviewable markdown artifacts that a PM or stakeholder can approve before any tool commitment.

The output is deliberately tool-agnostic. No DevRev fields, no Jira IDs, no GitHub labels. The brief captures what the problem is and what done looks like; export adapters (DevRev, Jira, GitHub) are a separate downstream step.

## Inputs
A path to a meeting folder. The folder must already contain `clusters.md`, `qa.md`, and `outline.md`.

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
type: problem | capability_gap | constraint | task | discovery
priority: low | medium | high
status: draft
confidence: grounded | mixed | inferred
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
**What they've already tried:** <past behaviour only — workarounds, manual processes, or tools already in use at the time of the call. Do not include future plans or intentions. If the only "workaround" described is something the client plans to do, write "none mentioned">

## Underlying need
<One short paragraph. Separate what they asked for from what they actually need. If there was a walk-back in the transcript, note it here: "Initially asked for X; rescoped to Y when Z became clear.">

## Acceptance criteria
- [ ] <Concrete "done when" criterion, traceable to evidence.>
- [ ] <Another criterion.>
- [ ] (inferred) <Criterion not directly supported by a quote — flagged for reviewer to challenge.>

## Success metric
<Only include this section when the transcript explicitly named a measurable outcome for what "working in production" looks like — a KPI, a ratio, a user behaviour the client said they would track. One or two sentences. If no success metric was surfaced in the transcript, omit this section entirely — do not write a placeholder.>

## Dependencies
- <What must exist before this can be built — only if the transcript named it explicitly. Omit section entirely if none mentioned.>

## Open questions
- <What the transcript could not answer — needed before building starts.>

## Priority signal
**<low | medium | high>** — <one line: how the client framed urgency, frequency, or blocking effect>

## Next action
- <Who does what next — derived by cross-referencing the outline's ## Commitments section against this brief's cluster. One line per relevant commitment: person, action, and whether it gates estimation. Omit this section entirely if no outline commitment relates to this brief.>

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

- **constraint** — a hard boundary the solution must satisfy before dependent work can start. Not a thing to build — a thing to confirm and design around. Common sources: a third-party API that must exist, a regulatory requirement, a trust condition set by the client, a stakeholder-gated approval (e.g., the client's compliance team must sign off).
  *Reviewer action:* Identify which other briefs list this as a dependency. Sequence this before those briefs. The first acceptance criterion of a constraint brief is usually a discovery or confirmation task, not a build task.

- **task** — a discrete piece of operational, process, or handover work with a clear end-state. Distinct from a constraint (which is about confirming a boundary) and distinct from a capability_gap (which is about building or improving a system capability). Typical task briefs: training programmes, written handover plans, documentation packages, scheduled configuration work, onboarding materials.
  *Reviewer action:* Ask "does this task have a defined time window and a clear acceptance condition?" Tasks should be scoped enough that an owner can produce a delivery date.

- **discovery** — the immediate deliverable is an investigation output, not a built capability. Use when the cluster's acceptance criteria are outputs like "test X and document the behavior", "run a discovery call and capture the user journey", or "produce a technical feasibility assessment." The problem is real but not yet understood well enough to estimate or design. Distinct from `problem` (which is ready for design exploration) and from `constraint` (which is a boundary to confirm, not a behavior to investigate). Typical discovery briefs: behavior audits, feasibility spikes, pre-requirements customer calls.
  *Reviewer action:* Ask "what does done look like, and who owns it?" Discovery briefs should produce a named artifact (a doc, a decision, a test result) with a clear owner — otherwise they will sit in the backlog indefinitely.

When in doubt, use `problem`. Over-labelling as `capability_gap`, `constraint`, `task`, or `discovery` is a common mistake — `problem` is the right default unless the cluster clearly fits one of the other shapes. Use `discovery` specifically when the ACs are investigation outputs rather than feature or process deliverables.

### Mapping from upstream clustering

The `theme-clustering` stage suggests a type using its own vocabulary (`feature` / `task` / `problem` / `constraint`). Translate to this stage's vocabulary using:

| Clustering type | Requirements type | Notes |
|---|---|---|
| `feature` | `capability_gap` | Most "feature" clusters describe a capability gap with a current workaround. If the cluster is pure greenfield with no current workaround named, use `problem` instead. |
| `task` | `task` | Direct map. Discrete operational/process work. |
| `problem` | `problem` or `discovery` | Direct map to `problem`. Downgrade to `discovery` when the cluster's ACs are investigation outputs (test X, run a call, produce a feasibility doc) rather than feature or process deliverables — the problem is real but not yet understood well enough to design. |
| `constraint` | `constraint` | Direct map. |

The drafter has final authority — re-classify if a closer reading of the cluster's Q&As reveals a different work shape than clustering suggested. The clustering type is a suggestion, not a contract.

## Rules

- **Problem statement is solution-free.** Never mention a feature, system, or fix in the Problem statement section. Only what hurts. The acceptance criteria are where solutions get defined.
- **Verbatim quotes stay verbatim.** Copy exactly from `qa.md` (which copied from `normalized.md`). No paraphrase, no compression.
- **No internal scaffolding in prose.** Cluster IDs (`C1`), Q-IDs (`Q5`), and chunk indices appear only in frontmatter and the Source section — never in the brief body.
- **Clusters with only inferred Q&As are dropped.** No grounded evidence = no brief. Append to `dropped.md`.
- **Open questions are real gaps.** Only list questions the transcript genuinely could not answer — questions the reviewer needs to resolve before work begins.
- **`confidence:` is a brief-level signal, not per-AC.** Set it in frontmatter using these definitions: `grounded` — primary evidence is client-stated and most ACs are unmarked; `mixed` — a blend of client and vendor evidence, or a meaningful share of ACs are `(inferred)`; `inferred` — primary evidence comes from the vendor/solution-side speaker, or the cluster is built mainly on open questions rather than confirmed client pain. This lets a PM sort briefs by certainty before sprint planning without opening each file.
- **`## Success metric` is conditional — omit if not in transcript.** Only write this section when the transcript explicitly named how success would be measured in production (a KPI, a ratio, a behaviour the client said they'd track). Do not invent a success metric, do not write a placeholder. If the transcript did not surface one, omit the section entirely.
- **`## Next action` is derived from the outline's commitments.** Before writing each brief, read `outline.md → ## Commitments`. For any commitment that directly relates to this brief's cluster — e.g. "clarify X with client before scoping", "deliver Y by end of month" — add one line per commitment: who, what, and whether it is a prerequisite for estimation. If no commitment relates to this brief, omit the section entirely.
- **Uncertain evidence → hedged problem statement.** When the primary evidence for a brief consists of a speaker *asking whether a problem exists* rather than confirming it ("can the AI already handle this?", "is this something we need to fine-tune?", "would this be an issue?"), the problem statement must reflect that uncertainty. Use hedged language ("may", "appears to", "unclear whether") — do not assert the problem confidently. If no speaker in the transcript confirmed the gap is real, escalate the item to an `## Open questions` entry in the most relevant brief rather than writing an independent problem statement around it.

### Acceptance criteria sourcing discipline

When you write each acceptance criterion, identify WHO proposed the substance. There are two clean categories:

- **Client-sourced** (asked, agreed, confirmed): The client either explicitly asked for this, agreed to it when proposed, or actively confirmed acceptance. These criteria remain **unmarked**.
- **Vendor-sourced** (proposed by the solution-side speaker without explicit client confirmation of the specifics): The vendor proposed an approach, a number, a methodology, or product terminology, and the client said "sounds good", "that's reasonable", or didn't object. Mark these **`(inferred)`** so the PM knows to challenge before estimation.

How to identify the vendor: the vendor frames themselves as "we will build", "our methodology", "our approach", or describes the solution. The client is the participant whose problems are being solved and who controls the buy/scope decision.

Examples:
- Vendor proposes "99.9% uptime SLA with 1-hour critical response" and client says "that's reasonable" → mark `(inferred)`. The client did not ask for these specific numbers; they accepted a proposal.
- Vendor uses product terminology like "Smart Baseline modelling" or "managed retraining pipeline" → mark `(inferred)`. The terminology is vendor-side; the client did not request it by name.
- Client says "we have a hard requirement on EU customer data" → unmarked. Client-initiated, specific.
- Client says "Slack is a must" → unmarked. Direct client commitment.

**Why this rule:** the PM reading the brief needs to know which criteria are locked-in client requirements and which are vendor proposals the client has only soft-accepted. Treating vendor-proposed specifics as fixed AC causes scope disputes later when the client renegotiates.

The same client-vs-vendor provenance logic applies to the **problem statement itself**, not only the ACs. If the core evidence for a cluster comes from the **vendor/solution-side speaker** identifying a gap themselves (e.g., a product manager saying "now that I think about it, this is a gap" or a CS team member flagging something the client never mentioned) rather than the client surfacing confirmed pain, add a one-sentence disclosure at the end of `## Problem statement`: "Note: this gap was surfaced by the [speaker role] during the call, not independently raised by the client." This tells the PM the cluster originated from internal product observation, not customer pain data — which affects prioritisation.

### Acceptance criteria traceability discipline

Every NON-`(inferred)` acceptance criterion must trace to at least one quote in `qa.md`, under one of this cluster's listed Q&A items. The test: if a PM follows the `Source` link to `qa.md` and reads the quoted evidence, can they verify the AC reflects something a client speaker actually said?

If you find yourself wanting to write an AC whose substance is NOT covered by any quote under this cluster's Q&As:

1. **First check** — is there a quote in another Q&A you overlooked that supports this AC? If yes, add that Q-ID to the Source line.
2. **If genuinely uncovered** — mark the AC `(inferred)` AND add a parenthetical noting the source (e.g., "from [speaker] at [timestamp] — not extracted as a Q&A").
3. **If even `(inferred)` feels too strong** — move it to `## Open questions` instead.

**Why this rule:** the brief is making client claims it must be able to back up. The Source link must lead a reviewer to verifiable evidence. An AC naming a specific feature (e.g., "mobile-responsive executive view") that doesn't appear in any quote under the cited Q&As is making a claim with no audit trail.

This rule often surfaces a gap in the extraction stage — if you keep finding yourself wanting to add ungrounded ACs that match the single-mention grounded-ask pattern (see `fast-evidence` / `moms-test-extraction`), the qa.md may have missed real client signals. In that case prefer flagging in `## Open questions` rather than writing an unsupported AC; the gap is then visible to the reviewer.

## What makes a good brief

A reviewer who has never read the transcript should be able to:
1. Understand the problem in one read of the Problem statement
2. Verify the problem is real by reading the Evidence quotes
3. Know what done looks like from the Acceptance criteria
4. Know what's still unknown from Open questions

If the brief requires the reader to go open the transcript to understand the problem, rewrite the Problem statement.

## Acceptance test
For a meeting folder with N clusters (minus any all-inferred drops), `requirements/` contains exactly N files with matching `<NN>-<slug>.md` names. Each brief's Evidence quotes appear verbatim in `qa.md`. No cluster IDs or Q-IDs appear outside frontmatter and the Source section.
