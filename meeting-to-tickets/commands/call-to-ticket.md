---
description: Turn a meeting transcript into DevRev-ready ticket drafts (7-stage pipeline)
argument-hint: <meeting-folder-or-transcript-path> [--no-devrev]
---

You are running the meeting-to-tickets pipeline on `$ARGUMENTS`.

## What to do

### 1. Resolve the input

- If `$ARGUMENTS` is a directory under `meetings/<slug>/` containing `source.*`, use it directly as the meeting folder.
- If `$ARGUMENTS` is a file path to a transcript, create `meetings/<inferred-slug>/` (slug derived from the file basename), copy the file in as `source.<ext>`, and use that folder.
- If `$ARGUMENTS` is empty, ask the user for the transcript path and stop.
- Honor an optional `--no-devrev` flag to skip stage 7 if the user only wants PM-review tickets.

### 2. Run the seven-stage pipeline

The `meeting-to-tickets` orchestrator skill chains the full sequence. Each stage's input is the previous stage's output file in the meeting folder.

| # | Stage | Skill | Output |
|---|---|---|---|
| 1 | intake | `transcript-intake` (calls `scripts/intake.py`) | `normalized.md` |
| 2 | outline | `meeting-outline` | `outline.md` |
| 3 | extraction (per chunk) | `moms-test-extraction` | `qa-chunks/qa-<N>.md` |
| 4 | reconciler | `qa-reconciler` | `qa.md` |
| 5 | clustering | `theme-clustering` | `clusters.md` |
| 6 | drafting | `ticket-drafting` | `tickets/*.md` + `dropped.md` |
| 7 | devrev-compactor | `devrev-compactor` (skip with `--no-devrev`) | `devrev/*.md` |

Invoke the orchestrator skill; do not manually chain. The orchestrator handles idempotency (skip stages whose output is newer than inputs), per-chunk extraction loops, and run-log appending.

### 3. Run the rigor gate

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_invariants.py" <meeting_folder>
```

Expected: exit 0. The checker validates:
- normalized.md structural integrity
- outline.md section completeness + count cross-check
- qa-chunks/ presence (one file per chunk in normalized.md)
- qa.md schema (legacy or reconciled), walk-back coverage vs outline
- clusters.md type enum, Q&A id references
- tickets/*.md frontmatter, AC traceability, no internal scaffolding in prose
- devrev/*.md 1:1 parity with tickets/, DevRev-canonical field enums
- Cross-cutting: verbatim-quote provenance (every blockquote traces to normalized.md), ticket-vs-cluster count, intake word-count round-trip

If any violations print to stderr, surface them to the user verbatim and fix before claiming success.

### 4. Report back

- Number of tickets produced (per cluster) and their titles
- Number of Q&As extracted, walk-backs resolved, any dropped
- Whether DevRev compact files were produced (or skipped via `--no-devrev`)
- Whether invariants passed
- Paths to both `tickets/` (PM review) and `devrev/` (engineering handoff)

## Rigor rules to honor

- Every blockquote in every PM-review ticket AND every DevRev compact file must be verbatim from `normalized.md` — the invariant checker enforces this; trust the failure if it fires.
- Compliments without behavioral evidence belong in `qa.md`'s `## Dropped` section, not in a ticket.
- A cluster with no grounded evidence does NOT get a ticket — append to `dropped.md` instead.
- Walk-backs declared in `outline.md` must each be covered by exactly one Q&A in `qa.md` carrying both the ask quote and the retraction quote.
- Internal scaffolding (cluster ids, Q-ids, chunk indices) appears only in YAML frontmatter and the `## Evidence` section — never in user-readable prose.
- This pipeline produces markdown drafts only. Pushing to DevRev (via API or copy-paste) is a separate downstream step the user owns; this plugin never calls the DevRev API.
