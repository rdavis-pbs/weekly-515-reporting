# weekly-515-reporting

A plugin that assembles your weekly **515** report. It gathers a week's worth of work activity from
your chat, mail, calendar, notes, code, tickets, AI sessions, and goals tracker, drops a summary file
for each into a dated folder, then distills everything into a proposed 515 entry that matches the
existing Airtable format.

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
| `chat-summary` | Slack | Slack via Slackbot summary (browser) | `chat-summary.md` |
| `email-summary` | Outlook mail | Microsoft 365 connector | `email-summary.md` |
| `calendar-summary` | Outlook calendar | Microsoft 365 connector | `calendar-summary.md` |
| `onenote-summary` | OneNote notes | SharePoint-hosted notebook via browser (Claude in Chrome) | `onenote-summary.md` |
| `git-summary` | GitHub | **GitHub REST API** via your own token (`scripts/github_fetch.py`) | `git-summary.md` |
| `azure-git-summary` | Azure DevOps (Azure Repos) | **Azure DevOps REST API** via your own PAT (`scripts/azure_devops_fetch.py`) | `azure-git-summary.md` |
| `jira-summary` | Jira | **Atlassian REST API** via your own API token (`scripts/jira_fetch.py`) | `jira-summary.md` |
| `claude-summary` | Claude Code + claude.ai chat + Cowork | Local transcripts on disk; chat via browser; Cowork via desktop app | `claude-summary.md` |
| `goals-summary` | Airtable resource tracker (FY goals/tasks) | **Airtable REST API** via your own token (`scripts/airtable_fetch.py --source goals`) | `goals-summary.md` |
| `weekly-515-rollup` | all of the above + your 515 records | **Airtable REST API** via your own token (`scripts/airtable_fetch.py`) | `proposed 515 accomplishments.md` |
| `run-weekly-515` | — | orchestrates all of the above | — |

Trigger `run-weekly-515` each Friday to do the whole thing, or run any single skill on its own.

If your environment differs from the stock assumptions above — a source you don't use, a browser
that's locked down, a step you want to pause on — record that once in
`docs/WEEKLY-RUN-PLAYBOOK.md` and `run-weekly-515` will read it before every run. See
[docs/WEEKLY-RUN-PLAYBOOK.md](docs/WEEKLY-RUN-PLAYBOOK.md) for the maintainer's own, as an example.

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
- `AZURE_DEVOPS_ORG_URL` — your Azure DevOps organization URL (used by `azure-git-summary`). Leave
  the plugin's whole Azure DevOps setup out if you don't use it — that collector is simply skipped.
- `AZURE_DEVOPS_PROJECT` / `AZURE_DEVOPS_EMAIL` — *optional.* Scope the scan to specific projects, or
  override the account email used to match commit authorship.
- `OUTPUT_ROOT` — *optional.* Reports default to the connected folder; set this only to write them elsewhere.

**API tokens** go in `.weekly-515-reporting/credentials.md` (template:
`shared/credentials.example.md`), never in `config.md`:

- `JIRA_API_TOKEN` — <https://id.atlassian.com/manage-profile/security/api-tokens>
- `GITHUB_TOKEN` — <https://github.com/settings/tokens> (needs `repo` on a classic token, or
  read-only Contents/Pull-requests/Issues/Metadata on a fine-grained one, to see private repos)
- `AZURE_DEVOPS_PAT` — `https://dev.azure.com/{org}/_usersSettings/tokens` (needs **Code (Read)**;
  scoped to one organization)

## Connectors used

- **Microsoft 365** (Outlook mail, calendar) — used directly.
- **Airtable** — the **Airtable REST API** with your own personal access token, via
  `scripts/airtable_fetch.py`. Two sources: your 515 records (`AIRTABLE_515_URL`, for the format) and
  optionally your FY goals/tasks (`AIRTABLE_GOALS_URL`, for Next Week's Priorities). Read-only; the
  Airtable connector and the browser remain as fallbacks for the 515 read.
- **Jira** — the **Atlassian REST API** with your own API token, via `scripts/jira_fetch.py`.
- **GitHub** — the **GitHub REST API** with your own token, via `scripts/github_fetch.py`.
- **Azure DevOps** — the **Azure DevOps REST API** with your own personal access token, via
  `scripts/azure_devops_fetch.py`. Optional: skipped entirely if `AZURE_DEVOPS_ORG_URL` isn't set.
  All fetch scripts are stdlib-only Python with no dependencies, and need no browser or connector.
- **Slack**, **OneNote**, **claude.ai chat** — accessed through the browser (Claude in Chrome), so no
  connector auth is required; just be signed in to each in Chrome. If your organization has disabled
  the extension, these collectors can't run — paste the material in yourself, or skip them; the
  roll-up uses whatever files exist.
- **Cowork** — read from the Claude desktop app (desktop-only; no web URL), by `claude-summary`.
- **Claude Code** — read from local session transcripts under `~/.claude/projects/`; nothing to
  authorize, but the sessions must live on the machine the plugin runs on.
