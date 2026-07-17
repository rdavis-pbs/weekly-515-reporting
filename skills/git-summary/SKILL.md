---
name: git-summary
description: >
  Summarize the user's GitHub activity — commits, pull requests, reviews, and issues — for the
  current work week (Mon–Fri) and save it as git-summary.md in the weekly 515 folder, using the
  GitHub connector. Use whenever the user wants their weekly code/repo activity captured for their
  515 report, asks "what did I ship this week", "summarize my commits/PRs", or runs the weekly 515
  workflow. Part of the weekly-515-reporting plugin.
---

# Git summary (GitHub)

Capture the engineering work the user personally moved this week — shipped code, PRs opened and
merged, reviews given, issues closed — as raw material for the weekly 515 roll-up.

> **Requires the GitHub connector to be authorized.** If GitHub tools aren't available, write
> `git-summary.md` noting that GitHub wasn't connected this run, and stop — don't fail the whole
> workflow.

## Step 1 — Establish the week and output folder

Read `${CLAUDE_PLUGIN_ROOT}/shared/work-week.md`; run its snippet for `FRIDAY`, `WEEK_START`,
`WEEK_END`, `LABEL`. Output goes to the `<FRIDAY>` folder.

## Step 2 — Identify the user and gather activity

Determine the user's GitHub login (the authenticated user). Then, scoped to `WEEK_START`–
`WEEK_END`, gather with your GitHub tools:

- **Commits** authored by the user (search commits with `author:<login>` and a date range, or list
  commits per active repo).
- **Pull requests** the user **opened**, **merged**, or had merged in this window.
- **Reviews** the user submitted on others' PRs.
- **Issues** the user opened or closed.

Prefer GitHub search with author/date qualifiers so you cover activity across repos rather than one
repo at a time. Capture repo name, title, PR/issue number, and merge/close status.

## Step 3 — Write the summary

Write to `<FRIDAY>/git-summary.md` using the shared header convention. Organize as:

- **Shipped / merged** — PRs merged and notable commits, grouped by repo, with a one-line "what &
  why" each (not raw commit messages).
- **In progress** — PRs opened but not yet merged, WIP branches.
- **Reviews & collaboration** — PRs the user reviewed, meaningful issue triage.
- **Issues closed** — bugs/tasks resolved.

Translate commit noise into outcomes a manager would care about (a feature delivered, a bug fixed,
a migration done) rather than listing every commit. Include repo names and PR numbers so the
roll-up can cite specifics. If there was no activity, say so.
