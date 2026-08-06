---
name: run-weekly-515
description: >
  Run the full weekly 515 workflow end to end: collect chat, email, calendar, OneNote, git, Jira,
  and Claude (Code + chat + Cowork) activity for the current work week, then roll it all up into a
  proposed 515 entry. This is
  the one-click Friday driver for the weekly-515-reporting plugin. Use whenever the user says "run
  my weekly 515", "do my 515", "prep my weekly report", "it's Friday, do my 515", or wants the
  whole weekly report workflow done at once.
---

# Run weekly 515 (orchestrator)

This is the single entry point the user triggers each Friday. It runs the collector skills, then the
roll-up, all against the same work week and output folder.

## Step 1 — Establish the week and output folder once

Read `${CLAUDE_PLUGIN_ROOT}/shared/work-week.md` and run its snippet to get `FRIDAY`, `LABEL`, and
the window. Announce to the user which week you're reporting on and where files will be saved, so
there's no ambiguity if it's run near a weekend.

## Step 2 — Run each collector

Carry out each of these skills in turn, following that skill's own SKILL.md. They're independent,
so a failure or missing connector in one should not stop the others — capture what each produces
and move on:

1. `chat-summary`  (Slack via Slackbot summary + Teams)
2. `email-summary`  (Outlook sent + received)
3. `calendar-summary`  (Outlook events)
4. `onenote-summary`  (local/OneDrive notes export)
5. `git-summary`  (GitHub via the REST API — no browser)
6. `jira-summary`  (Jira via the Atlassian REST API — no browser)
7. `claude-summary`  (Claude Code local sessions + claude.ai chat via browser + Cowork via desktop app)

Each writes one file into the `<FRIDAY>` folder. Keep a running note of which succeeded and which
were skipped (source empty, connector not authorized, or config like a filter/notes path not set).

## Step 3 — Roll up

Run the `weekly-515-rollup` skill. It reads the recent Airtable 515 records and every summary file
in the `<FRIDAY>` folder, then writes `proposed 515 accomplishments.md`.

## Step 4 — Report

Give the user a short status: which sources were collected, which were skipped and why, a 2–3
sentence highlight of the week, and anything to verify. Present `proposed 515 accomplishments.md`
so they can open it. Mention they can re-run any single collector skill on its own if a source was
missing (e.g. authorize GitHub, then run `git-summary`, then `weekly-515-rollup` again).
