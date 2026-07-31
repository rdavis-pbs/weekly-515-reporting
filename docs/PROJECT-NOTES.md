# Project notes — weekly-515-reporting

Context and rationale for this plugin that isn't obvious from the code. Written for a future
session (or a future you) picking this up in VS Code / Claude Code, where the original build
conversation isn't available.

## What this plugin does

Assembles your weekly **515** report. Seven collector skills each summarize one source of work
activity for the week and drop a markdown file into a dated folder; a roll-up skill then distills
all of them into a proposed 515 entry that matches the existing Airtable format. `run-weekly-515`
runs the whole chain.

- Output folder: `515 weekly reports/<FRIDAY>/` (e.g. `.../2026-07-17/`), one file per collector,
  plus `proposed 515 accomplishments.md` from the roll-up.
- The roll-up drafts to a **local file only** — it never writes to Airtable. You review and
  paste it in yourself.

## Week logic (important, and deliberately not uniform)

Shared logic lives in `shared/work-week.md`; every skill reads it first so they agree on the
folder name.

- **Anchor Friday**: if run Mon–Fri, it's this week's Friday; if run Sat/Sun, the Friday of the
  week that just ended. The output folder is always named for this anchor Friday.
- **Most collectors use Mon–Fri** (chat, email, calendar, OneNote, git, Claude).
- **Jira is the exception — it uses a 7-day Friday→Friday window**, ending on the same anchor
  Friday the folder is named for (so folder and Jira window line up). This was a specific request:
  your Jira reporting period is Fri→Fri, and your saved filter has hardcoded dates that the
  skill deliberately **ignores** in favor of the computed window.

## Connector strategy (why some sources use the browser)

This was a deliberate design choice, not a limitation to "fix":

- **Microsoft 365 connector** (Outlook mail, calendar, Teams) — used directly. Already connected.
- **GitHub** — read through the **browser** (Claude in Chrome) by `git-summary`, using GitHub's
  search UI scoped to the user + week. No GitHub MCP connector is available in this environment, so
  the browser is the path; if GitHub isn't reachable, `git-summary` notes that and doesn't block the
  others. (Optional `GITHUB_USER` config key; otherwise the login is read from the signed-in session.)
- **Slack** — uses Slackbot's built-in weekly summary read through the browser (Claude in Chrome),
  NOT the Slack connector. Reason: the Slack connector requires enumerating every chat to access,
  which you didn't want. Slackbot's own recap already covers the workspace.
- **Jira** — read through the browser via your saved filter. No Atlassian connector needed.
- **Airtable** — read via the **Airtable connector** (roll-up reads the last few 515 records to learn
  the format). Falls back to the browser (`AIRTABLE_515_URL`) if the connector isn't available.
- **Claude** (`claude-summary`) — three surfaces, mixed access:
  - **Claude Code** is read from **local session transcripts** on disk (`~/.claude/projects/*/*.jsonl`),
    filtered to the Mon–Fri window by each turn's ISO `timestamp` and grouped by the session's `cwd`.
    No connector or browser — but the sessions must live on the machine the plugin runs on.
  - **claude.ai chat** is read through the browser. **Cowork** is read from the **desktop app**
    (its task list / on-disk history) — Cowork is desktop-only and has no browsable web URL.

Browser sources just need you signed in to those sites in Chrome with the Claude in Chrome
extension connected.

## Config values to set (per skill)

All person/machine-specific values live in `shared/config.md` (git-ignored — copy
`shared/config.example.md` to create it). Skills read them from there by key.

| Variable | Used by | Value / status |
|----------|---------|----------------|
| `JIRA_FILTER_URL` | `jira-summary` | your Jira saved-filter URL |
| `ONENOTE_URL` | `onenote-summary` | your SharePoint Doc.aspx notebook URL |
| `AIRTABLE_515_URL` | `weekly-515-rollup` | your 515 base/view URL |
| `OUTPUT_ROOT` | `shared/work-week.md` | root folder for dated report subfolders |

## Open items / TODO

- [ ] Set `AIRTABLE_515_URL` in `shared/config.md`.
- [ ] Be signed in to GitHub in Chrome so `git-summary` can read it via the browser (no GitHub
      connector is used; the skill degrades gracefully if GitHub isn't reachable). Optionally set
      `GITHUB_USER` in config.
- [ ] First real run: trigger `run-weekly-515` on a Friday and sanity-check each output file, then
      tune the summary sections/tone to match how you actually write your 515.
- No auto-run / scheduling — you run this manually. (Decided against a scheduled task.)

## Repo / release workflow

- Source of truth is this git repo. `.gitignore` excludes packaged `*.plugin` zips.
- To cut a release: bump `version` in `.claude-plugin/plugin.json`, update `CHANGELOG.md`, commit,
  tag `vX.Y.Z`. Package by zipping the plugin dir contents into `weekly-515-reporting.plugin`
  (a plain zip; exclude `.git`, `.DS_Store`), then install/re-install that file in Cowork.
- Version history so far is in `CHANGELOG.md` (current: 0.3.0).

## How to continue this in Claude Code

Open this folder in VS Code. This conversation's context does not carry over, but this file plus
`README.md` and `CHANGELOG.md` should be enough to get oriented. The skills are plain markdown with
YAML frontmatter — edit `SKILL.md` files directly.
