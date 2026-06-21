---
name: meeting-to-tickets
description: Run the meeting-to-tickets pipeline end-to-end for a single meeting folder. Chains transcript-intake → moms-test-extraction → theme-clustering → ticket-drafting, with stage checkpoints, --auto, --force <stage>, and idempotent reruns. Writes meetings/<slug>/run.log.
---

# meeting-to-tickets (orchestrator)

You are running the four-stage pipeline for one meeting.

## Inputs
A path to a meeting folder, plus optional flags:
- `--auto` — skip confirmation prompts; run end to end.
- `--force <stage>` — rerun the given stage even if its output is newer than its input. `<stage>` is one of `intake`, `extraction`, `clustering`, `drafting`.

## Pipeline
Stages run in this order:

| # | Stage | Skill | Input | Output |
|---|---|---|---|---|
| 1 | intake | `transcript-intake` | `source.*` | `normalized.md` |
| 2 | extraction | `moms-test-extraction` | `normalized.md` | `qa.md` |
| 3 | clustering | `theme-clustering` | `qa.md` | `clusters.md` |
| 4 | drafting | `ticket-drafting` | `clusters.md`, `qa.md` | `tickets/*.md`, `dropped.md` (append) |

## Idempotency
Before invoking each sub-skill:
- Determine the stage's input file(s) and output file(s) per the table above.
- If the output file exists and its mtime is newer than every input file's mtime, **skip the stage** and log `stage <name>: skipped (output up to date)`.
- `--force <stage>` overrides this skip for the named stage.

## Stage checkpoints
After each stage that ran (not skipped), unless `--auto`:
- Print a one-line summary: e.g. `stage extraction done: 14 Q&As, 6 dropped`.
- Pause and ask the user "Continue? [Y/n]". On `n`, stop the pipeline; user can resume later by re-invoking.

Computing summaries:
- intake: number of chunks (from frontmatter) and any `format_warning`.
- extraction: `total_qa` and `dropped` from frontmatter.
- clustering: `total_clusters` and `unclustered_qa` from frontmatter.
- drafting: count of files written to `tickets/` and any entries added to `dropped.md` this run.

## Logging
Append a line per stage to `<meeting_folder>/run.log` in the form:

```
<ISO-8601 timestamp> <stage> <status> <summary>
```

`<status>` ∈ {`started`, `skipped`, `done`, `failed`}.

## Failure handling
If any stage fails (e.g. the sub-skill errored, or an input file is missing), halt the pipeline, log `failed`, and print a one-line remediation hint (e.g. "run `transcript-intake` on this folder first").

## Constraints
- Do not modify files outside the meeting folder.
- Do not call any external service.
- Do not parse skill outputs heuristically beyond reading frontmatter for summary counts — the sub-skills own their formats.

## Acceptance test
Against a fresh `meetings/clean-short/source.txt` (no prior outputs), `meeting-to-tickets --auto` produces `normalized.md`, `qa.md`, `clusters.md`, `tickets/*.md`, and a non-empty `run.log`. Running it again is a no-op (every stage skipped). Running it with `--force extraction` reruns only extraction and downstream stages whose inputs changed.
