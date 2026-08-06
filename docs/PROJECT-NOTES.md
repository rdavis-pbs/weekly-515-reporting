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

- **Anchor Friday**, with the cutover on **Wednesday**: run Wed–Sun → this week's Friday; run Mon or
  Tue → *last* week's Friday. The reasoning is that early in the week you're still writing up the
  week that just ended, not the one barely underway. Weeks are Monday-start, so on Sat/Sun "this
  week's Friday" is the Friday just passed. The output folder is always named for this anchor Friday.
  (Before v0.9.0 the cutover was Saturday — Mon–Fri all meant "this week.")
- **Most collectors use Mon–Fri** (chat, email, calendar, OneNote, git, Claude).
- **Jira is the exception — it uses a 7-day Friday→Friday window**, ending on the same anchor
  Friday the folder is named for (so folder and Jira window line up). This was a specific request:
  your Jira reporting period is Fri→Fri. Since v0.9.0 the dates are injected into your JQL via
  `{start}`/`{end}` placeholders, so there are no hardcoded dates left to ignore.
- `scripts/jira_fetch.py` reimplements the anchor rule in Python. **If you change the rule, change
  both** — `shared/work-week.md` and `anchor_friday()` in that script — or the Jira window and the
  output folder will drift apart.

## Connector strategy (why some sources use the browser)

This was a deliberate design choice, not a limitation to "fix":

