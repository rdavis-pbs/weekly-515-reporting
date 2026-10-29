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

Every source below is **optional** — nobody has to set up all of them. Different people rely on
different tools, so each collector is skipped automatically (no error, no reported gap) if its
config key isn't set. `run-weekly-515` reports which sources are configured and which are available
but not set up at the start of every run, so you always know what's running and what you could add.

| Skill | Source | How it connects | Output file |
|-------|--------|-----------------|-------------|
| `chat-summary` | Slack *(optional)* | Slack via your saved recap skill, read by manual paste | `chat-summary.md` |
| `email-summary` | Outlook mail *(optional)* | Microsoft 365 connector | `email-summary.md` |
| `calendar-summary` | Outlook calendar *(optional)* | Microsoft 365 connector | `calendar-summary.md` |
| `notes-summary` | Personal notes *(optional, any tool)* | Notepad, OneNote, Word, a notebook, whatever — read by manual paste | `notes-summary.md` |
| `git-summary` | GitHub *(optional)* | **GitHub REST API** via your own token (`scripts/github_fetch.py`) | `git-summary.md` |
| `azure-git-summary` | Azure DevOps (Azure Repos) *(optional)* | **Azure DevOps REST API** via your own PAT (`scripts/azure_devops_fetch.py`) | `azure-git-summary.md` |
| `jira-summary` | Jira *(optional)* | **Atlassian REST API** via your own API token (`scripts/jira_fetch.py`) | `jira-summary.md` |
| `claude-summary` | Claude Code + claude.ai chat + Cowork | Local transcripts on disk; Cowork via desktop app; chat via browser if available | `claude-summary.md` |
| `goals-summary` | Airtable resource tracker (FY goals/tasks) *(optional)* | **Airtable REST API** via your own token (`scripts/airtable_fetch.py --source goals`) | `goals-summary.md` |
| `weekly-515-rollup` | all of the above + your 515 records **(required)** | **Airtable REST API** via your own token (`scripts/airtable_fetch.py`) | `proposed 515 accomplishments.md` |
| `run-weekly-515` | — | orchestrates all of the above | — |

Trigger `run-weekly-515` each Friday to do the whole thing, or run any single skill on its own.
`chat-summary` and `notes-summary` default to a manual-paste stub rather than reading their source
directly, since Claude in Chrome is disabled org-wide at PBS — `run-weekly-515` pauses for those
pastes before rolling up.

If your environment differs further from the stock assumptions above — a step you want to pause
on, a saved Slack recap skill with a different name — record that once in
`docs/WEEKLY-RUN-PLAYBOOK.md` and `run-weekly-515` will read it before every run. See
[docs/WEEKLY-RUN-PLAYBOOK.md](docs/WEEKLY-RUN-PLAYBOOK.md) for the maintainer's own, as an example.

## Before first use — set these

Copy `shared/config.example.md` to `.weekly-515-reporting/config.md` **inside a folder you own and
connect to Cowork** (e.g. your "515 weekly reports" folder), and fill in your own values. Keeping it
in a connected/workspace folder — not the plugin folder — means your real URLs stay off GitHub, the
config survives plugin auto-updates (the installed plugin folder is a cache replaced on each update),
**and** it survives Cowork sessions (the sandbox home directory is wiped each session). Easiest path:
just run any skill and let first-run setup create it for you.

Every key below is **optional** except `AIRTABLE_515_URL` — set only the ones for sources you
actually use; leaving the rest out just skips that collector.

- `SLACK_URL` — *optional, and not even required to use Slack collection* — `chat-summary` always
  writes its paste stub regardless; this just adds a convenience link to the prompt. Tell Claude
  you don't use Slack to actually skip it.
- `JIRA_SITE` — ships **pre-filled** to the org's shared Atlassian host (every colleague here is
  at PBS); you normally don't touch it.
- `JIRA_EMAIL` — **this is what turns Jira collection on**, now that `JIRA_SITE` is always
  present. Set it to your own Atlassian account email to opt in; leave it a placeholder (or delete
  the line) and `jira-summary` is skipped.
- `JIRA_JQL` — on by default (every issue you updated in the window); edit it only if you want a
  different query, using the `{start}`/`{end}` placeholders.
- `NOTES_LOCATION` / `NOTES_URL` — *optional.* Used by `notes-summary`, which is tool-agnostic
  (OneNote, Notepad, Word, a notebook, whatever). Omit both and it just asks you directly each run.
- `AIRTABLE_515_URL` — **required.** Your 515 base/view URL (used by `weekly-515-rollup`) — the one
  source that isn't optional, since there's no 515 format to draft into without it.
- `GITHUB_USER` / `GITHUB_HOST` — *optional.* Defaults to the token's own account on github.com; set
  `GITHUB_HOST` only for GitHub Enterprise Server. `git-summary` itself is skipped if `GITHUB_TOKEN`
  isn't set in `credentials.md`.
- `AZURE_DEVOPS_ORG_URL` — *optional.* Your Azure DevOps organization URL (used by
  `azure-git-summary`). Leave the plugin's whole Azure DevOps setup out if you don't use it — that
  collector is simply skipped.
