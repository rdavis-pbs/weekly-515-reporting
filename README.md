# weekly-515-reporting

A plugin that assembles your weekly **515** report. It gathers a week's worth of work activity
from six sources, drops a summary file for each into a dated folder, then distills everything into a
proposed 515 entry that matches the existing Airtable format.

> **New here?** See [docs/COLLEAGUE-SETUP.md](docs/COLLEAGUE-SETUP.md) for step-by-step install and setup.

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
| `git-summary` | GitHub | Browser (Claude in Chrome) — GitHub search UI | `git-summary.md` |
| `jira-summary` | Jira | Saved filter via browser (Claude in Chrome) | `jira-summary.md` |
| `claude-summary` | Claude Code + claude.ai chat + Cowork | Local transcripts on disk; chat via browser; Cowork via desktop app | `claude-summary.md` |
| `weekly-515-rollup` | all of the above + Airtable | Airtable connector | `proposed 515 accomplishments.md` |
| `run-weekly-515` | — | orchestrates all of the above | — |

Trigger `run-weekly-515` each Friday to do the whole thing, or run any single skill on its own.

## Before first use — set these

Copy `shared/config.example.md` to `.weekly-515-reporting/config.md` **inside a folder you own and
connect to Cowork** (e.g. your "515 weekly reports" folder), and fill in your own values. Keeping it
in a connected/workspace folder — not the plugin folder — means your real URLs stay off GitHub, the
config survives plugin auto-updates (the installed plugin folder is a cache replaced on each update),
**and** it survives Cowork sessions (the sandbox home directory is wiped each session). Easiest path:
just run any skill and let first-run setup create it for you.

- `SLACK_URL` — your Slack workspace/channel URL (used by `chat-summary`).
- `JIRA_FILTER_URL` — your Jira saved-filter URL (used by `jira-summary`).
- `ONENOTE_URL` — your SharePoint/OneDrive OneNote notebook URL (used by `onenote-summary`).
- `AIRTABLE_515_URL` — your 515 base/view URL (used by `weekly-515-rollup`).
- `OUTPUT_ROOT` — *optional.* Reports default to the connected folder; set this only to write them elsewhere.

## Connectors used

- **Microsoft 365** (Outlook mail, calendar, Teams) — used directly.
- **Airtable** — used directly by `weekly-515-rollup` via the Airtable connector.
- **Slack**, **Jira/Atlassian**, **OneNote**, **GitHub**, **claude.ai chat** — accessed through the
  browser (Claude in Chrome), so no connector auth is required; just be signed in to each in Chrome.
- **Cowork** — read from the Claude desktop app (desktop-only; no web URL), by `claude-summary`.
- **Claude Code** — read from local session transcripts under `~/.claude/projects/`; nothing to
  authorize, but the sessions must live on the machine the plugin runs on.