- **Microsoft 365 connector** (Outlook mail, calendar, Teams) — used directly. Already connected.
- **GitHub** — read via the **GitHub REST API** with a personal access token, driven by
  `scripts/github_fetch.py`. Switched from the browser in v0.9.0 alongside Jira. Uses the search API
  so it spans every repo at once without enumerating them: commits, PRs opened, PRs merged, PRs
  reviewed, issues opened/closed. For reviewed PRs it then fetches the actual reviews, because
  `reviewed-by:` matches PRs reviewed at *any* time — only the review objects say when the user
  reviewed and what they said. Optional `GITHUB_USER` (defaults to the token's own account) and
  `GITHUB_HOST` (for Enterprise Server, which uses `/api/v3`).
  - **The failure mode to remember:** a token missing `repo` (classic) / Contents (fine-grained) can
    still authenticate fine and return *zero* results for a week of private-repo work. That's a
    silent wrong answer, not an error, so both the script and the skill call it out explicitly
    whenever counts come back empty.
- **Slack** — uses Slackbot's built-in weekly summary read through the browser (Claude in Chrome),
  NOT the Slack connector. Reason: the Slack connector requires enumerating every chat to access,
  which you didn't want. Slackbot's own recap already covers the workspace.
- **Jira** — read via the **Atlassian Jira Cloud REST API** using a personal API token, driven by
  `scripts/jira_fetch.py` (stdlib only, no pip installs). Switched from the browser in v0.9.0 when
  PBS disabled the Claude-in-Chrome extension. The API path is also strictly better than what the
  browser could do: it pulls each issue's full changelog and comments, filters both to entries whose
  **author is you** inside the window, and so makes the "only report what the user personally did"
  rule mechanical instead of a judgment call. No Atlassian MCP connector is used — a plain script
  needs no per-surface registration and behaves identically in Cowork and Claude Code. (An MCP
  server would only pay off if Jira needed to be queried interactively; the fetch code could be
  lifted into one later.)
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

All person/machine-specific values live in `<workspace>/.weekly-515-reporting/config.md` — **not** in
the plugin folder (see the v0.7.0 note in `CHANGELOG.md`; `shared/config.example.md` is the
template). Skills read them from there by key.

| Variable | Used by | Value / status |
|----------|---------|----------------|
| `SLACK_URL` | `chat-summary` | your Slack workspace/channel URL |
| `JIRA_SITE` | `jira-summary` | your Atlassian host, e.g. `yourorg.atlassian.net` |
| `JIRA_EMAIL` | `jira-summary` | the account email that owns the API token |
| `JIRA_JQL` | `jira-summary` | *optional* — JQL with `{start}`/`{end}` placeholders |
| `GITHUB_USER` | `git-summary` | *optional* — defaults to the token's own account |
| `GITHUB_HOST` | `git-summary` | *optional* — only for GitHub Enterprise Server |
| `ONENOTE_URL` | `onenote-summary` | your SharePoint Doc.aspx notebook URL |
| `AIRTABLE_515_URL` | `weekly-515-rollup` | your 515 base/view URL |
| `OUTPUT_ROOT` | `shared/work-week.md` | *optional* — defaults to the config's own folder |

Secrets live in a sibling file, `<workspace>/.weekly-515-reporting/credentials.md`, holding
`JIRA_API_TOKEN` and `GITHUB_TOKEN`. Splitting them keeps `config.md` safe to share or paste when
debugging.

## Fetch scripts (`scripts/`)

`jira_fetch.py` and `github_fetch.py` are standalone, stdlib-only CLIs. Deliberately **not** MCP
servers: a script needs no per-surface registration and behaves identically in Cowork and Claude
Code. (An MCP server would only pay off if these needed interactive querying; the fetch code could be
lifted into one later.)

Shared logic lives in `scripts/_common.py` — config discovery, `KEY = value` parsing, secret
resolution, the week-anchor rule, and the retrying HTTP client. **`anchor_friday()` there is the only
Python copy of the week rule**; it mirrors the shell snippet in `shared/work-week.md`, and those two
are the pair to keep in sync.

Both scripts follow the same contract, so a third source can copy the pattern:

- Resolve config → resolve token → compute window → fetch → **filter to what the user personally did
  inside the window** → write `<FRIDAY>/<source>-activity.json` → print a human digest to stdout.
- Diagnostics go to stderr, the digest to stdout, so a caller can read either independently.
- `--check` verifies auth and writes nothing. `--start/--end` backfills an older week.
  `--insecure` exists for TLS-inspecting corporate networks.
- Self-imposed limits are reported, never silent: capped review-detail fetches and GitHub's 1000-result
  search ceiling both surface in `notes[]` or on stderr.

**Only ever keep one config.** `jira_fetch.py` searches Cowork mounts → upward from CWD → `$HOME`,
and warns when it finds duplicates. Three stale copies accumulated across the v0.6.0→v0.7.0 config
moves (`shared/config.md`, `~/.weekly-515-reporting/config.md`) and were deleted in v0.9.0; which
one won had depended on the shell's working directory.

## Open items / TODO

- [ ] **Create the Jira API token** and save it as `JIRA_API_TOKEN` in
      `.weekly-515-reporting/credentials.md`, then verify with `jira_fetch.py --check`. Nothing in
      `jira-summary` works until this exists. Token creation is confirmed allowed on the PBS
      Atlassian tenant.
- [ ] **Reinstall the plugin.** The installed copy is v0.5.0 (`local-desktop-app-uploads`), so none
      of the v0.6.0+ config relocation or the v0.9.0 Jira API work is live yet.
- [ ] **Create the GitHub token** and save it as `GITHUB_TOKEN` in `credentials.md`, then verify with
      `github_fetch.py --check`. It needs `repo` scope (classic) or Contents read (fine-grained), or
      private work stays invisible.
- [ ] **Claude in Chrome is disabled by PBS policy.** Jira and GitHub are now solved via their REST
      APIs. Still browser-dependent: `chat-summary` (Slack), `onenote-summary`, and the claude.ai-chat
      portion of `claude-summary`. Slack and OneNote are to be **pasted in manually** by the user.
      claude.ai chat has no API, so that portion of `claude-summary` may simply be dropped — the
      Claude Code half reads local transcripts on disk and is unaffected.
- [ ] First real run end-to-end: sanity-check each output file, then tune the summary sections/tone
      to match how you actually write your 515.
- No auto-run / scheduling — you run this manually. (Decided against a scheduled task.)

## Repo / release workflow

- Source of truth is this git repo, published as a **public GitHub marketplace**:
  `rdavis-pbs/weekly-515-reporting`. Colleagues add that marketplace in the desktop app and install
  from it; with auto-sync on they pick up new versions automatically.
- To cut a release: bump `version` in `.claude-plugin/plugin.json`, update `CHANGELOG.md`, commit,
  tag `vX.Y.Z`, and push. **No zip packaging** — distribution is the GitHub repo itself, so pushing
  is the release. (Earlier notes here described zipping a `.plugin` file; that isn't how this ships.)
- Because distribution is a git push, `.gitignore` is what keeps personal values out of other
  people's installs. Never commit a real `config.md` or `credentials.md`.
- Version history is in `CHANGELOG.md`.

## How to continue this in Claude Code

Open this folder in VS Code. This conversation's context does not carry over, but this file plus
`README.md` and `CHANGELOG.md` should be enough to get oriented. The skills are plain markdown with
YAML frontmatter — edit `SKILL.md` files directly.
