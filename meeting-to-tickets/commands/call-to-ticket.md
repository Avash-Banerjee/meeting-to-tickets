---
description: Turn a meeting transcript into DevRev-ready ticket drafts
argument-hint: <meeting-folder-or-transcript-path>
---

You are running the meeting-to-tickets pipeline on `$ARGUMENTS`.

## What to do

1. **Resolve the input.**
   - If `$ARGUMENTS` is a directory under `meetings/<slug>/` containing `source.*`, use it directly as the meeting folder.
   - If `$ARGUMENTS` is a file path to a transcript, create `meetings/<inferred-slug>/` (slug derived from the file basename), copy the file in as `source.<ext>`, and use that folder.
   - If `$ARGUMENTS` is empty, ask the user for the transcript path and stop.

2. **Run intake** by invoking the `transcript-intake` skill against the meeting folder. This is a deterministic Python script — fast and free.

3. **Run the four-stage pipeline** by invoking the `meeting-to-tickets` orchestrator skill against the meeting folder. The orchestrator will:
   - Apply `moms-test-extraction` to produce `qa.md`
   - Apply `theme-clustering` to produce `clusters.md`
   - Apply `ticket-drafting` to produce one `tickets/<NN>-<slug>.md` per cluster

4. **Run the rigor gate.** Invoke `scripts/check_invariants.py` against the meeting folder:
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_invariants.py" <meeting_folder>
   ```
   Expected: exit 0. If any violations print to stderr, surface them to the user verbatim and fix before claiming success.

5. **Report back** with:
   - Number of tickets produced (per cluster) and their titles
   - Number of Q&As extracted and any dropped
   - Whether invariants passed
   - Path to the ticket markdown files for review

## Rigor rules to honor

- Every blockquote in every ticket must be verbatim from `normalized.md` — the invariant checker enforces this; trust the failure if it fires.
- Compliments without behavioral evidence belong in `qa.md`'s `## Dropped` section, not in a ticket.
- A cluster with no grounded evidence does NOT get a ticket — append to `dropped.md` instead.
- Do not push to DevRev. This pipeline produces markdown drafts only; the user reviews and pushes manually.
