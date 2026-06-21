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
- Aim for 1–6 clusters per meeting. If you find yourself producing more, you are over-splitting — re-merge.
- A single Q&A may belong to multiple clusters. Overlap is allowed.
- Q&As that don't fit any theme go to `## Unclustered`. Nothing is silently dropped at this stage.

## Suggested DevRev type
For each cluster, suggest one of:
- `feature` — describes a new capability the client wants.
- `task` — a discrete change to an existing capability (small scope, well-shaped).
- `problem` — an existing pain not yet shaped into a specific solution.

Lean toward `problem` when the cluster is mostly Q&As from lenses 1 (problem in life), 2 (workarounds), 3 (cost). Lean toward `feature` when the cluster includes lens 4 (underlying need) framed as a new capability. Use `task` for narrow, concrete changes.

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
