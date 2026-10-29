---
name: run-weekly-515
description: >
  Run the full weekly 515 workflow end to end: collect Slack chat, email, calendar, personal notes,
  GitHub and Azure DevOps git activity, Jira, Claude (Code + chat + Cowork), and Airtable
  resource-tracker goals for the current work week, then roll it all up into a proposed 515 entry.
  Every source is optional — surfaces which ones are configured and which are available but not set
  up before running anything, since different people rely on different tools. This is the one-click
  Friday driver for the weekly-515-reporting plugin. Use whenever the user says "run my weekly 515",
  "do my 515", "prep my weekly report", "it's Friday, do my 515", or wants the whole weekly report
  workflow done at once.
---

# Run weekly 515 (orchestrator)

This is the single entry point the user triggers each Friday. It runs the collector skills, then the
roll-up, all against the same work week and output folder.

> **Check for a local playbook first.** If `${CLAUDE_PLUGIN_ROOT}/docs/WEEKLY-RUN-PLAYBOOK.md`
> exists, read it before doing anything else and follow it where it differs from the steps below.
> It records any standing personal preferences in this environment (a named saved skill to run, a
> source the user deliberately doesn't use, a machine quirk) — details this generic orchestrator
> can't know.

## Step 1 — Establish the week and output folder once

Read `${CLAUDE_PLUGIN_ROOT}/shared/work-week.md` and run its snippet to get `FRIDAY`, `LABEL`, and
the window. Announce to the user which week you're reporting on and where files will be saved, so
there's no ambiguity if it's run near a weekend.

## Step 2 — Report which sources are configured

**Every source below is optional** — nobody has to set up all of them, and which ones apply
depends entirely on the tools the user actually uses. Before running anything, follow the **Source
availability** section of `${CLAUDE_PLUGIN_ROOT}/shared/work-week.md` to check which collectors
have what they need, and tell the user up front, as two short lists: what's configured and will
run this week, and what's available but not set up (with a one-line note on what key would enable
it). This also doubles as a quick way to show the user their current setup any time they ask "what
sources do I have configured."

## Step 3 — Run each configured collector

Carry out each of these skills in turn, following that skill's own SKILL.md — but **only the ones
Step 2 found configured** (or that need no config at all). Skip the rest outright rather than
invoking them and letting them fail; that skip is already reflected in Step 2's report, so don't
re-report it as a gap here. They're independent, so a failure in one should not stop the others —
capture what each produces and move on:

1. `chat-summary`  (Slack via Slackbot summary, read by manual paste — Teams is not a source)
2. `email-summary`  (Outlook sent + received, via the Microsoft 365 connector)
3. `calendar-summary`  (Outlook events, via the Microsoft 365 connector)
4. `notes-summary`  (personal notes, any tool, read by manual paste)
5. `git-summary`  (GitHub via the REST API — no browser)
6. `azure-git-summary`  (Azure DevOps Git via the REST API — no browser)
7. `jira-summary`  (Jira via the Atlassian REST API — no browser)
8. `claude-summary`  (Claude Code local sessions — only reachable if *this* run is itself a genuine Claude Code session, not Cowork — + Cowork via desktop app; claude.ai chat marked not-collected unless browser tools are available)
9. `goals-summary`  (Airtable resource tracker via the REST API — committed/upcoming work)

Each writes one file into the `<FRIDAY>` folder. Keep a running note of which succeeded, which were
skipped as not configured, and which ran but found nothing.

## Step 4 — Checkpoint before the roll-up

`chat-summary` and `notes-summary` default to a manual-paste stub (`Status: AWAITING INPUT`) while
Claude in Chrome is disabled org-wide at PBS. **Do not run `weekly-515-rollup` in the same turn**
if either stub is still unfilled — report what's collected so far, list exactly what needs the
user (which stub(s), and anything else that failed), and stop. Resume with the roll-up in a later
turn once the user confirms the stubs are filled.

## Step 5 — Roll up

Run the `weekly-515-rollup` skill. It reads two Airtable sources via the REST API (no browser) — the
recent 515 records and table schema for the format, and the user's committed FY goals/tasks for Next
Week's Priorities — plus every summary file in the `<FRIDAY>` folder, then writes
`proposed 515 accomplishments.md`.

## Step 6 — Report

Give the user a short status: which sources were collected, which were skipped because they're not
configured, a 2–3 sentence highlight of the week, and anything to verify. Present
`proposed 515 accomplishments.md` so they can open it. Mention they can add a source later by
setting its key in `config.md`/`credentials.md` and re-running that single collector, then
`weekly-515-rollup` again.
