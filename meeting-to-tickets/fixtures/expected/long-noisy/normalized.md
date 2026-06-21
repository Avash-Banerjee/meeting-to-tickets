---
meeting_slug: long-noisy
participants: [Alice, Priya]
chunks: 1
format_warning: null
---

<!-- chunk 1/1 -->
<!-- t=00:00 -->
Alice: Welcome back, Priya. Two things on the agenda: reporting follow-ups and a question about access control.

<!-- t=00:06 -->
Priya: Reporting first. The CSV export from last week works, but it only includes the current page — not the whole filtered view.

<!-- t=00:15 -->
Alice: Got it. And how often does that come up?
Priya: Every export. I end up downloading three or four pages and stitching them.

<!-- t=00:24 -->
Alice: Have you tried working around it any other way?

<!-- t=00:32 -->
Priya: I tried using the API endpoint directly last Tuesday. It returned everything, but the column order was wrong so finance rejected it.

<!-- t=00:42 -->
Alice: Finance rejected the file because of column order? Walk me through that.

<!-- t=00:51 -->
Priya: They have a macro that expects columns A through M in a specific order. If the header row doesn't match, the macro crashes.

<!-- t=01:02 -->
Alice: So we need the export to honor that column order. Do you have the spec for it?

<!-- t=01:11 -->
Priya: I can get it. I'll forward the template spreadsheet after this call.

<!-- t=01:20 -->
Alice: Perfect. Also — is this just your team or is every region doing the same stitch-and-merge?

<!-- t=01:30 -->
Priya: APAC does it too. I found out last month when I was on a call with their ops lead. She spends every Friday on the same thing.

<!-- t=01:42 -->
Alice: Okay, so this is wider than one team. That changes the priority a bit. Let me note that — multi-region impact, same workaround.

<!-- t=01:52 -->
Priya: Right. And if you're building the full-view export, please make sure it respects the active filters. Last time we got an export it dumped everything regardless of filters.

<!-- t=02:03 -->
Alice: Filter-aware export, correct column order, full view not just current page. Anything else on reporting?

<!-- t=02:13 -->
Priya: One more — scheduled exports would be a huge win. Right now I have a calendar reminder every Monday. If the system could just email the CSV at 8am, I'd save an hour a week.

<!-- t=02:24 -->
Alice: Scheduled delivery to email. Got it. Is a fixed time okay or does it need to be configurable?

<!-- t=02:34 -->
Priya: Configurable would be better. APAC is in a different timezone so they'd want a different slot.

<!-- t=02:44 -->
Alice: Makes sense. Okay, let's shift to access control. You mentioned last week you hit a wall trying to provision a new team member.

<!-- t=02:55 -->
Priya: Yeah. Jess joined two Mondays ago. I went to add her to the reporting group and the button was greyed out. I had to file a ticket with IT.

<!-- t=03:06 -->
Alice: How long did that take?

<!-- t=03:17 -->
Priya: Four days. Jess couldn't see anything for four days. It came up in her onboarding survey — she rated "access to tools" as her lowest score.

<!-- t=03:27 -->
Alice: Four days with no dashboard access during onboarding. And this wasn't a one-off?

<!-- t=03:38 -->
Priya: No, same thing happened with Marcus two months ago. And with the contractor we brought on in February — she left before IT finished the provisioning.

<!-- t=03:50 -->
Alice: So you've seen this three times in six months. What would self-serve provisioning need to look like for you to trust it?

<!-- t=04:01 -->
Priya: I need to be able to add someone to a group myself, see it take effect immediately, and get an audit log I can show compliance.

<!-- t=04:12 -->
Alice: Immediate effect, audit log for compliance. What groups can you currently manage on your own?

<!-- t=04:23 -->
Priya: None. Everything goes through IT. Even removing someone who left the company — I file a ticket and then cross my fingers.

<!-- t=04:34 -->
Alice: That's a real risk. Someone who leaves the company could still have access until the ticket is resolved.

<!-- t=04:45 -->
Priya: Exactly. We had an incident in Q1 where a contractor's account was still active six weeks after they finished. Security flagged it.

<!-- t=04:56 -->
Alice: Okay. So the deprovisioning case is at least as important as the provisioning case, maybe more so from a security angle.

<!-- t=05:07 -->
Priya: Agreed. If I could at least disable an account myself immediately and then let IT clean it up later, that would cover the risk.

<!-- t=05:18 -->
Alice: Disable-immediately with async cleanup. I like that. What's the compliance requirement — do you need the audit log within a certain time window?

<!-- t=05:29 -->
Priya: Our policy says the access change has to be logged within 24 hours. Currently there's no log at all on our end — IT keeps theirs separately.

<!-- t=05:40 -->
Alice: No unified log. So right now if compliance asks, you'd have to request IT's logs?

<!-- t=05:51 -->
Priya: Yes, and that took three days last time. We almost missed a compliance window.

<!-- t=06:02 -->
Alice: Good to know. Let me summarize what I've heard: full-view filter-aware export, correct column order, scheduled email delivery with configurable time zones, self-serve provisioning and deprovisioning with immediate effect, and a unified audit log.

<!-- t=06:12 -->
Priya: That's it. Oh — one last thing. Can the audit log be exportable too? Our compliance team wants it as a spreadsheet, not a UI.

<!-- t=06:22 -->
Alice: Audit log exportable as a spreadsheet. Noted. Thanks Priya, this was really helpful.

<!-- t=06:30 -->
Priya: Thanks Alice. Looking forward to seeing the mock-ups.
