# weekly-515-reporting

A plugin that assembles your weekly **515** report. It gathers a week's worth of work activity
from six sources, drops a summary file for each into a dated folder, then distills everything into a
proposed 515 entry that matches the existing Airtable format.

> **New here?** See [docs/COLLEAGUE-SETUP.md](docs/COLLEAGUE-SETUP.md) for step-by-step install and setup.

## The week & folder convention

All skills target one **Mon–Fri** work week, anchored to a Friday, with the cutover on **Wednesday**:

- Run **Wed–Sun** → this week (on Sat/Sun that's the Friday just passed).
- Run **Mon or Tue** → last week — early in the week you're still reporting on the week that ended.
- Output goes to `515 weekly reports/<FRIDAY>/` (e.g. `515 weekly reports/2026-07-17/`).

`jira-summary` is the one exception: it reports a 7-day **Friday→Friday** span ending on that same
anchor Friday, so its window still lines up with the folder.

The shared logic lives in `shared/work-week.md`, which every skill reads first so they always agree
on the folder.

## Skills

| Skill | Source | How it connects | Output file |
|-------|--------|-----------------|-------------|
| `chat-summary` | Slack + Teams | Slack via Slackbot summary (browser); Teams via connector | `chat-summary.md` |
| `email-summary` | Outlook mail | Microsoft 365 connector | `email-summary.md` |
| `calendar-summary` | Outlook calendar | Microsoft 365 connector | `calendar-summary.md` |
| `onenote-summary` | OneNote notes | SharePoint-hosted notebook via browser (Claude in Chrome) | `onenote-summary.md` |
| `git-summary` | GitHub | **GitHub REST API** via your own token (`scripts/github_fetch.py`) | `git-summary.md` |
| `jira-summary` | Jira | **Atlassian REST API** via your own API token (`scripts/jira_fetch.py`) | `jira-summary.md` |
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
- `JIRA_SITE` / `JIRA_EMAIL` — your Atlassian host and account email (used by `jira-summary`).
- `JIRA_JQL` — *optional.* Custom JQL with `{start}`/`{end}` placeholders; defaults to "issues you
  updated in the window."
- `ONENOTE_URL` — your SharePoint/OneDrive OneNote notebook URL (used by `onenote-summary`).
- `AIRTABLE_515_URL` — your 515 base/view URL (used by `weekly-515-rollup`).
- `GITHUB_USER` / `GITHUB_HOST` — *optional.* Defaults to the token's own account on github.com; set
  `GITHUB_HOST` only for GitHub Enterprise Server.
- `OUTPUT_ROOT` — *optional.* Reports default to the connected folder; set this only to write them elsewhere.

**API tokens** go in `.weekly-515-reporting/credentials.md` (template:
`shared/credentials.example.md`), never in `config.md`:

- `JIRA_API_TOKEN` — <https://id.atlassian.com/manage-profile/security/api-tokens>
- `GITHUB_TOKEN` — <https://github.com/settings/tokens> (needs `repo` on a classic token, or
  read-only Contents/Pull-requests/Issues/Metadata on a fine-grained one, to see private repos)

## Connectors used

- **Microsoft 365** (Outlook mail, calendar, Teams) — used directly.
- **Airtable** — used directly by `weekly-515-rollup` via the Airtable connector.
- **Jira** — the **Atlassian REST API** with your own API token, via `scripts/jira_fetch.py`.
- **GitHub** — the **GitHub REST API** with your own token, via `scripts/github_fetch.py`.
  Both fetch scripts are stdlib-only Python with no dependencies, and need no browser or connector.
- **Slack**, **OneNote**, **claude.ai chat** — accessed through the browser (Claude in Chrome), so no
  connector auth is required; just be signed in to each in Chrome. If your organization has disabled
  the extension, these collectors can't run — paste the material in yourself, or skip them; the
  roll-up uses whatever files exist.
- **Cowork** — read from the Claude desktop app (desktop-only; no web URL), by `claude-summary`.
- **Claude Code** — read from local session transcripts under `~/.claude/projects/`; nothing to
  authorize, but the sessions must live on the machine the plugin runs on.
