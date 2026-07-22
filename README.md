# weekly-515-reporting

A plugin that assembles your weekly **515** report. It gathers a week's worth of work activity
from six sources, drops a summary file for each into a dated folder, then distills everything into a
proposed 515 entry that matches the existing Airtable format.

## The week & folder convention

All skills target one **Mon–Fri** work week, anchored to a Friday:

- Run Mon–Fri → this week. Run Sat/Sun → the week that just ended.
- Output goes to `515 weekly reports/<FRIDAY>/` (e.g. `515 weekly reports/2026-07-17/`).

The shared logic lives in `shared/work-week.md`, which every skill reads first so they always agree
on the folder.

## Skills

| Skill | Source | How it connects | Output file |
|-------|--------|-----------------|-------------|
| `chat-summary` | Slack + Teams | Slack via Slackbot summary (browser); Teams via connector | `chat-summary.md` |
| `email-summary` | Outlook mail | Microsoft 365 connector | `email-summary.md` |
| `calendar-summary` | Outlook calendar | Microsoft 365 connector | `calendar-summary.md` |
| `onenote-summary` | OneNote notes | SharePoint-hosted notebook via browser (Claude in Chrome) | `onenote-summary.md` |
| `git-summary` | GitHub | GitHub connector | `git-summary.md` |
| `jira-summary` | Jira | Saved filter via browser (Claude in Chrome) | `jira-summary.md` |
| `claude-summary` | Claude Code + claude.ai chat + Cowork | Local session transcripts on disk; chat & Cowork via browser | `claude-summary.md` |
| `weekly-515-rollup` | all of the above + Airtable | Airtable read via browser | `proposed 515 accomplishments.md` |
| `run-weekly-515` | — | orchestrates all of the above | — |

Trigger `run-weekly-515` each Friday to do the whole thing, or run any single skill on its own.

## Before first use — set these

Copy `shared/config.example.md` to `~/.weekly-515-reporting/config.md` (a `.weekly-515-reporting`
folder in your home directory) and fill in your own values. This lives outside the plugin folder on
purpose: it keeps your real URLs off GitHub **and** it survives plugin auto-updates (the installed
plugin folder is a cache that gets replaced on each update, so config kept inside it would be lost).

- `JIRA_FILTER_URL` — your Jira saved-filter URL (used by `jira-summary`).
- `ONENOTE_URL` — your SharePoint/OneDrive OneNote notebook URL (used by `onenote-summary`).
- `AIRTABLE_515_URL` — your 515 base/view URL (used by `weekly-515-rollup`).
- `OUTPUT_ROOT` — the folder where dated report subfolders are written.

## Connectors used

- **Microsoft 365** (Outlook mail, calendar, Teams) — used directly.
- **GitHub** — must be authorized for `git-summary`.
- **Slack**, **Jira/Atlassian**, **Airtable**, **claude.ai chat**, **Cowork** — accessed through the
  browser (Claude in Chrome), so no connector auth is required for those.
- **Claude Code** — read from local session transcripts under `~/.claude/projects/`; nothing to
  authorize, but the sessions must live on the machine the plugin runs on.
