# Meeting-to-DevRev-Tickets

A Claude Code / Agent SDK plugin that turns meeting transcripts into DevRev-ready ticket drafts on disk, with *The Mom's Test* discipline at every stage.

## What it does

Most meeting notes capture what was said. This tool captures what actually matters — the real business problems, the evidence behind each request, and what needs to happen next.

Drop in a raw transcript. The pipeline reads it the way a good BA would: it finds the pain points, the workarounds customers are already using, the things that were asked for and then walked back, and the decisions that were made. Every finding stays linked to the exact quote it came from. Nothing is assumed. Anything without evidence is flagged or dropped.

The output is two sets of files per meeting:

- **Requirements briefs** (`requirements/*.md`) — one per business theme. Plain-language, tool-agnostic. Includes the problem statement, supporting quotes, business impact, what the customer actually needs vs. what they asked for, acceptance criteria, dependencies, and open questions. Designed for a PM or BA to review and approve before anything goes into the backlog.
- **DevRev tickets** (`devrev/*.md`) — one per brief, ready to copy-paste into DevRev. Lean engineering-handoff format. The quotes stay in the brief; the ticket just has what an engineer needs.

### How it works — the stages

| Stage | What it does |
|---|---|
| **Transcript normalization** | Cleans the raw transcript into a consistent format regardless of source (Otter.ai, VTT, plain text). |
| **Meeting outline** | Builds a reference index of recurring themes, key entities, costs mentioned, commitments made, and any points where someone asked for something and then changed their mind. |
| **Mom's Test extraction** | Reads the transcript through the lens of *The Mom's Test* — separating real business problems from feature wishes, identifying workarounds, costs of inaction, and commitments. Every finding is anchored to a verbatim quote. |
| **QA reconciliation** | For long calls split across multiple chunks, merges duplicate findings and resolves references that span different parts of the conversation. |
| **Theme clustering** | Groups related findings into logical themes — each one roughly maps to one backlog item. |
| **Requirements drafting** | Writes one structured brief per theme. |
| **DevRev export** | Converts each brief into a DevRev-ready ticket with the right type, severity, and field shape. |

### Key principles

- **Evidence-first** — every requirement traces back to a specific quote in the transcript.
- **Problem-first** — the briefs describe what hurts, not what to build. Solutions come later.
- **Hallucination-resistant** — anything not grounded in the transcript is either flagged `(inferred)` or dropped entirely.
- **Human-review in the loop** — the requirements briefs are a PM checkpoint before anything reaches engineering.

## Pipeline (adaptive: 5-stage fast path / 7-stage full path)

```
Fast path (single-chunk transcripts — most discovery calls):
source.* ──▶ normalized.md ──▶ outline.md + qa-chunks/qa-1.md + qa.md ──▶ clusters.md ──▶ requirements/*.md ──▶ devrev/*.md
            (transcript-intake)  (fast-evidence — single pass)               (theme-clustering)  (requirements-drafting)  (requirements-to-devrev)

Full path (multi-chunk transcripts — long calls, ≥45 min):
source.* ──▶ normalized.md ──▶ outline.md ──▶ qa-chunks/qa-N.md ──▶ qa.md ──▶ clusters.md ──▶ requirements/*.md ──▶ devrev/*.md
            (transcript-intake)  (meeting-outline)  (moms-test-extraction)  (qa-reconciler)  (theme-clustering)  (requirements-drafting)  (requirements-to-devrev)
                                                       per chunk
```

The `meeting-to-tickets` orchestrator picks the path automatically from `chunks: N` in the intake frontmatter, with checkpoints, idempotency, and a run.log. The DevRev export stage is optional — skip with `--no-devrev` if you only want the neutral requirement briefs.

Two output artifacts per meeting:

- **`requirements/*.md`** — neutral, tool-agnostic requirement briefs (one per cluster). PM-review shape with Problem / Evidence / Underlying need / Acceptance criteria / Dependencies / Open questions / Priority signal / Source. No DevRev/Jira/GitHub fields baked in.
- **`devrev/*.md`** — engineering-handoff DevRev-ready ticket per brief. Hybrid template adapting by requirements type (`problem`/`capability_gap`/`constraint`) with frontmatter for DevRev's data model. Verbatim transcript quotes stay in the requirements brief; the DevRev file is lean and copy-paste-ready.

