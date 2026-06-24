---
description: Turn a meeting transcript into neutral requirements briefs (adaptive pipeline — fast path for short calls, full path for long ones)
argument-hint: <meeting-folder-or-transcript-path> [--no-devrev]
---

You are running the meeting-to-tickets pipeline on `$ARGUMENTS`.

## What to do

### 1. Resolve the input

- If `$ARGUMENTS` is a directory under `meetings/<slug>/` containing `source.*`, use it directly as the meeting folder.
- If `$ARGUMENTS` is a file path to a transcript, create `meetings/<inferred-slug>/` (slug derived from the file basename), copy the file in as `source.<ext>`, and use that folder.
- If `$ARGUMENTS` is empty, ask the user for the transcript path and stop.
- Honor an optional `--no-devrev` flag to skip the DevRev export adapter if the user only wants neutral requirement briefs.

### 2. Run the orchestrator (adaptive pipeline)

Invoke the `meeting-to-tickets` orchestrator skill. After intake, it picks one of two paths based on the transcript's chunk count:

**Fast path** (single-chunk transcripts — most discovery calls):

| # | Stage | Skill | Output |
|---|---|---|---|
| 1 | intake | `transcript-intake` (calls `scripts/intake.py`) | `normalized.md` |
| 2 | evidence | `fast-evidence` (single-pass outline + Q&As) | `outline.md`, `qa-chunks/qa-1.md`, `qa.md` |
| 3 | clustering | `theme-clustering` | `clusters.md` |
| 4 | drafting | `requirements-drafting` | `requirements/*.md` + `dropped.md` |

**Full path** (multi-chunk transcripts — long calls, ≥45 minutes typically):

| # | Stage | Skill | Output |
|---|---|---|---|
| 1 | intake | `transcript-intake` | `normalized.md` |
| 2 | outline | `meeting-outline` | `outline.md` |
| 3 | extraction (per chunk) | `moms-test-extraction` | `qa-chunks/qa-<N>.md` |
| 4 | reconciler | `qa-reconciler` | `qa.md` |
| 5 | clustering | `theme-clustering` | `clusters.md` |
| 6 | drafting | `requirements-drafting` | `requirements/*.md` + `dropped.md` |

Both paths produce identical output file formats. Downstream tooling cannot tell which path was used.

Optional export adapter (runs by default, skip with `--no-devrev`):

| Stage | Skill | Output |
|---|---|---|
| devrev-compactor | `devrev-compactor` | `devrev/*.md` |

Invoke the orchestrator; do not manually chain. The orchestrator handles path selection, idempotency, per-chunk extraction loops, and run-log appending.

### 3. Run the rigor gate

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_invariants.py" <meeting_folder>
```

Expected: exit 0. The checker validates:
- normalized.md structural integrity
- outline.md section completeness + count cross-check
- qa-chunks/ presence (one file per chunk in normalized.md — including the synthetic qa-1.md the fast path produces)
- qa.md schema, walk-back coverage vs outline
- clusters.md type enum, Q&A id references
- requirements/*.md frontmatter, AC traceability, no internal scaffolding in prose
- devrev/*.md 1:1 parity with requirements/ (when devrev stage ran)
- Verbatim-quote provenance against `normalized.md`, brief-vs-cluster count parity, intake word-count round-trip

If any violations print to stderr, surface them to the user verbatim and fix before claiming success.

### 4. Report back

- Which path ran (fast or full) and total LLM stages used
- Number of requirement briefs produced and their titles
- Q&As extracted, walk-backs resolved, dropped entries
- Whether DevRev compact files were produced (or skipped via `--no-devrev`)
- Whether invariants passed
- Path to `requirements/` (neutral briefs for human review) and `devrev/` if produced

## Rigor rules to honor

- Every blockquote in every requirements brief AND every DevRev compact file must be verbatim from `normalized.md` — the invariant checker enforces this.
- Compliments without behavioral evidence belong in `qa.md`'s `## Dropped` section, not in a brief.
- A cluster with no grounded evidence does NOT get a brief — append to `dropped.md` instead.
- Walk-backs declared in `outline.md` must each be covered by exactly one Q&A in `qa.md` carrying both the ask quote and the retraction quote.
- Internal scaffolding (cluster IDs, Q-IDs, chunk indices) appears only in YAML frontmatter and the `## Source` section — never in user-readable prose.
- The requirements briefs are neutral by design. Pushing to DevRev/Jira/GitHub is a separate adapter step that runs on top of `requirements/`.
