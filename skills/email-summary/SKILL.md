---
name: email-summary
description: >
  Summarize the user's sent and received Outlook email for the current work week (Mon–Fri) and
  save it as email-summary.md in the weekly 515 folder. Use whenever the user wants their weekly
  email activity captured for their 515 report, asks to "summarize my emails this week", "what did
  I send/receive", or runs the weekly 515 workflow. Part of the weekly-515-reporting plugin.
---

# Email summary (Outlook)

Capture what the user drove, committed to, decided, and got blocked by over email this week, as
raw material for the weekly 515 roll-up.

## Step 1 — Establish the week and output folder

Read `${CLAUDE_PLUGIN_ROOT}/shared/work-week.md`; run its snippet for `FRIDAY`, `WEEK_START`,
`WEEK_END`, `LABEL`. Output goes to the `<FRIDAY>` folder.

## Step 2 — Gather received email

Use your Outlook email search with `afterDateTime=WEEK_START` and `beforeDateTime=WEEK_END`. Pull
the most substantive threads (skip newsletters, automated alerts, and calendar noise). Use
`read_resource` on the returned URIs to read bodies when a thread looks decision-bearing.

## Step 3 — Gather sent email

Search again with `folderName="Sent Items"` over the same window to capture what the user
initiated, committed to, or resolved. What the user *sent* is usually the strongest signal of
their own accomplishments and decisions.

## Step 4 — Write the summary

Write to `<FRIDAY>/email-summary.md` using the shared header convention. Organize as:

- **Decisions** — decisions communicated or agreed by email.
- **Progress & accomplishments** — deliverables sent, approvals given, issues resolved, things the
  user drove forward.
- **Commitments made** — things the user promised to do (dates, owners).
- **Blockers & waiting-on** — asks the user is waiting on, escalations, unresolved threads.

Group by project or correspondent, include dates and the other party, and stay factual. If a
category is empty, say so. Do not quote long passages — summarize.
