# Project notes — weekly-515-reporting

Context and rationale for this plugin that isn't obvious from the code. Written for a future
session (or a future you) picking this up in VS Code / Claude Code, where the original build
conversation isn't available.

## What this plugin does

Assembles your weekly **515** report. Nine collector skills each summarize one source for the week
and drop a markdown file into a dated folder; a roll-up skill then distills all of them into a
proposed 515 entry that matches the existing Airtable format. `run-weekly-515` runs the whole chain.
`azure-git-summary` is optional — skipped entirely if `AZURE_DEVOPS_ORG_URL` isn't set, for users
who only use GitHub.

Eight collectors look **backward** (what happened). `goals-summary` is the one that looks
**forward** — the Airtable resource tracker holds committed activities mapped to department goals,
which is what Next Week's Priorities needs and what no amount of reading this week's chatter can
reliably produce.

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
- **Most collectors use Mon–Fri** (chat, email, calendar, personal notes, git, Claude).
- **Jira is the exception — it uses a 7-day Friday→Friday window**, ending on the same anchor
  Friday the folder is named for (so folder and Jira window line up). This was a specific request:
  your Jira reporting period is Fri→Fri. Since v0.9.0 the dates are injected into your JQL via
  `{start}`/`{end}` placeholders, so there are no hardcoded dates left to ignore.
- `scripts/jira_fetch.py` reimplements the anchor rule in Python. **If you change the rule, change
  both** — `shared/work-week.md` and `anchor_friday()` in that script — or the Jira window and the
  output folder will drift apart.

## Connector strategy (why some sources use the browser)

This was a deliberate design choice, not a limitation to "fix". **Every collector is optional, not
just Azure DevOps** — different people rely on different tools, and a missing config key just
skips that source rather than erroring or reporting a gap. `shared/work-week.md` (§2c, "Source
availability") defines the check once, and `run-weekly-515` runs it before every full run,
reporting two lists to the user: what's configured, and what's available but not set up. This
replaced an earlier design where Azure DevOps was the only source treated as optional and
everything else was implicitly assumed to apply to everyone — which stopped being true the moment
a second colleague with a different toolset started using the plugin.

- **Microsoft 365 connector** (Outlook mail, calendar) — used directly. Already connected.
- **Microsoft Teams — removed as a source in v0.10.1.** You don't use it. It had been costing every
  run a Graph `chat_message_search` sweep that then got written up as a coverage gap: 38 of 40 chats
  on 8/7/2026, then 0 of 38 on 8/14 (HTTP 429). A gap that reads as "chat we failed to capture" when
  there was never any chat there is worse than no section at all.
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
- **Azure DevOps (Azure Repos) — added as a GitHub counterpart, optional.** Read via the **Azure
  DevOps REST API** with a personal access token (Code: Read), driven by
  `scripts/azure_devops_fetch.py`, same contract as the GitHub/Jira scripts. Skipped entirely if
  `AZURE_DEVOPS_ORG_URL` isn't set, since not everyone uses it. Enumerates every project (or just
  `AZURE_DEVOPS_PROJECT`, if set) and every repo in each: commits authored, PRs created, PRs
  completed, PRs reviewed.
  - **No per-vote timestamp exists in the API.** Unlike GitHub's PR reviews, an Azure DevOps
    reviewer's vote has no timestamp of its own — the vote is just a field on the PR's current
    state. The script approximates "reviewed in this window" from the user's own thread comments
    when any exist, and falls back to the PR's created/closed dates (flagged
    `vote_date_is_approximate`) when there's no comment to pin it to. This is a real API gap, not a
    bug to "fix" by polling harder.
  - **A PAT is scoped to one organization.** If work spans multiple Azure DevOps orgs, only the one
    in `AZURE_DEVOPS_ORG_URL` is covered — same shape of limitation as GitHub Enterprise Server's
    `GITHUB_HOST` being one host at a time.
  - **Commit-author matching needs an email**, normally read from the Azure DevOps profile API
    (`vssps.dev.azure.com/{org}/_apis/profile/profiles/me`) — which only exists on Azure DevOps
    Services (cloud), not reliably on an on-prem Server. `AZURE_DEVOPS_EMAIL` is the escape hatch,
    same idea as `JIRA_EMAIL`.
