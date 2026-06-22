---
source: normalized.md
chunks_processed: 1
total_qa: 9
dropped: 2
---

### Q1 — CSV export only exports current page, not full filtered view (lens: problem in life)
**Answer:** The existing CSV export is limited to the currently visible page rather than the full filtered result set, forcing Priya to download multiple pages and stitch them manually on every export.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "The CSV export from last week works, but it only includes the current page — not the whole filtered view."
- Priya: "Every export. I end up downloading three or four pages and stitching them."

### Q2 — Workaround: direct API call, rejected by finance due to column order (lens: what they've already tried)
**Answer:** Priya tried the direct API endpoint to get the full export, but finance rejected the output because the column order did not match their macro's expectations.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "I tried using the API endpoint directly last Tuesday. It returned everything, but the column order was wrong so finance rejected it."
- Priya: "They have a macro that expects columns A through M in a specific order. If the header row doesn't match, the macro crashes."

### Q3 — Multi-region scope: APAC has the same stitch-and-merge workaround (lens: frequency and scope)
**Answer:** The reporting export pain is not isolated to Priya's team — APAC's ops lead has the same problem and spends every Friday doing the same manual stitch-and-merge.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "APAC does it too. I found out last month when I was on a call with their ops lead. She spends every Friday on the same thing."

### Q4 — Scheduled export would save an hour per week (lens: cost)
**Answer:** A scheduled export that emails the CSV at 8am would save Priya an hour a week and eliminate a manual calendar reminder she currently uses.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "One more — scheduled exports would be a huge win. Right now I have a calendar reminder every Monday. If the system could just email the CSV at 8am, I'd save an hour a week."
- Priya: "Configurable would be better. APAC is in a different timezone so they'd want a different slot."

### Q5 — Self-serve provisioning blocked: button greyed out, requires IT ticket (lens: problem in life)
**Answer:** Priya cannot provision new team members herself — the button is greyed out and she must file an IT ticket. A recent new hire (Jess) had no dashboard access for four days during onboarding.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "I went to add her to the reporting group and the button was greyed out. I had to file a ticket with IT."
- Priya: "Four days. Jess couldn't see anything for four days. It came up in her onboarding survey — she rated \"access to tools\" as her lowest score."

### Q6 — Provisioning delay is a pattern, not a one-off (lens: frequency and scope)
**Answer:** The four-day provisioning delay happened three times in six months: with Jess, with Marcus two months ago, and with a contractor who left before IT finished.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "No, same thing happened with Marcus two months ago. And with the contractor we brought on in February — she left before IT finished the provisioning."

### Q7 — Deprovisioning security risk: ex-contractor's account active six weeks after offboarding (lens: cost)
**Answer:** Because deprovisioning also goes through IT, accounts can remain active long after someone leaves — an incident in Q1 saw a contractor's account still active six weeks post-departure, flagged by security.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "We had an incident in Q1 where a contractor's account was still active six weeks after they finished. Security flagged it."
- Priya: "If I could at least disable an account myself immediately and then let IT clean it up later, that would cover the risk."

### Q8 — No unified audit log; compliance log retrieval took three days (lens: cost)
**Answer:** There is no unified audit log on the client side — IT keeps their own. Last time compliance asked, it took three days to get IT's logs, nearly missing a compliance window. Policy requires logging access changes within 24 hours.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "Our policy says the access change has to be logged within 24 hours. Currently there's no log at all on our end — IT keeps theirs separately."
- Priya: "Yes, and that took three days last time. We almost missed a compliance window."

### Q9 — Stated ask vs. underlying need: self-serve provisioning + exportable audit log (lens: ask vs. need)
**Answer:** Priya asked for the ability to add someone to a group herself with immediate effect. The underlying need is full lifecycle access management (provision, deprovision, audit) that is self-serve and compliance-ready, including an exportable audit log.
**Confidence:** grounded
**Chunk:** 1
**Quotes:**
- Priya: "I need to be able to add someone to a group myself, see it take effect immediately, and get an audit log I can show compliance."
- Priya: "Can the audit log be exportable too? Our compliance team wants it as a spreadsheet, not a UI."

## Dropped
- Q (proposed): "Would they pay more for access control features?" — not mentioned in transcript; no behavioral evidence.
- Q (proposed): "What does Priya think of the mock-ups so far?" — closing pleasantry with no signal ("Looking forward to seeing the mock-ups"). Future intent only; no past behavior.