## Install

This project ships in two forms — choose based on whether you want to use it or work on it.

### As a Claude Code plugin (for distribution / sharing)

The project root is a Claude Code plugin: `.claude-plugin/plugin.json` manifest, `commands/call-to-ticket.md` slash command, `skills/` skill pack (9 skills), `.claude/settings.json` permission allowlist for pipeline writes, and `scripts/` deterministic helpers.

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

# 4. Symlink all skills so Claude Code can invoke them by name
ln -s ~/.claude/plugins/meeting-to-tickets/skills/meeting-to-tickets/SKILL.md \
      ~/.claude/commands/meeting-to-tickets.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/transcript-intake/SKILL.md \
      ~/.claude/commands/transcript-intake.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/meeting-outline/SKILL.md \
      ~/.claude/commands/meeting-outline.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/fast-evidence/SKILL.md \
      ~/.claude/commands/fast-evidence.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/moms-test-extraction/SKILL.md \
      ~/.claude/commands/moms-test-extraction.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/qa-reconciler/SKILL.md \
      ~/.claude/commands/qa-reconciler.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/theme-clustering/SKILL.md \
      ~/.claude/commands/theme-clustering.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/requirements-drafting/SKILL.md \
      ~/.claude/commands/requirements-drafting.md
ln -s ~/.claude/plugins/meeting-to-tickets/skills/requirements-to-devrev/SKILL.md \
      ~/.claude/commands/requirements-to-devrev.md
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

# Neutral requirement briefs live at meetings/acme-discovery/requirements/*.md
# DevRev-ready tickets at meetings/acme-discovery/devrev/*.md
```

The SDK provides the Skill, Bash, Read, Write tools that the skills and scripts depend on. The plugin exposes:
- 9 skills under `skills/` (orchestrator + 8 stage skills)
- 1 slash command under `commands/`
- 2 Python utilities under `scripts/` (`intake.py`, `check_invariants.py`)
- Plugin-shipped permission allowlist under `.claude/settings.json`

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
4. Review `requirements/*.md` (neutral, tool-agnostic briefs — for PM review).
5. Push `devrev/*.md` (DevRev-ready ticket per brief) to DevRev via copy-paste or your own API integration.

Optional flags:
- `--no-devrev` — skip the DevRev export stage if you only want neutral requirement briefs.
- `--auto` (orchestrator) — skip stage confirmation prompts.
- `--force <stage>` (orchestrator) — rerun a specific stage. Fast path: `intake|evidence|clustering|drafting|devrev-export`. Full path: `intake|outline|extraction|reconciler|clustering|drafting|devrev-export`.

## Invariants

Run `python scripts/check_invariants.py meetings/<slug>` to validate a meeting folder. Exits 0 if all rigor invariants hold. The checker validates structural integrity, verbatim-quote provenance against `normalized.md`, AC traceability, walk-back coverage, brief-vs-cluster count parity, intake word-count round-trip, no-internal-scaffolding-in-prose, and DevRev-canonical field shape on `devrev/*.md` (dual-mode: validates both the new `requirements/`-sourced schema and the legacy `tickets/`-sourced schema).

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
| `meeting-outline` | Cross-chunk reference index (themes, entities, costs, commitments, walk-backs). Full path only. |
| `fast-evidence` | Single-pass outline + extraction + reconciliation for single-chunk transcripts. Fast path only. |
| `moms-test-extraction` | Per-chunk Mom's-Test Q&A extraction with outline as context. Full path only. |
| `qa-reconciler` | Cross-chunk dedup + walk-back resolution into consolidated qa.md. Full path only. |
| `theme-clustering` | Group Q&As into themed clusters with suggested type (problem / capability_gap / constraint / discovery) |
| `requirements-drafting` | Neutral, tool-agnostic requirement brief per cluster |
| `requirements-to-devrev` | DevRev-ready ticket per brief (hybrid template adapting by requirements type) |
| `meeting-to-tickets` | Orchestrator: picks fast or full path, chains all stages with idempotency |

