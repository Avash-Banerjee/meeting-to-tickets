---
type: feature
priority_hint: high
component: access-control
source_meeting: long-noisy
cluster_id: C2
---

# Self-serve access control with audit log

## Business goal
Close a named-and-measured compliance gap (24-hour logging policy currently unmet, confirmed first-quarter security incident with a six-week access overhang) and remove the IT-ticket bottleneck on time-sensitive lifecycle changes. The strategic signal is that the existing manual path has produced both audited risk and onboarding-survey damage; the cost is no longer hypothetical.

## Description

**The problem in context.**
Priya cannot provision or deprovision team members herself — all access changes require an IT ticket. This has caused a four-day access gap for a new hire (Jess), a contractor who left before IT finished provisioning, and a security incident where an ex-contractor's account remained active six weeks after offboarding.

**What they've already tried.**
Filing IT tickets for every access change — provisioning, deprovisioning, and group membership. There is no self-serve path; even removing access for someone who left the company requires waiting on IT.

> Priya: "I went to add her to the reporting group and the button was greyed out. I had to file a ticket with IT."
> Priya: "None. Everything goes through IT. Even removing someone who left the company — I file a ticket and then cross my fingers."

**Cost of doing nothing.**
Four-day average provisioning delays, a contractor who churned before getting access, a confirmed security incident, and near-miss compliance windows. Priya's policy requires access changes to be logged within 24 hours — currently impossible without IT involvement.

> Priya: "Four days. Jess couldn't see anything for four days. It came up in her onboarding survey — she rated \"access to tools\" as her lowest score."
> Priya: "We had an incident in Q1 where a contractor's account was still active six weeks after they finished. Security flagged it."
> Priya: "Our policy says the access change has to be logged within 24 hours. Currently there's no log at all on our end — IT keeps theirs separately."

**Stated ask vs. underlying need.**
Stated ask: add someone to a group myself with immediate effect. Underlying need: full lifecycle self-serve access management (provision, deprovision, audit log) that satisfies compliance requirements and eliminates the IT bottleneck for time-sensitive changes.

> Priya: "I need to be able to add someone to a group myself, see it take effect immediately, and get an audit log I can show compliance."
> Priya: "Can the audit log be exportable too? Our compliance team wants it as a spreadsheet, not a UI."

**Constraints / signals from the call.**
- Provisioning delay pattern confirmed across at least three people in six months (Jess, Marcus, February contractor).
- Deprovisioning risk is at least as urgent as provisioning — security flagged a six-week access overhang.
- Compliance requirement: access changes logged within 24 hours.
- Audit log must be exportable as a spreadsheet (not just a UI view).
- Acceptable interim: disable account immediately with async IT cleanup, rather than waiting for full deprovisioning.

## Acceptance criteria
- [ ] Team admin can add a user to a group without filing an IT ticket; change takes effect immediately.
- [ ] Team admin can disable a user's account immediately; full deprovisioning can happen asynchronously.
- [ ] All access changes are logged in a unified audit log visible to the team admin within 24 hours.
- [ ] Audit log is exportable as a spreadsheet (CSV or XLSX).
- [ ] (inferred) Compliance export includes timestamp, actor, action, and affected user for each change.

## Priority hint
**High** — confirmed security incident, near-missed compliance window, repeated onboarding friction, and a specific 24-hour logging policy requirement that is currently unmet.

## Open questions
- What groups/roles can Priya manage vs. which must stay with IT?
- Is the "disable immediately" action available to all admins or only designated roles?
- What fields are required in the compliance-facing audit log export?
- Does the 24-hour logging window apply to all access changes or only terminations?

## Evidence
- qa.md → Q5, Q6, Q7, Q8, Q9
- normalized.md chunk 1 (02:44–06:22)
