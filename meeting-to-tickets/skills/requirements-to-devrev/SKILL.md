---
name: requirements-to-devrev
description: For each neutral requirements brief in meetings/<slug>/requirements/, produce a DevRev-ready ticket at meetings/<slug>/devrev/<NN>-<slug>.md that can be copy-pasted directly into DevRev's create-work-item UI. Hybrid template — consistent outer shell, inner sections adapt by requirements type (problem | capability_gap | constraint). No verbatim transcript quotes (those stay in the requirements brief, which is the audit trail).
---

# requirements-to-devrev

You are converting neutral requirements briefs into DevRev-ready ticket files. Each brief becomes one DevRev work item that can be copy-pasted directly into DevRev's create-work-item UI.

The input is `requirements/*.md` (PM-review artifacts). The output is `devrev/*.md` (engineering-handoff artifacts). The verbatim transcript evidence stays in the requirements brief; the DevRev ticket is lean and actionable. A reader who wants to verify the transcript follows the `source_requirement` link in the frontmatter — they don't need quotes embedded in the ticket itself.

## Inputs
A path to a meeting folder. Must already contain `requirements/*.md` files.

## Output
- One markdown file per requirements brief at `<meeting_folder>/devrev/<NN>-<slug>.md` — same `NN` and `<slug>` as the input brief, so 1:1 mapping is filename-preserved.
- **Write all DevRev files in a single response using parallel Write calls.** Each file is independent and all inputs are resolved in the requirements briefs.
- Write nothing else.

## Type mapping

| Requirements `type` | DevRev `type` | Why |
|---|---|---|
| `problem` | `feature_request` | Pain identified; solution needs to be designed |
| `capability_gap` | `improvement` | Workaround exists; build the real thing |
| `constraint` | `task` | Discovery / validation activity, not a build |
| (only if brief explicitly described a defect) | `bug` | Bug fix |

## Severity mapping

- `priority: high` → `severity: high`
- `priority: medium` → `severity: medium`
- `priority: low` → `severity: low`

**Promote to `severity: blocker`** when a `constraint` brief blocks 2+ other briefs. Determine this by scanning every other brief's `## Dependencies` section: if 2 or more briefs name this constraint's theme as a dependency, promote.

## Frontmatter (every file)

```yaml
---
title: <Brief's H1 verbatim>
type: feature_request | improvement | task | bug
severity: blocker | high | medium | low
tags: [<3-5 kebab-case tags>]
source_meeting: <meeting_slug>
source_requirement: ../requirements/<NN>-<slug>.md
---
```

## Body — hybrid template

The outer shell is consistent across all types. Inner sections adapt by `type`. Always emit sections in the order below.

### Section 1: Title + meta (always)

```
# <Title>

**Type:** <human label: Feature | Improvement | Task | Bug>
**Priority:** <human label: Blocker | High | Medium | Low>
**Tags:** <comma-separated, same set as frontmatter>
```

### Section 2: Summary (always)

One paragraph, 2–3 sentences. Adapt the framing by type:
- **problem** — state the pain, not the fix. ("Patients can't reach the clinic after hours, causing missed bookings.")
- **capability_gap** — state the gap *and* the rough direction. ("Replace manual CSV exports with an automated daily pipeline integrating Salesforce, SAP, and the legacy PostgreSQL inventory system.")
- **constraint** — state what must be confirmed. ("Confirm whether the legacy PostgreSQL inventory schema can be captured before the two developers leave next month.")

### Section 3: Business Impact (problem | capability_gap only)

Bullet list. Pull from the brief's "Cost of doing nothing" and "Who has this problem" lines. Quantify when the brief did. **Omit this section entirely for `constraint` briefs** — constraints have blast radius (captured under "Blocks"), not impact.

### Section 4: Current Workaround (problem | capability_gap, only if mentioned)

Bullet list. From the brief's "What they've already tried" line. Omit if the brief said "none mentioned" or had nothing concrete.

### Section 5: Proposed Outcome / Objective (always)

