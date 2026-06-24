---
name: meeting-to-tickets
description: Run the meeting-to-tickets pipeline end-to-end for one meeting folder. Automatically chooses the fast path (3 LLM calls) for single-chunk transcripts or the full path (6+ LLM calls) for multi-chunk ones. Chains intake → evidence → clustering → drafting, with stage checkpoints, --auto, --force <stage>, idempotent reruns, and a run.log.
---

# meeting-to-tickets (orchestrator)

You are running the meeting-to-tickets pipeline for one meeting. After intake, you choose one of two paths based on the transcript's chunk count — then both paths converge at clustering and run identically from there.

## Inputs
A path to a meeting folder, plus optional flags:
- `--auto` — skip confirmation prompts; run end to end.
- `--force <stage>` — rerun the named stage even if its output is up to date. Valid stage names depend on path — see tables below.
- `--no-devrev` — skip the final DevRev export stage; stop after `requirements-drafting`. By default the DevRev export runs.

## Path selection

After running intake, read `chunks:` from `normalized.md` frontmatter:

- **`chunks: 1` → fast path** (single-pass evidence, ~3 LLM calls total)
- **`chunks: 2+` → full path** (staged evidence, ~6+ LLM calls total)

Both paths produce identical output files. Downstream stages (clustering, drafting) cannot tell which path was used.

---

## Fast path — single-chunk transcripts

| # | Stage | Skill | Input | Output |
|---|---|---|---|---|
| 1 | intake | `transcript-intake` | `source.*` | `normalized.md` |
| 2 | evidence | `fast-evidence` | `normalized.md` | `outline.md`, `qa-chunks/qa-1.md`, `qa.md` |
| 3 | clustering | `theme-clustering` | `qa.md` | `clusters.md` |
| 4 | drafting | `requirements-drafting` | `clusters.md`, `qa.md` | `requirements/*.md`, `dropped.md` |
| 5 | devrev-export | `requirements-to-devrev` | `requirements/*.md` | `devrev/*.md` |

Stage 5 runs by default but is skipped when `--no-devrev` is passed.

`--force` stage names for fast path: `intake`, `evidence`, `clustering`, `drafting`, `devrev-export`.

---

## Full path — multi-chunk transcripts

| # | Stage | Skill | Input | Output |
|---|---|---|---|---|
| 1 | intake | `transcript-intake` | `source.*` | `normalized.md` |
| 2 | outline | `meeting-outline` | `normalized.md` | `outline.md` |
| 3 | extraction | `moms-test-extraction` (looped per chunk) | `normalized.md` (one chunk), `outline.md` | `qa-chunks/qa-<N>.md` |
| 4 | reconciler | `qa-reconciler` | `qa-chunks/qa-*.md`, `outline.md` | `qa.md` |
| 5 | clustering | `theme-clustering` | `qa.md` | `clusters.md` |
| 6 | drafting | `requirements-drafting` | `clusters.md`, `qa.md` | `requirements/*.md`, `dropped.md` |
| 7 | devrev-export | `requirements-to-devrev` | `requirements/*.md` | `devrev/*.md` |

Stage 3 (extraction) is a loop: invoke `moms-test-extraction` once per chunk, producing `qa-chunks/qa-1.md`, `qa-chunks/qa-2.md`, etc.

Stage 7 runs by default but is skipped when `--no-devrev` is passed.

`--force` stage names for full path: `intake`, `outline`, `extraction`, `reconciler`, `clustering`, `drafting`, `devrev-export`.

---

## Idempotency

Before invoking any stage:
- Determine its input and output files from the table for the active path.
- If all output files exist and their mtime is newer than every input file's mtime, **skip the stage** and log `stage <name>: skipped (output up to date)`.
- `--force <stage>` overrides this for the named stage.

Dependency edges — fast path:
- `evidence` depends on `normalized.md`.
- `clustering` and `drafting` depend on `qa.md`.
- `devrev-export` depends on every file in `requirements/`.

Dependency edges — full path:
- `outline` depends on `normalized.md`.
- `extraction` (each chunk) depends on both `normalized.md` and `outline.md` — a stale outline invalidates all extraction.
- `reconciler` depends on `outline.md` AND every `qa-chunks/qa-*.md`.
- `clustering` and `drafting` depend on `qa.md`.
- `devrev-export` depends on every file in `requirements/`.

`--force` cascades naturally: forcing an earlier stage changes its output, which makes later stages' outputs stale, which causes them to re-run.

## Stage checkpoints

After each stage that ran (not skipped), unless `--auto`:
- Print a one-line summary (see below).
- Pause and ask "Continue? [Y/n]". On `n`, stop; user can resume by re-invoking.

Summaries:
- intake: `chunks=<N>`, `format_warning=<value>`, `path=fast|full`
- evidence (fast path): `qa=<int>`, `dropped=<int>`, `walk_backs=<N>`
- outline (full path): `themes=<N>`, `entities=<N>`, `walk_backs=<N>`
- extraction/chunk (full path): `chunk=<N>`, `total_qa=<int>`, `dropped=<int>`
- reconciler (full path): `qa_before_dedup=<int>`, `qa_after_dedup=<int>`, `walk_backs_resolved=<int>`
- clustering: `total_clusters=<int>`, `unclustered_qa=<int>`
- drafting: `briefs_written=<int>`, `dropped_entries=<int>`
- devrev-export: `devrev_files_written=<int>`, `blocker_promotions=<int>`

## Logging

Append one line per stage to `<meeting_folder>/run.log`:

```
<ISO-8601 timestamp> <stage>[/<chunk>] <status> <summary>
```

`<status>` ∈ {`started`, `skipped`, `done`, `failed`}. Include `path=fast` or `path=full` in the intake log line.

## Failure handling

| Failure | Hint |
|---|---|
| `normalized.md` missing | Run `transcript-intake` on this folder first. |
| `chunks:` missing from `normalized.md` frontmatter | Re-run intake — frontmatter is malformed. |
| `fast-evidence` called but `chunks` ≠ 1 | Path selection logic error — should not happen. Force `intake` to refresh chunk count, then re-run. |
| `outline.md` missing when extraction runs (full path) | Force `outline` to regenerate it. |
| Extraction produced zero grounded Q&As for a chunk | Inspect `qa-chunks/qa-<N>.md` — chunk may be compliments-only. Check against `outline.md` themes for that chunk. |
| Walk-back coverage gaps in `qa.md` | A walk-back in `outline.md` wasn't found in qa-chunks. Re-run extraction for the relevant chunks. |
| Brief count ≠ clusters minus dropped | Check `dropped.md` and `requirements/` — one is stale. |

## Constraints
- Do not modify files outside the meeting folder.
- Do not call any external service.
- Do not parse skill outputs heuristically beyond reading frontmatter for summary counts.

## Acceptance test

**Fast path:** Against a fresh single-chunk `source.*`, `--auto` produces `normalized.md`, `outline.md`, `qa-chunks/qa-1.md`, `qa.md`, `clusters.md`, `requirements/*.md`, and `run.log` with `path=fast` in the intake line. Total LLM stages: 3.

**Full path:** Against a fresh multi-chunk `source.*`, `--auto` produces `normalized.md`, `outline.md`, `qa-chunks/qa-1.md` … `qa-chunks/qa-<N>.md`, `qa.md`, `clusters.md`, `requirements/*.md`, and `run.log` with `path=full`. Total LLM stages: 4 + N (where N = chunk count).

**Both paths:** Running again is a no-op (all stages skipped). Output files are format-identical regardless of which path produced them.