- **Slack** (optional) — uses Slackbot's built-in weekly summary, NOT the Slack connector. Reason:
  the Slack connector requires enumerating every chat to access, which you didn't want. Slackbot's
  own recap already covers the workspace. **Read by manual paste by default** since v0.13.0: write
  an `AWAITING INPUT` stub and stop until the user pastes the recap, rather than opening it through
  the browser — Claude in Chrome is disabled org-wide at PBS, so that path is dormant, not primary.
  Falls back to a direct browser read if the extension is ever available.
- **Jira** — read via the **Atlassian Jira Cloud REST API** using a personal API token, driven by
  `scripts/jira_fetch.py` (stdlib only, no pip installs). Switched from the browser in v0.9.0 when
  PBS disabled the Claude-in-Chrome extension. The API path is also strictly better than what the
  browser could do: it pulls each issue's full changelog and comments, filters both to entries whose
  **author is you** inside the window, and so makes the "only report what the user personally did"
  rule mechanical instead of a judgment call. No Atlassian MCP connector is used — a plain script
  needs no per-surface registration and behaves identically in Cowork and Claude Code. (An MCP
  server would only pay off if Jira needed to be queried interactively; the fetch code could be
  lifted into one later.)
  - **Requires a classic API token, not a scoped one.** `Jira.__init__` in `jira_fetch.py`
    authenticates with Basic Auth directly against `https://{JIRA_SITE}/...`. Atlassian's newer
    "API token with scopes" tokens are routed through `api.atlassian.com/ex/jira/{cloudId}/...`
    instead — a different host this script never calls — so a scoped token 401s here regardless
    of which scopes were granted; it isn't a permissions gap, it's the wrong token type. Supporting
    scoped tokens would mean resolving the cloud ID and switching the base URL, which hasn't been
    done since classic tokens already cover the need (read-only, same-as-your-own-access). Documented
    everywhere a Jira token is created: `COLLEAGUE-SETUP.md`, `shared/credentials.example.md`,
    `README.md`, `jira-summary/SKILL.md`, and the script's own error message.
- **Airtable goals/tasks** (`AIRTABLE_GOALS_URL`, optional) — the user's own view of the **Tasks**
  tab of the FY resource-planner base (e.g. "FY27 Resource Planner"; it also has **Goals** and
  **Metrics** tabs, which aren't fetched directly — each task links to one of each, and the script's
  existing generic link-field resolution turns those into display names since all three tabs live in
  the same base). Read into `<FRIDAY>/airtable-goals.json`, used for Next Week's Priorities.
  **Selection is by due date and completion, deliberately never by status.** In the real table most
  near-term rows have a blank `Status` while nearly every row that carries one is already overdue, so
  the obvious `Status in (To Do, In Progress)` filter returns zero rows and reads as "no upcoming
  work" — a silent wrong answer rather than an error. Everything not Done/Delivered/Cancelled counts
  as committed; the script's job is ordering (overdue / due_next_7d / due_within_30d / later /
  undated, relative to the anchor Friday), not filtering. Note the bucket names are relative to the
  END of the reporting week, so `due_next_7d` is the week after the report — that's the Next Week's
  Priorities window.
  - **`Owners` is a multi-person link field, not a single assignee.** Co-ownership with colleagues is
    normal in this table, unlike the 515 table's single-owner field. The "multiple people in the
    sample" check that flags an unfiltered 515 view would false-positive here on every run, so it's
    gated on the assignee field's type: a `multipleRecordLinks` assignee gets an informational note,
    not the "this view is probably not filtered to you" warning.
  - **`Record Type`** (`Task`/`Note`/`Gate`/`Decision`) didn't exist in the old FY26 table. A `Note`
    isn't committed work; a `Gate` is a milestone with its own due date. The skill is told to handle
    both distinctly rather than reporting every row as an undifferentiated task.