- **problem | capability_gap** — header is `## Proposed Outcome`. One paragraph describing what changes for the user when the work is done.
- **constraint** — header is `## Objective`. One sentence stating what needs to be confirmed.

### Section 6: Criteria (always)

Header varies by type:
- **problem** — `## Provisional Acceptance Criteria` with one-line preamble: *"Subject to design exploration; challenge before estimation."* Then the checklist. Preserve `(inferred)` markers from the brief.
- **capability_gap** — `## Acceptance Criteria`. Checklist copied from the brief. Preserve `(inferred)` markers.
- **constraint** — `## Success Criteria`. Checklist describing what "confirmed" looks like. Adapt the brief's AC into validation criteria where needed.

If the brief had no acceptance criteria at all (all-inferred drop), write: `_To be defined after discovery._` under this header.

### Section 7: Dependencies | Blocks (always)

- **problem | capability_gap** — header is `## Dependencies`. Bullet list from the brief. Omit the section entirely if the brief had none.
- **constraint** — header is `## Blocks`. Required even if empty. Derive by scanning every other brief's `## Dependencies` section in this meeting folder: for each brief whose dependencies semantically name this constraint, add a line: `- requirements/<NN>-<slug>.md — <Title of that brief>`. If none match, write `- None identified.`

### Section 8: Open Questions (always)

Bullet list, copied from the brief's `## Open questions` section. These are pre-kickoff blockers — they must be resolved before the work item can be estimated or assigned.

### Section 9: Source (always)

```
## Source
- Requirements brief: `requirements/<NN>-<slug>.md`
- Meeting: <meeting_slug>
```

## Tag derivation

Generate 3–5 kebab-case tags per ticket. Combine:
- 1–2 **domain tags** from the theme name (e.g., "Goal/KPI tracking" → `goal-tracking`, `kpi`).
- 1 **work-state tag**: `problem`, `capability-gap`, or `constraint`.
- 1–2 **business-area tags** if obvious from the brief (e.g., `data-pipeline`, `ux`, `security`, `compliance`, `alerting`).

Avoid generic tags (`feature`, `platform`, `engineering`). Tags should narrow a backlog filter, not broaden it. Same tag set goes in both frontmatter and Section 1's `**Tags:**` line.

## Rules

- **No verbatim transcript quotes.** The requirements brief preserves them; the DevRev ticket does not duplicate them. Reviewers needing the source follow the `source_requirement` link.
- **Title is the brief's H1 verbatim.** No rephrasing, no shortening.
- **Acceptance criteria are copied from the brief.** Do not invent new criteria. Preserve `(inferred)` markers — they signal which items need a PM challenge before estimation.
- **Section order is fixed** even when adaptive headers change names. A reader scanning multiple tickets should see the same rhythm.
- **Blocks for constraints is required.** Scan all other briefs in this meeting to populate it. If genuinely nothing is blocked, write `- None identified.` — do not omit the section.
- **PARALLEL WRITES — STRICT.** Emit all DevRev `Write` calls as separate tool_use blocks inside ONE assistant response. They MUST appear in the SAME response, not split across N response turns. Splitting them is wrong: it costs N× the round-trips, triggers N separate permission prompts for the user, and serialises a workload that has zero data dependencies. Each DevRev file is independent; all inputs are resolved in the requirements briefs before this stage starts. If you find yourself acknowledging or summarising between writes, you are doing it wrong; revert and batch.

## Constraints
- Do not modify `requirements/*.md`.
- Do not write any file other than `devrev/*.md`.
- Do not invoke any external service. The DevRev API push is a downstream step the user owns.

## Acceptance test
For a meeting folder with N requirements briefs:
- `devrev/` contains exactly N files with matching `<NN>-<slug>.md` names.
- Every devrev file's frontmatter `source_requirement` resolves to an existing brief.
- Every `constraint`-type devrev file contains a `## Blocks` section.
- No blockquote lines (`>`-prefixed) appear in any devrev file body.
- The invariant checker exits 0 after running on the meeting folder.
