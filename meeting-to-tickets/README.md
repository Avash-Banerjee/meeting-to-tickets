# Meeting-to-DevRev-Tickets

A Claude Code / Agent SDK plugin that turns meeting transcripts into DevRev-ready ticket drafts on disk, with *The Mom's Test* discipline at every stage.

## Pipeline (7 stages)

```
source.* ──▶ normalized.md ──▶ outline.md ──▶ qa-chunks/qa-N.md ──▶ qa.md
            (transcript-intake)  (meeting-outline)  (moms-test-extraction)  (qa-reconciler)
                                                       per chunk
                            │
                            └──▶ clusters.md ──▶ tickets/*.md ──▶ devrev/*.md
                                  (theme-clustering)  (ticket-drafting)  (devrev-compactor)
                                                                          optional, skip with --no-devrev
```

The `meeting-to-tickets` skill chains all seven stages with checkpoints, idempotency, and a run.log. Two output artifacts per meeting:

- **`tickets/*.md`** — PM-review epic-shaped markdown with full Mom's-Test Description, Business Goal, Acceptance Criteria, Priority Hint, Open Questions, Evidence trail.
- **`devrev/*.md`** — engineering-handoff compact markdown with DevRev-canonical frontmatter (type/severity/applies_to_part), one-paragraph summary, verbatim AC, top evidence, source link.

## Install

This project ships in two forms — choose based on whether you want to use it or work on it.

### As a Claude Code plugin (for distribution / sharing)

The project root is a Claude Code plugin: `.claude-plugin/plugin.json` manifest, `commands/call-to-ticket.md` slash command, `skills/` skill pack (8 skills), and `scripts/` deterministic helpers.

```bash
# 1. Clone into the user's plugins directory
git clone <repo-url> ~/.claude/plugins/meeting-to-tickets

# 2. Install Python deps for the deterministic scripts
pip install PyYAML

# 3. Symlink the slash command into ~/.claude/commands/
#    (Claude Code reads custom slash commands only from this directory)
mkdir -p ~/.claude/commands
ln -s ~/.claude/plugins/meeting-to-tickets/commands/call-to-ticket.md \
      ~/.claude/commands/call-to-ticket.md

# 4. Symlink all 8 skills so Claude Code can invoke them by name
ln -s ~/.claude/plugins/meeting-to-tickets/skills/meeting-to-tickets/SKILL.md \
      ~/.claude/commands/meeting-to-tickets.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/transcript-intake/SKILL.md \
      ~/.claude/commands/transcript-intake.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/meeting-outline/SKILL.md \
      ~/.claude/commands/meeting-outline.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/moms-test-extraction/SKILL.md \
      ~/.claude/commands/moms-test-extraction.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/qa-reconciler/SKILL.md \
      ~/.claude/commands/qa-reconciler.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/theme-clustering/SKILL.md \
      ~/.claude/commands/theme-clustering.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/ticket-drafting/SKILL.md \
      ~/.claude/commands/ticket-drafting.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/devrev-compactor/SKILL.md \
      ~/.claude/commands/devrev-compactor.md
```

> **Why the symlinks?** Claude Code's local plugin system does not auto-discover `commands/` or `skills/` from `~/.claude/plugins/`. The only directory it reads custom slash commands and skills from is `~/.claude/commands/`. The symlinks above wire the two together without duplicating files.

After setup, the plugin exposes one slash command: `/call-to-ticket <meeting-folder-or-transcript-path> [--no-devrev]`. From any Claude Code session, the orchestrator + rigor gate run end-to-end and report tickets.

### As a Claude Agent SDK plugin (for embedding in your own tool)

The same plugin layout works for any host built on the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Your app loads the plugin from a directory; the SDK auto-discovers `skills/` and `commands/`.

