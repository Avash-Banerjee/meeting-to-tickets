# Meeting-to-DevRev-Tickets

A Claude Code skill pack that turns meeting transcripts into DevRev-ready ticket drafts on disk, with *The Mom's Test* discipline at every stage.

## Pipeline

```
source.* ──▶ normalized.md ──▶ qa.md ──▶ clusters.md ──▶ tickets/*.md
            (transcript-intake)  (moms-test-extraction)  (theme-clustering)  (ticket-drafting)
```

The `meeting-to-tickets` skill chains all four stages with checkpoints and idempotency.

## Install

This project ships in two forms — choose based on whether you want to use it or work on it.

### As a Claude Code plugin (for distribution / sharing)

The project root is structured as a Claude Code plugin: a `.claude-plugin/plugin.json` manifest, a `commands/call-to-ticket.md` slash command, the `skills/` skill pack, and the `scripts/` deterministic helpers.

To install in any Claude Code environment:

```bash
# Either: clone into the user's plugins directory
git clone <repo-url> ~/.claude/plugins/meeting-to-tickets

# Or: install Python deps system-wide so the plugin's scripts can run
pip install PyYAML
```

The plugin exposes one slash command: `/call-to-ticket <meeting-folder-or-transcript-path>`. Run it from any Claude Code session; the orchestrator + rigor gate run end-to-end and report tickets.

### For workspace iteration (this repo, developing the pipeline)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements-dev.txt   # includes pytest
```

In this mode there is no plugin install — you invoke the skills directly from inside Claude Code while you're sitting in this directory. The bash invocation in `skills/transcript-intake/SKILL.md` auto-falls-back to the workspace `.venv` when `CLAUDE_PLUGIN_ROOT` is unset, so the same skill files serve both modes.

## Use

1. Create a folder for the meeting: `meetings/2026-06-19-acme-discovery/`.
2. Drop the transcript in as `source.txt` (or `.vtt`, `.srt`, `.md`).
3. From Claude Code, invoke the `meeting-to-tickets` skill against the folder.
4. Review `tickets/*.md`; edit if needed; push to DevRev manually (phase 1) or via a publish step (phase 2).

Flags:
- `--auto` — skip stage confirmation prompts.
- `--force <intake|extraction|clustering|drafting>` — rerun a specific stage.

## Invariants

Run `python scripts/check_invariants.py meetings/<slug>` to validate a meeting folder. Exits 0 if all rigor invariants hold (verbatim quotes present, valid YAML, allowed types, AC traceability).

## Tests

Run the structural-invariant pytest suite:

```bash
cd meeting-to-tickets
.venv/bin/pytest scripts/ -v
```

Run invariants against a committed fixture snapshot as a smoke test:

```bash
.venv/bin/python scripts/check_invariants.py fixtures/expected/clean-short
```

Run invariants against a live meeting folder after `meeting-to-tickets` produces outputs:

```bash
.venv/bin/python scripts/check_invariants.py meetings/<slug>
```

## Fixtures

`fixtures/` holds four regression transcripts. `fixtures/expected/<slug>/` holds committed snapshots used to detect prompt drift.

## Design

Full design and rationale: `../docs/superpowers/specs/2026-06-21-meeting-to-devrev-tickets-design.md` (in the parent project root).

## Phase 2 path

Phase 2 introduces a backend service that takes over `transcript-intake`'s mechanical work for heavier transcripts, plus a `devrev-publish` skill that pushes ticket markdown via the DevRev API. The phase 1 pipeline is structured so phase 2 is additive — see the design doc, §10.
