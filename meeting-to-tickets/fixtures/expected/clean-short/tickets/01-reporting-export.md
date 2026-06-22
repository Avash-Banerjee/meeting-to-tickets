---
type: feature
priority_hint: medium
component: reporting
source_meeting: clean-short
cluster_id: C1
---

# Reporting export to CSV/XLSX

## Business goal
Unblock finance's monthly close by removing the weekly screenshot-and-retype reconciliation cycle that lands on a single ops person. The strategic signal is repeated cross-team friction (finance has independently asked twice for a CSV they can drop into their model) — not a personal preference but a recurring interdepartmental dependency.

## Description

**The problem in context.**
Acme's ops team needs a reliable monthly handoff to finance. Today the process is a weekly manual reconciliation that lands on one person and blocks finance's month-end close.

**What they've already tried.**
Screenshots of the dashboard retyped into a spreadsheet for finance. Earlier attempt with a shared Notion page was abandoned because the data went stale.

> Priya: "I open the new-accounts dashboard, screenshot it, then retype the numbers into a spreadsheet for finance."
> Priya: "We tried a shared Notion page last quarter. It just got out of date too fast."

**Cost of doing nothing.**
Most of a working day per week from Priya plus a recurring blocker for finance's month-end close.

> Priya: "I spent almost a full day chasing missing fields in onboarding."
> Priya: "Finance can't close the month."

**Stated ask vs. underlying need.**
The client asked for "an export button." The underlying need is a finance handoff that mirrors the current dashboard view and matches finance's expected column order.

> Priya: "At minimum, give me a CSV that matches what I'm looking at on the dashboard — same filters, same date range."

## Acceptance criteria
- [ ] User can export the new-accounts dashboard's current view to CSV from the dashboard header.
- [ ] Export respects the active date range and any applied filters.
- [ ] XLSX export available as a follow-up option (separate ticket if scope grows).
- [ ] (inferred) Column ordering matches finance's existing model.

## Priority hint
**Medium** — recurring weekly pain with a named workaround. Not blocking, high frustration, blocks finance's month-end close.

## Open questions
- What is finance's expected column ordering? (Priya did not know off-hand.)
- Are there role/permission constraints on who can export?
- Is there a row-count cap we should enforce on CSV exports?

## Evidence
- qa.md → Q1, Q2, Q3, Q4
- normalized.md chunk 1