- `AZURE_DEVOPS_PROJECT` / `AZURE_DEVOPS_EMAIL` — *optional.* Scope the scan to specific projects, or
  override the account email used to match commit authorship.
- `OUTPUT_ROOT` — *optional.* Reports default to the connected folder; set this only to write them elsewhere.

**API tokens** go in `.weekly-515-reporting/credentials.md` (template:
`shared/credentials.example.md`), never in `config.md`:

- `AIRTABLE_API_KEY` — <https://airtable.com/create/tokens> (**required**; scopes
  `data.records:read` + `schema.bases:read` only; **Access** limited to exactly the 515 tracker
  base and, if used, the FY27 Resource Planner base — nothing else; **expiration: "No
  expiration"**, unlike the tokens below, since this one isn't meant to be rotated on a schedule)
- `JIRA_API_TOKEN` — <https://id.atlassian.com/manage-profile/security/api-tokens> (the plain
  **"Create API token"** option, classic/no scopes — **not** "Create API token with scopes"; a
  scoped token is routed through `api.atlassian.com` instead of your site's own URL, which this
  script doesn't call, so it 401s here regardless of scopes granted)
- `GITHUB_TOKEN` — <https://github.com/settings/tokens> (needs `repo` on a classic token, or
  read-only Contents/Pull-requests/Issues/Metadata on a fine-grained one, to see private repos)
- `AZURE_DEVOPS_PAT` — `https://dev.azure.com/{org}/_usersSettings/tokens` (needs **Code (Read)**;
  scoped to one organization)

## Connectors used

- **Microsoft 365** (Outlook mail, calendar) — used directly. Optional in the sense that
  `email-summary`/`calendar-summary` are skipped if the connector isn't authorized. The connector
  shows up in **Cowork** (confirmed working there); **no genuine Claude Code surface has it** —
  not the VS Code/JetBrains extensions, and not the desktop app's own **Code** surface either
  (confirmed by a colleague on v0.13.0, despite it being the same app as Cowork). Running the
  plugin from Code means pasting email/calendar in manually instead (see the Claude Code bullet
  below for why you might still choose that trade-off).
- **Airtable** — the **Airtable REST API** with your own personal access token, via
  `scripts/airtable_fetch.py`. Two sources: your 515 records (`AIRTABLE_515_URL`, **required** —
  the format) and optionally your FY goals/tasks (`AIRTABLE_GOALS_URL`, for Next Week's
  Priorities). Read-only; the Airtable connector and the browser remain as fallbacks for the 515
  read (the browser one unavailable where Claude in Chrome is disabled by policy).
- **Jira** *(optional)* — the **Atlassian REST API** with your own API token, via
  `scripts/jira_fetch.py`. `JIRA_SITE` ships pre-filled to the org's shared host; skipped if
  `JIRA_EMAIL` isn't set to your own account email.
- **GitHub** *(optional)* — the **GitHub REST API** with your own token, via
  `scripts/github_fetch.py`. Skipped if `GITHUB_TOKEN` isn't set.
- **Azure DevOps** *(optional)* — the **Azure DevOps REST API** with your own personal access
  token, via `scripts/azure_devops_fetch.py`. Skipped entirely if `AZURE_DEVOPS_ORG_URL` isn't set.
  All fetch scripts are stdlib-only Python with no dependencies, and need no browser or connector.
- **Slack**, **personal notes** (any tool) — read by **manual paste** by default: `chat-summary`
  and `notes-summary` *always* write an `AWAITING INPUT` stub and the run pauses until you paste,
  since Claude in Chrome is disabled org-wide at PBS — neither is gated by `SLACK_URL` or
  `NOTES_LOCATION`/`NOTES_URL`, which are just optional convenience hints. Both fall back to
  reading their source directly through the browser instead, if that extension is ever available
  again. The only way either is skipped is by telling Claude you don't use Slack, or don't keep
  separate notes — not by leaving a config key unset.
- **claude.ai chat** — read through the browser (Claude in Chrome) when available; marked
  **not-collected** (not "no activity" — a different claim) while the extension is disabled.
- **Cowork** — read from the Claude desktop app (desktop-only; no web URL), by `claude-summary`.
- **Claude Code** — read from local session transcripts under `~/.claude/projects/`; nothing to
  authorize, but **the plugin itself must be running from a genuine Claude Code session** (CLI,
  VS Code/JetBrains extension, or the desktop app's own Code surface) to reach them — running from
  **Cowork** instead resolves `~/.claude/projects/` to Cowork's own sandboxed, ephemeral home
  directory, not your real machine's, so that surface comes back empty and gets marked
  not-collected rather than "no activity." Trade-off, confirmed, not just the IDE extensions: **no**
  Code surface — not VS Code, not JetBrains, not the desktop app's own Code mode — has the
  Microsoft 365 connector, so picking Code over Cowork to get Claude Code history always costs the
  automatic email/calendar read in exchange. There is no single surface with both; see
  `docs/COLLEAGUE-SETUP.md` for the run-twice-and-merge workaround.

`run-weekly-515` reports, at the start of every run, which of the optional sources above are
currently configured and which are available but not set up — so you always know what's included
this week without having to remember your own config.
