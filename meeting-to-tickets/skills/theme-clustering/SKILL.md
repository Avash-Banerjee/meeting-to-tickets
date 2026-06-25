---
name: theme-clustering
description: Group Q&A pairs in meetings/<slug>/qa.md into themed clusters at meetings/<slug>/clusters.md. Each cluster gets a suggested DevRev type (feature/task/problem) and rationale. Q&As with no fit go in Unclustered.
---

# theme-clustering

You are grouping Q&A pairs into themes a PO would groom as backlog units.

## Inputs
A path to a meeting folder. The folder must already contain `qa.md`.

## Output
Write `<meeting_folder>/clusters.md`. Do not write anything else.

## How to cluster
- A cluster is a coherent theme that could plausibly become one ticket. Examples: "Onboarding reconciliation", "Reporting export", "Access control review".
- **Cluster count is adaptive — scale to what the transcript actually justifies.** A 15-minute check-in might produce 1-2 clusters; a 60-minute discovery call typically 4-7; a multi-hour deep-dive can have 8-12. Don't force a target. If you find yourself producing many small clusters that feel redundant or could plausibly be sub-sections of a larger ticket, re-merge. If you have a single mega-cluster covering everything, look for natural sub-themes and split.
- A single Q&A may belong to multiple clusters. Overlap is allowed.
- Q&As that don't fit any theme go to `## Unclustered`. Nothing is silently dropped at this stage.

## Cluster coherence — deliverable + owner discipline

A cluster represents ONE DevRev ticket. For that, the cluster must satisfy two structural tests:

1. **One primary deliverable.** All member Q&As contribute to producing the same concrete deliverable (a feature, a methodology, a confirmation, a configuration). A Q&A that names a *dependency* of the main deliverable (e.g., "we need read-only access first") stays in the same cluster — the dependency goes into the brief's Dependencies section, not its own ticket. A Q&A that names a *separate deliverable* (e.g., one Q&A says "build a methodology section in the proposal" and another says "schedule a compliance review") must go in a separate cluster.

2. **One team owner.** A PM should be able to assign the resulting ticket to exactly one team end-to-end. If two distinct teams would need to coordinate to deliver the cluster (e.g., platform engineering + customer success, or data science + legal), the cluster is doing too much — split along the team boundary.

### Anti-pattern: domain-grouping without work-type alignment

Do NOT group items just because they share a domain or keyword. Two Q&As both touching "governance", "compliance", "data", or "security" can still be different deliverables for different teams. Same shape examples:

- A "feature build" (engineering) + a "regulatory/governance review of that feature" (legal/compliance) share the same domain word but represent different work types with different owners. Split.
- A "platform capability" (engineering) + a "customer success workflow tied to that capability" (CS/PM) share the domain but represent different deliverables. Split.
- A "data architecture decision" (platform) + a "data governance policy" (compliance/ops) share "data" but are different work types with different owners. Split.

The pattern: domain similarity is not enough. Work-type alignment AND owner alignment are the test.

### Pre-finalize self-check

Before writing `clusters.md`, walk every candidate cluster through this check:

1. List each member Q&A's likely concrete deliverable in one phrase. If the list contains more than one distinct deliverable (and they are NOT a deliverable + its dependencies), split.
2. List each member Q&A's likely owning team. If the list contains more than one distinct team owner, split.
3. Read the cluster's rationale. If the rationale uses "and" to connect distinct themes that wouldn't go to the same team (e.g., "bias mitigation and compliance approval"), that's a smell — likely needs splitting.

Lean toward MORE clusters over stuffed clusters. 10 well-scoped tickets each going to one team beat 6 mixed ones requiring cross-team coordination from the start.

## Suggested DevRev type
For each cluster, suggest one of:
- `feature` — describes a new capability the client wants.
- `task` — a discrete change to an existing capability OR a discrete piece of operational/process work (e.g., training programme, handover plan, documentation, configuration). Small scope, well-shaped, clear end-state.
- `problem` — an existing pain not yet shaped into a specific solution.
- `constraint` — a hard boundary the cluster's work must satisfy or confirm before dependent work can start. Includes regulatory/compliance requirements, commercial terms, third-party gating approvals (e.g., compliance team review), and technical limits the client has explicitly named. Not a thing to build — a thing to confirm and design around.

Type-selection guidance:
- Lean toward `problem` when the cluster is mostly Q&As from lenses 1 (problem in life), 2 (workarounds), 3 (cost).
- Lean toward `feature` when the cluster includes lens 4 (underlying need) framed as a new capability the platform should provide.
- Lean toward `task` for narrow, concrete changes OR for discrete operational/process work (training, documentation, scheduled handovers).
- Lean toward `constraint` when the cluster is about confirming or locking in a boundary (compliance approval, SOW terms, regulatory requirements, stakeholder-gated approvals). The cluster's deliverable is "confirmation obtained", not "feature built".

This type is a *suggestion* — the requirements drafter (next stage) has authority to re-classify based on closer reading. But getting it right at clustering reduces churn downstream.

## Output shape

```markdown
---
total_clusters: <int>
unclustered_qa: <int>
---

## C1 — <Theme name> (suggested type: feature | task | problem)
**Rationale:** <one line>
**Q&A:** Q<i>, Q<j>, ...

## C2 — ...

## Unclustered
- Q<i>: <one-line reason it didn't fit any cluster>
```

## Constraints
- Do not modify `qa.md`.
- Do not write any file other than `clusters.md`.
- Use only Q&A ids that exist in `qa.md`. Do not invent new ones.

## Acceptance test
Run against `meetings/clean-short/qa.md`; result should match `fixtures/expected/clean-short/clusters.md` (theme name and rationale wording may vary slightly; the cluster grouping must match).
