---
name: meeting-to-tickets
description: Run the six-stage meeting-to-tickets pipeline end-to-end for one meeting folder. Chains transcript-intake → meeting-outline → moms-test-extraction (per chunk) → qa-reconciler → theme-clustering → ticket-drafting, with stage checkpoints, --auto, --force <stage>, idempotent reruns, and a run.log.
---

# meeting-to-tickets (orchestrator)

You are running the six-stage pipeline for one meeting.

## Inputs
A path to a meeting folder, plus optional flags:
- `--auto` — skip confirmation prompts; run end to end.
- `--force <stage>` — rerun the given stage even if its output is newer than its input. `<stage>` is one of `intake`, `outline`, `extraction`, `reconciler`, `clustering`, `drafting`.

## Pipeline
Stages run in this order:

| # | Stage | Skill | Input | Output |
|---|---|---|---|---|
| 1 | intake | `transcript-intake` | `source.*` | `normalized.md` |
| 2 | outline | `meeting-outline` | `normalized.md` | `outline.md` |
| 3 | extraction | `moms-test-extraction` (looped per chunk) | `normalized.md` (one chunk), `outline.md` | `qa-chunks/qa-<N>.md` |
| 4 | reconciler | `qa-reconciler` | `qa-chunks/qa-*.md`, `outline.md` | `qa.md` |
| 5 | clustering | `theme-clustering` | `qa.md` | `clusters.md` |
| 6 | drafting | `ticket-drafting` | `clusters.md`, `qa.md` | `tickets/*.md`, `dropped.md` (append) |
| 7 | devrev-compactor | `devrev-compactor` | `tickets/*.md`, `outline.md` | `devrev/*.md` |

Stage 3 (extraction) is a loop: for an N-chunk meeting, you invoke `moms-test-extraction` N times — once per chunk — producing `qa-chunks/qa-1.md`, `qa-chunks/qa-2.md`, etc.

Stage 7 (devrev-compactor) is optional in this orchestrator. It runs by default but can be skipped with `--no-devrev` if the user only wants the PM-review tickets. The compactor produces a 1:1 sibling for each `tickets/*.md` in `devrev/`, formatted for direct DevRev copy-paste or API push. The original `tickets/` files remain the PM-review artifact.

## Idempotency
Before invoking each sub-skill (or each chunk's extraction):
- Determine the stage's input file(s) and output file(s) per the table above.
- If the output file exists and its mtime is newer than every input file's mtime, **skip the stage** and log `stage <name>: skipped (output up to date)`.
- `--force <stage>` overrides this skip for the named stage.

Dependency edges to honor:
- outline depends on intake (`normalized.md`).
- extraction (per chunk) depends on BOTH intake and outline — a stale outline invalidates extraction.
- reconciler depends on outline AND every `qa-chunks/qa-*.md`.
- clustering and drafting depend on the reconciled `qa.md`.

When `--force` cascades: forcing an earlier stage means later stages will re-run naturally as their inputs change.

## Stage checkpoints
After each stage that ran (not skipped), unless `--auto`:
- Print a one-line summary.
- Pause and ask the user "Continue? [Y/n]". On `n`, stop the pipeline; user can resume by re-invoking.

Computing summaries:
- intake: `chunks=<N>`, `format_warning=<value>`.
- outline: `themes=<N>`, `entities=<N>`, `walk_backs=<N>`.
- extraction (each chunk): `chunk=<N>`, `total_qa=<int>`, `dropped=<int>`.
- reconciler: `qa_before_dedup=<int>`, `qa_after_dedup=<int>`, `walk_backs_resolved=<int>`.
- clustering: `total_clusters=<int>`, `unclustered_qa=<int>`.
- drafting: `tickets_written=<int>`, `dropped_entries=<int>`.

## Logging
Append a line per stage (or per per-chunk extraction) to `<meeting_folder>/run.log`:

```
<ISO-8601 timestamp> <stage>[/<chunk>] <status> <summary>
```

`<status>` ∈ {`started`, `skipped`, `done`, `failed`}.

## Failure handling
If any stage fails, halt the pipeline, log `failed`, and print a one-line remediation hint. Examples:

| Failure | Hint |
|---|---|
| `normalized.md` missing | Run `transcript-intake` on this folder first. |
| `outline.md` missing when extraction tries to run | Run `meeting-outline` first; check that `normalized.md` is well-formed (frontmatter `chunks: <int>` present). |
| extraction produced zero grounded Q&As for a chunk | Inspect `qa-chunks/qa-<N>.md` — the chunk may be all compliments. Compare against `outline.md` themes for that chunk to confirm. |
| reconciler's walk-back coverage gaps section non-empty | A walk-back declared in `outline.md` couldn't be located in qa-chunks. Re-run extraction for the chunks containing the ask and the retraction. |
| ticket count != clusters minus dropped | Check `dropped.md` for cluster-level drops and `tickets/` for files; one or the other is out of date. |

## Constraints
- Do not modify files outside the meeting folder.
- Do not call any external service.
- Do not parse skill outputs heuristically beyond reading frontmatter for summary counts.

## Acceptance test
Against a fresh `meetings/<slug>/source.*` (no prior outputs), `meeting-to-tickets --auto` produces:
- `normalized.md` (intake)
- `outline.md` (outline)
- `qa-chunks/qa-1.md` … `qa-chunks/qa-<N>.md` (one per chunk)
- `qa.md` (reconciled, deduped, with `walk_backs_resolved` equal to `outline.md`'s declared walk-back count)
- `clusters.md`
- `tickets/*.md` (+ `dropped.md` for refused clusters)
- `run.log` recording every stage and per-chunk extraction call

Running it again is a no-op (every stage skipped). `--force outline` reruns outline, extraction (all chunks), reconciler, clustering, and drafting because each depends on the previous. `--force <one chunk's extraction>` is not supported at this level — force the whole extraction stage if needed.
