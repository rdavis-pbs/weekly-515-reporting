---
name: calendar-summary
description: >
  Review and summarize the activities described in the user's Outlook calendar events for the
  current work week (Mon–Fri) and save it as calendar-summary.md in the weekly 515 folder. Use
  whenever the user wants their weekly meetings/calendar captured for their 515 report, asks "what
  meetings did I have this week", or runs the weekly 515 workflow. Part of the weekly-515-reporting
  plugin.
---

# Calendar summary (Outlook)

Turn this week's meetings into a record of what the user participated in, drove, and decided — raw
material for the weekly 515 roll-up. Focus on the *substance* of meetings, not just their titles.

## Step 1 — Establish the week and output folder

Read `${CLAUDE_PLUGIN_ROOT}/shared/work-week.md`; run its snippet for `FRIDAY`, `WEEK_START`,
`WEEK_END`, `LABEL`. Output goes to the `<FRIDAY>` folder.

## Step 2 — Gather events

Use your Outlook calendar search with `afterDateTime=WEEK_START`, `beforeDateTime=WEEK_END`, and
`order="oldest"` to walk the week in order. For each meaningful event, use `read_resource` on its
URI to pull the body, agenda, attendees, and — where present — the meeting transcript
(`meetingTranscriptUrl`) for what was actually discussed and decided.

Skip pure focus-time blocks, declined events, and personal holds unless they clearly represent work
(e.g. a heads-down block tied to a deliverable).

## Step 3 — Write the summary

Write to `<FRIDAY>/calendar-summary.md` using the shared header convention. Organize as:

- **Key meetings** — for each: date, title, who was there (roles/teams, not a full roster), the
  purpose, and the outcome or decisions.
- **Decisions made** — pulled out explicitly so the roll-up can find them.
- **Follow-ups & action items** — commitments that came out of meetings, with owners if known.
- **Recurring cadence** — a one-line note on standing meetings (1:1s, standups) rather than a row
  each.

Distinguish meetings the user **organized/led** from ones they merely attended — leading is a
stronger 515 signal. Stay factual; if a transcript or body wasn't available, summarize from the
subject and attendees and note the limitation.
