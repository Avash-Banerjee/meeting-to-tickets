---
type: feature
priority_hint: high
component: reporting
source_meeting: long-noisy
cluster_id: C1
---

# Reporting export: full-view, filter-aware, scheduled delivery

## Business goal
Eliminate a confirmed multi-team weekly export tax — Priya's team plus APAC ops both repeat the same manual stitch — and unblock finance's macro-driven close. The strategic signal is cross-region reach (APAC discovered independently last month) combined with a downstream consumer (finance) whose tooling depends on the export's exact shape.

## Description

**The problem in context.**
The existing CSV export only exports the current page, not the full filtered result set. Priya's team and APAC's ops team both perform a manual stitch-and-merge every time they need a complete export — Priya every Monday, APAC every Friday. Finance rejects files whose column order doesn't match their macro's A-through-M schema.

**What they've already tried.**
Multiple pages downloaded and manually stitched. Also tried the direct API endpoint — it returned the full dataset but in wrong column order, which crashed finance's macro.

> Priya: "Every export. I end up downloading three or four pages and stitching them."
> Priya: "I tried using the API endpoint directly last Tuesday. It returned everything, but the column order was wrong so finance rejected it."
> Priya: "They have a macro that expects columns A through M in a specific order. If the header row doesn't match, the macro crashes."

**Cost of doing nothing.**
Priya spends time stitching on every export; APAC ops lead spends every Friday on the same thing. A scheduled export would save Priya an hour per week.

> Priya: "APAC does it too. I found out last month when I was on a call with their ops lead. She spends every Friday on the same thing."
> Priya: "One more — scheduled exports would be a huge win. Right now I have a calendar reminder every Monday. If the system could just email the CSV at 8am, I'd save an hour a week."

**Stated ask vs. underlying need.**
Stated ask is a full-view export. Underlying need is a finance-compatible, filter-aware, scheduled export that works across multiple time zones without manual intervention.

> Priya: "Right. And if you're building the full-view export, please make sure it respects the active filters. Last time we got an export it dumped everything regardless of filters."
> Priya: "Configurable would be better. APAC is in a different timezone so they'd want a different slot."

**Constraints / signals from the call.**
- Multi-region impact: at least two teams (Priya's and APAC's) have the same problem.
- Finance's column spec (columns A–M) must be honored; Priya will forward the template spreadsheet.
- Scheduled delivery needs configurable time slots to accommodate different time zones.

## Acceptance criteria
- [ ] Export includes the full filtered result set, not just the current page.
- [ ] Export respects all active filters applied in the UI at time of export.
- [ ] Column order matches finance's A-through-M macro schema (spec to be provided by Priya).
- [ ] Scheduled email delivery is configurable per user/team (time and timezone).
- [ ] (inferred) APAC users can configure a different delivery time from Priya's team.

## Priority hint
**High** — multi-region impact confirmed (at minimum two teams), recurring weekly cost, finance dependency, and a concrete workaround that fails (API column order rejection). Alice noted the scope change mid-call.

## Open questions
- What is the exact column spec for finance's macro? (Priya to forward template spreadsheet.)
- Is the scheduled delivery per user, per team, or per report?
- What format should the scheduled email include — CSV only, or XLSX option?
- Row-count or file-size limits on full-view exports?

## Evidence
- qa.md → Q1, Q2, Q3, Q4
- normalized.md chunk 1 (00:06–02:44)