```python
# Python example using claude-agent-sdk
from claude_agent_sdk import Agent

agent = Agent(
    model="claude-sonnet-4-6",
    plugin_paths=["/path/to/meeting-to-tickets"],   # this repo's root
)

# Either: trigger via slash command
result = await agent.run_slash_command(
    "/call-to-ticket /path/to/transcript.txt"
)

# Or: invoke the orchestrator skill directly
result = await agent.run_skill(
    "meeting-to-tickets",
    args={"meeting_folder": "meetings/acme-discovery/"},
)

# Tickets live at meetings/acme-discovery/tickets/*.md
# Compact DevRev-shape items at meetings/acme-discovery/devrev/*.md
```

The SDK provides the Skill, Bash, Read, Write tools that the skills and scripts depend on. The plugin exposes:
- 8 skills under `skills/` (orchestrator + 7 stage skills)
- 1 slash command under `commands/`
- 2 Python utilities under `scripts/` (`intake.py`, `check_invariants.py`)

For agents that don't speak slash commands, just call the orchestrator skill by name with the meeting folder as input.

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
3. From Claude Code, type `/call-to-ticket meetings/2026-06-19-acme-discovery/` — or invoke the `meeting-to-tickets` orchestrator skill against the folder.
4. Review `tickets/*.md` (epic-shaped, for PM review).
5. Push `devrev/*.md` (compact, DevRev-canonical) to DevRev via copy-paste or your own API integration.

Optional flags:
- `--no-devrev` — skip stage 7 if you only want PM-review tickets.
- `--auto` (orchestrator) — skip stage confirmation prompts.
- `--force <stage>` (orchestrator) — rerun a specific stage; valid: `intake|outline|extraction|reconciler|clustering|drafting|devrev`.

## Invariants

Run `python scripts/check_invariants.py meetings/<slug>` to validate a meeting folder. Exits 0 if all rigor invariants hold. The checker validates structural integrity, verbatim-quote provenance against `normalized.md`, AC traceability, walk-back coverage, ticket-vs-cluster count parity, intake word-count round-trip, no-internal-scaffolding-in-prose, and the DevRev-canonical field shape on `devrev/*.md`.

## Tests

```bash
cd meeting-to-tickets
.venv/bin/pytest scripts/ -v
```

Run invariants against the committed fixture snapshots as a smoke test:

```bash
.venv/bin/python scripts/check_invariants.py fixtures/expected/clean-short
```

## Fixtures

`fixtures/` holds four regression transcripts (clean-short, long-noisy, compliments-only, no-speaker-labels). `fixtures/expected/<slug>/` holds committed snapshots used to detect prompt drift. The fixtures are deliberately domain-agnostic — they cover the structural shapes (1-chunk vs multi-chunk, with/without speaker labels, compliments-only stress test) without baking in any vertical-specific content.

## Skills

| Skill | Role |
|---|---|
| `transcript-intake` | Mechanical normalization (Python script under the hood) |
| `meeting-outline` | Cross-chunk reference index (themes, entities, costs, commitments, walk-backs) |
| `moms-test-extraction` | Per-chunk Mom's-Test Q&A extraction with outline as context |
| `qa-reconciler` | Cross-chunk dedup + walk-back resolution into consolidated qa.md |
| `theme-clustering` | Group Q&As into 1-N themed clusters with suggested DevRev type |
| `ticket-drafting` | PM-review epic markdown per cluster |
| `devrev-compactor` | DevRev-canonical compact sibling per ticket |
| `meeting-to-tickets` | Orchestrator: chains all 7 stages with idempotency |

## Design

Full design and rationale: `docs/superpowers/specs/2026-06-21-meeting-to-devrev-tickets-design.md` (in the parent project root if you cloned the workspace; in this repo if you cloned just the plugin).

## Phase 2 paths

- **Backend service for intake** — heavier transcripts (multi-hour calls, parallel meetings) processed outside a session.
- **devrev-publish skill** — calls DevRev API directly using the `devrev/*.md` files this plugin already produces. Field mapping is already done; this just needs the API client and Part-ID lookup.
- **Multi-meeting state** — themes deduplicating across calls (the same client mentioned in three meetings = one ticket, not three).