- **Airtable** (required — the one source that isn't optional) — read via the **Airtable REST
  API** (`scripts/airtable_fetch.py`, `AIRTABLE_API_KEY`), same stdlib-script pattern as Jira and
  GitHub. The roll-up reads the last few 515 records to learn the format *and* the table schema,
  which is the part the connector path never gave us: field types and the valid select options, so
  a drafted `#N Goals` uses values that actually exist. Records are sorted by the week-ending date
  field rather than creation time, so a backfilled record can't become the format sample. The
  **connector** and then the **browser** (`AIRTABLE_515_URL`) remain as fallbacks, in that order —
  kept for colleagues whose setup differs, though on this machine neither runs (the browser one
  for the same Chrome-disabled reason as Slack above), which is what motivated the API move.
- **Claude** (`claude-summary`) — three surfaces, mixed access:
  - **Claude Code** is read from **local session transcripts** on disk (`~/.claude/projects/*/*.jsonl`),
    filtered to the Mon–Fri window by each turn's ISO `timestamp` and grouped by the session's `cwd`.
    No connector or browser — but the sessions must live on the machine the plugin runs on, **and
    the plugin itself must be running as a genuine Claude Code session** (CLI, VS Code/JetBrains
    extension, or the desktop app's own Code surface) to reach them. Running from **Cowork**
    instead resolves `~/.claude/projects/` to Cowork's own sandboxed, ephemeral home directory, not
    the real one — same root cause as `config.md`/`credentials.md` needing a connected folder
    instead of `~`. This surface then comes back not-collected, not "no activity."
  - **claude.ai chat** is read through the browser, when available. Disabled org-wide at PBS, so
    this surface is normally marked **not-collected** — distinct from "no activity," since one is a
    missing read and the other is a finding.
  - **Cowork** is read from the **desktop app** (its task list / on-disk history) — Cowork is
    desktop-only and has no browsable web URL.

Browser-fallback sources just need you signed in to those sites in Chrome with the Claude in Chrome
extension connected and enabled — which it currently isn't, org-wide, at PBS.

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
| `AZURE_DEVOPS_ORG_URL` | `azure-git-summary` | *optional* — unset skips the collector entirely |
| `AZURE_DEVOPS_PROJECT` | `azure-git-summary` | *optional* — comma-separated project names to scope to |
| `AZURE_DEVOPS_EMAIL` | `azure-git-summary` | *optional* — only if profile email resolution fails |
| `NOTES_LOCATION` | `notes-summary` | *optional* — free text naming where you keep notes |
| `NOTES_URL` | `notes-summary` | *optional* — only if notes live at a browser-openable URL |
| `AIRTABLE_515_URL` | `weekly-515-rollup` | your 515 base/view URL — **required**, not optional |
| `OUTPUT_ROOT` | `shared/work-week.md` | *optional* — defaults to the config's own folder |

Secrets live in a sibling file, `<workspace>/.weekly-515-reporting/credentials.md`, holding
`JIRA_API_TOKEN`, `GITHUB_TOKEN`, and `AZURE_DEVOPS_PAT`. Splitting them keeps `config.md` safe to
share or paste when debugging.

## Fetch scripts (`scripts/`)

`jira_fetch.py`, `github_fetch.py`, and `azure_devops_fetch.py` are standalone, stdlib-only CLIs.
Deliberately **not** MCP servers: a script needs no per-surface registration and behaves identically
in Cowork and Claude Code. (An MCP server would only pay off if these needed interactive querying;
the fetch code could be lifted into one later.)

Shared logic lives in `scripts/_common.py` — config discovery, `KEY = value` parsing, secret
resolution, the week-anchor rule, and the retrying HTTP client. **`anchor_friday()` there is the only
Python copy of the week rule**; it mirrors the shell snippet in `shared/work-week.md`, and those two
are the pair to keep in sync.

All of them follow the same contract, so a new source can copy the pattern:

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

- [x] **Create the Jira API token.** Done — `JIRA_API_TOKEN` is in `credentials.md` and
      authenticates as Robert Davis. `JIRA_API_TOKEN_EXPIRES` is tracked so the 8/14/2026
      mid-week-expiry failure can't repeat silently.
- [ ] **Reinstall the plugin.** The installed copy is v0.5.0 (`local-desktop-app-uploads`), so none
      of the v0.6.0+ config relocation or the v0.9.0 Jira API work is live yet.
- [x] **Create the GitHub token.** Done — `GITHUB_TOKEN` authenticates as `rdavis-pbs` and returns
      private-repo commits, so the scope is sufficient.
- [x] **Claude in Chrome is disabled by PBS policy.** Settled in v0.10.1 as a local workaround in
      the playbook, then **promoted to plugin default in v0.13.0** once it was clear the policy is
      org-wide, not Robert-specific: `chat-summary` and `notes-summary` (renamed from
      `onenote-summary`, see below) now write labeled `AWAITING INPUT` stubs and stop before the
      roll-up as their *default* behavior, not a local deviation — every colleague on this plugin
      hits the same PBS policy. The claude.ai-chat portion of `claude-summary` is marked
      not-collected rather than dropped, since "unknown" and "no activity" aren't the same claim.
      The Claude Code half reads local transcripts and is unaffected **by Chrome specifically** —
      see the next item for a separate caveat on *where* the plugin runs. Robert's own run
      procedure lives in [WEEKLY-RUN-PLAYBOOK.md](WEEKLY-RUN-PLAYBOOK.md); that file no longer needs
      to carry the Chrome workaround itself, since the skills do now.
- [x] **`claude-summary`'s Claude Code surface requires running the plugin from a genuine Claude
      Code session, not Cowork — confirmed, not hypothetical.** Claude Code writes its transcripts
      to the real machine's home directory; Cowork tasks run in a sandboxed, ephemeral home (same
      reason `config.md`/`credentials.md` need a connected folder instead of `~`), so that surface
      can't be reached from inside Cowork. Robert already runs this workflow from the **Claude Code
      VS Code extension** (since 2026-10-02, originally for an unrelated reason — Cowork's plugin
      resync lagged behind his newer local plugin version, the same "Reinstall the plugin" issue
      above), so his `claude-summary` runs do find real history. The cost: **the VS Code extension
      has no Microsoft 365 Connectors UI** (confirmed 2026-10-02 — M365 shows connected in Claude
      Desktop, but not in the extension's settings), so `email-summary`/`calendar-summary` can't run
      their MCP calls from that same session. Robert bridges those two manually (same pattern as
      Slack/notes) — see `WEEKLY-RUN-PLAYBOOK.md`. Documented as general guidance for any colleague
      in README, `COLLEAGUE-SETUP.md`, and `claude-summary/SKILL.md`: running from Code (CLI,
      VS Code/JetBrains extension, or the desktop app's own Code surface) gets Claude Code history
      but costs the Microsoft 365 connector; running from Cowork gets Microsoft 365 for certain but
      not Claude Code history. **Confirmed by a colleague (v0.13.0 rollout): the desktop app's own
      Code surface also has no Microsoft 365 connector** — so there is no single surface that gets
      both. The practical answer is to run twice and merge: once from Code for `claude-summary`
      (and the REST-API sources), once from Cowork/Claude Desktop for `email-summary`/
      `calendar-summary`, pasting the Cowork run's output into the same `<FRIDAY>/` folder the Code
      run used before the roll-up. Documented in `COLLEAGUE-SETUP.md`.
- [x] **Onboarding friction found during a colleague's first setup (v0.13.0), fixed in
      `COLLEAGUE-SETUP.md`:**
      - **"Add marketplace" and "Install" are two separate, easy-to-conflate clicks.** A colleague
        added the marketplace and stopped there, assuming that was the whole install — the plugin
        itself was never installed, so none of its skills existed yet. Step 1 now calls this out
        explicitly as two distinct parts.
      - **The first-run "connect a folder" prompt gives no guidance on scope,** and a colleague
        connected their entire Documents folder rather than a new, dedicated one — oversharing
        everything in Documents to the plugin's reach, not just the 515 config/output. Step 2 now
        tells people to create a brand-new empty folder first and connect *that*, with a note on
        how to disconnect an over-broad folder already connected and reconnect a narrower one.
      - **The Airtable token's scope and bases weren't spelled out concretely enough.** Tightened
        Step 3d: scopes are `data.records:read` + `schema.bases:read` **only** (no write scope),
        **Access** is **exactly two bases** — the 515 weekly tracker and the FY27 Resource Planner
        — and **expiration is "No expiration"**, unlike Jira/GitHub, since this token isn't on a
        rotation schedule. `AIRTABLE_API_KEY_EXPIRES` is dropped from the template entirely rather
        than left optional, so nothing implies it should be tracked.
- [x] **Every collector made optional, not just Azure DevOps (v0.13.0).** Different colleagues use
      different tools, so a missing config key now skips a source cleanly instead of being either
      hardcoded-required or (for everything but Azure DevOps) simply undocumented as skippable.
      `shared/work-week.md` §2c defines the one availability check; `run-weekly-515` runs it before
      every full run and reports two lists — configured vs. available-but-unset — so the user sees
      their own setup without re-deriving it from nine SKILL.md files.
- [x] **Slack and personal notes carved out as the exception to the config-gated model.** Neither
      `SLACK_URL` nor `NOTES_LOCATION`/`NOTES_URL` was ever actually required for the manual-paste
      workflow — they're just hints that make the paste prompt more specific. `chat-summary` and
      `notes-summary` now **always** write their `AWAITING INPUT` stub regardless of whether those
      keys are set; the only way either collector is skipped is the user saying, in reply, that
      they don't use Slack or don't keep separate notes — not a missing config key. Also expanded
      the notes stub with concrete paste instructions (where to look, what date range, that a raw/
      unordered paste is fine) rather than a one-line generic ask. Added step-by-step instructions
      in `COLLEAGUE-SETUP.md` for creating the "Weekly Activity Summary" Slackbot skill itself
      (Slack's own saved-prompt AI feature), since the plugin previously assumed it already
      existed without ever explaining how to make one.
- [x] **`JIRA_SITE` pre-filled with the org's real Atlassian host (`pbsdistribution.atlassian.net`)
      in the tracked `shared/config.example.md`, with `JIRA_EMAIL` as the opt-in trigger instead.**
      Deliberately revisits the precedent in [[config-holds-secrets]] (this repo's first commit
      leaked that exact hostname and had to be scrubbed) — decided this time that an org's own
      Atlassian subdomain isn't sensitive enough to withhold, given every colleague on this plugin
      is at PBS and typing it in manually added no real benefit. Since `JIRA_SITE` is now always
      present, it stopped being a useful signal for "has this person opted into Jira collection" —
      `JIRA_EMAIL` (which must be set to the user's own real account email) is the trigger now,
      everywhere this was checked: `shared/work-week.md` §2c, `jira-summary/SKILL.md`'s error
      handling, `COLLEAGUE-SETUP.md`, `README.md`. `JIRA_JQL`'s default is also uncommented/active
      by default now rather than something to opt into.
- [x] **`onenote-summary` renamed `notes-summary` and made tool-agnostic (v0.13.0).** It no longer
      assumes OneNote, or any particular note-taking tool — it asks the user to paste whatever they
      jotted down this week, wherever that lives (OneNote, Notepad, Word, a notebook, ...).
      Robert's own OneNote navigation details (which sections, how dates are written, the
      `Credentials` page to never open) moved to
      [WEEKLY-RUN-PLAYBOOK.md](WEEKLY-RUN-PLAYBOOK.md) as a personal note for if/when browser access
      to it returns, rather than staying hardcoded in a skill meant to work for anyone.
- [ ] First real run end-to-end: sanity-check each output file, then tune the summary sections/tone
      to match how you actually write your 515.
- [ ] **Create the Azure DevOps PAT**, if you use Azure DevOps — `AZURE_DEVOPS_ORG_URL` in
      `config.md`, `AZURE_DEVOPS_PAT` in `credentials.md`, then `python
      weekly-515-reporting/scripts/azure_devops_fetch.py --check`. Not done yet, so
      `azure-git-summary` is currently skipped on every run.
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
