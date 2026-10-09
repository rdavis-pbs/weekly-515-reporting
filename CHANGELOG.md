# Changelog

All notable changes to the weekly-515-reporting plugin.

## 0.11.0
- **New collector `azure-git-summary`, the Azure DevOps (Azure Repos) counterpart to `git-summary`.**
  New bundled script `scripts/azure_devops_fetch.py` (stdlib-only Python, same contract as the
  Jira/GitHub/Airtable fetchers) authenticates with a personal access token, enumerates every
  project and repo the token can see (or just `AZURE_DEVOPS_PROJECT`, if set), and returns three
  buckets: commits authored, PRs created (split into opened/completed by status and date), and PRs
  reviewed. Writes `<FRIDAY>/azure-git-activity.json` for the skill to summarize into
  `azure-git-summary.md`. Wired into `run-weekly-515` and read by `weekly-515-rollup`.
- **Entirely optional, unlike the other git source.** Skipped outright if `AZURE_DEVOPS_ORG_URL`
  isn't set in `config.md` — GitHub-only users see no change. New credential `AZURE_DEVOPS_PAT`
  (plus optional `AZURE_DEVOPS_PAT_EXPIRES`); new optional config keys `AZURE_DEVOPS_PROJECT` (scope
  to specific projects) and `AZURE_DEVOPS_EMAIL` (override commit-author email resolution).
- **PR review timestamps are approximated, and the script says so.** Unlike GitHub's review
  objects, Azure DevOps' PR reviewer `vote` field carries no timestamp of its own. The script pins
  a review to the window using the user's own thread comments when any exist; absent a comment, it
  falls back to the PR's created/closed date and marks the entry `vote_date_is_approximate` so the
  skill reports it more loosely rather than asserting an exact day.
- Same scope trap as GitHub, called out in both the script and the skill: a PAT missing **Code
  (Read)** on a project authenticates fine and silently sees nothing in that project — not an
  error, just an empty result that can read as "no activity."
- A PAT is scoped to one Azure DevOps organization; if work spans more than one, only the one in
  `AZURE_DEVOPS_ORG_URL` is covered, and the skill says so rather than reporting the others as idle.

## 0.10.1
- **`chat-summary` now points at the user's saved Slack skill, "Weekly Activity Summary,"** instead
  of composing a Slackbot prompt each run. The skill already carries the prompt and the week framing,
  so the ask each Friday is just "run it and paste the result" — and a hand-built prompt would drift
  from the one the user actually maintains. The generated prompt survives only as a fallback for if
  the saved skill goes away.
- **Microsoft Teams is no longer a source.** `chat-summary` is now Slack-only: the Teams connector
  step is gone, and the skill explicitly says Teams' absence is *not* a gap. The user doesn't use
  Teams, so every run was spending a Graph `chat_message_search` sweep to produce a section that
  then reported failure — 38 of 40 chats on 8/7, then 0 of 38 on 8/14 (HTTP 429). A "gap" describing
  chat that never existed is worse for the roll-up than no section, because it reads as coverage the
  report failed to get.
- **New `docs/WEEKLY-RUN-PLAYBOOK.md`, and `run-weekly-515` now reads it first.** The orchestrator
  is generic by design, but the environment it runs in isn't: two of its eight collectors need
  Claude in Chrome, which PBS has disabled outright. The playbook records the standing deviations
  once — Teams isn't a source, Slack and OneNote are user-pasted stubs with a hard checkpoint before
  the roll-up, `claude-summary` runs the Claude Code surface only, use `python` not `python3` — plus
  preflight checks, the stub templates, and the roll-up rules drafts keep violating. This replaces
  re-deriving the workflow from nine SKILL.md files every Friday, and makes the weekly run cheap
  enough that it isn't worth re-reading the whole plugin to do it.
- The Slack/OneNote paste-in workaround is now a **defined step with a stop point** rather than
  something improvised mid-run. A stub that says `AWAITING INPUT` can't be mistaken by a later
  roll-up for a quiet week, which is the failure the previous ad-hoc approach risked.

## 0.10.0
- **`weekly-515-rollup` now reads Airtable through the Airtable REST API.** New bundled script
  `scripts/airtable_fetch.py` (stdlib Python only, same shape as the Jira and GitHub fetchers)
  authenticates with a personal access token, pulls the base/table/view ids out of
  `AIRTABLE_515_URL`, and writes `<FRIDAY>/airtable-515-records.json`. The connector and browser
  paths are retained as fallbacks — the API is tried first because both fallbacks were unavailable on
  the 8/14 run, which left that week's draft formatted from memory rather than confirmed live.
- **The table schema is now fetched, not guessed.** The artifact carries real field names in table
  order, field types, and the valid `choices` for every select field — so a drafted `#N Goals` uses
  option values that actually exist instead of ones the user has to correct on paste. This is why the
  token wants `schema.bases:read` alongside `data.records:read`; without it the collector still runs
  and says what's missing.
- **Records are ordered by the reported week, not by creation time.** The script sorts on the
  week-ending date field so "the most recent records" means the most recent *weeks* — a backfilled or
  re-edited record can't jump the queue and become the format sample.
- **Linked-record fields resolve to display names.** The REST API returns a link cell as raw record
  ids (`["rec123"]`) where the connector showed "Robert Davis", so the collector looks up the linked
  table's primary field. Without this the User field is unfillable and the multi-person check below
  compares opaque ids.
- **Unfiltered views are reported.** If the sampled records span several people, the artifact says so:
  on a team-wide table that means the draft would otherwise be modeled on colleagues' entries, which
  reads as a formatting choice rather than a bug.
- **Still strictly read-only.** GETs only; the token needs no write scope. The roll-up continues to
  end at a local draft file that the user reviews and pastes in themselves.
- New credential `AIRTABLE_API_KEY` (plus optional `AIRTABLE_API_KEY_EXPIRES` for the same
  warn-before-it-lapses check the other tokens get). `AIRTABLE_515_URL` is unchanged.
- **New collector skill `goals-summary`** — the eighth collector, and the only forward-looking one.
  It reads the Airtable resource tracker (FY goals/tasks, activities mapped to department goals) and
  writes `<FRIDAY>/goals-summary.md`. It stands alone as an answer to "what's due soon?" / "what am I
  committed to?" without running a 515, which is why it's a skill rather than a step inside the
  roll-up. The roll-up reads its output when present and the JSON artifact regardless.
  - The tracker's own `Department Goals` / `FY Project` values partly coincide with the 515's `#N
    Goals` options — some match exactly, others are near misses. Where they match, the roll-up now
    uses the user's own activity-to-goal mapping instead of inferring one; near misses are flagged as
    inference.
- **New optional source: your FY goals/tasks table** (`AIRTABLE_GOALS_URL`), written to
  `<FRIDAY>/airtable-goals.json`. The roll-up now builds **Next Week's Priorities** from work you are
  formally committed to, with due dates, instead of inferring priorities from the week's chatter.
  Items arrive pre-sorted into urgency buckets — `overdue`, `due_next_7d`, `due_within_30d`, `later`,
  `undated` — measured from the reporting week's Friday, so `due_next_7d` is precisely the Next Week
  window. Omit the key and the source is skipped; the 515 read is unaffected.
  - **Selection is by due date and completion, never by status** — the one design note worth keeping.
    In the real table most near-term rows have a blank `Status`, while nearly every row that carries
    one is already overdue. Filtering on `Status in (To Do, In Progress)` therefore returns *zero*
    rows and reads as "nothing coming up": a silent wrong answer, not an error. Everything not
    Done/Delivered/Cancelled counts as committed, and the script adds ordering rather than filtering.
  - `--source 515|goals|both` runs either or both. `Created By` is dropped from the goals artifact —
    it carries a colleague's name and email, which has no business in a weekly report file.

## 0.9.0
- **`jira-summary` now uses the Atlassian Jira Cloud REST API instead of the browser.** PBS disabled
  the Claude-in-Chrome extension, so the browser path was dead. New bundled script
  `scripts/jira_fetch.py` (stdlib Python only — no pip installs, no MCP server) authenticates with a
  personal API token, runs your JQL, and pulls each matching issue's changelog and comments.
- **Attribution is now enforced mechanically.** The script keeps only comments and field changes
  whose *author is you*, dated inside the window, and writes them to `<FRIDAY>/jira-activity.json`
  for the skill to summarize. Previously the skill had to infer authorship while reading pages.
  Issues that matched the query but hold none of your activity are listed separately rather than
  dropped silently.
- **JQL dates are parameterized.** `JIRA_JQL` in config takes `{start}`/`{end}` placeholders filled
  per run, replacing the old "saved filter has hardcoded dates, ignore them" workaround. New config
  keys `JIRA_SITE` and `JIRA_EMAIL`; `JIRA_FILTER_URL` is now only a human convenience link.
- **Secrets split out of config.** The API token lives in `.weekly-515-reporting/credentials.md`
  (new template `shared/credentials.example.md`), so `config.md` stays safe to share. The token can
  also come from the `JIRA_API_TOKEN` environment variable.
- **`git-summary` now uses the GitHub REST API instead of the browser**, for the same reason. New
  bundled script `scripts/github_fetch.py` searches across every repo the token can see and returns
  six buckets: commits authored, PRs opened, PRs merged, PRs reviewed, issues opened, issues closed.
  For reviewed PRs it fetches the actual review objects, since `reviewed-by:` matches PRs reviewed at
  any time — only the reviews themselves say when the user reviewed and whether they approved or
  requested changes. New credential `GITHUB_TOKEN`; new optional config keys `GITHUB_HOST` (GitHub
  Enterprise Server) and a repurposed `GITHUB_USER` (defaults to the token's own account).
  - Note the failure mode called out in the script and skill: a token lacking `repo` scope
    authenticates fine but returns **zero** results for private-repo work. Empty counts are reported
    as a probable scope problem rather than as "no activity."
- **New `scripts/_common.py`** holding the logic both fetch scripts share: config discovery, secret
  resolution, the retrying HTTP client, and the week-anchor rule. `anchor_friday()` there is now the
  single Python implementation of the week rule, paired only with the shell snippet in
  `shared/work-week.md`.
- **Week cutover moved from Saturday to Wednesday** in `shared/work-week.md`, affecting every
  collector: run Wed–Sun → this week, run Mon or Tue → last week. Early in the week you're still
  reporting on the week that just ended.
- **Config discovery hardened.** It now walks *up* from the working directory, so running from a
  subfolder no longer misses the workspace config and silently fall back to the legacy home-directory
  copy. When multiple configs exist it warns and names them. Three stale duplicates left over from
  the v0.6.0→v0.7.0 config moves were deleted.
- Fixed `shared/work-week.md` hardcoding `python3`, which is a non-functional stub on Windows; it now
  probes for a working interpreter.
- Both fetch scripts now force UTF-8 on stdout/stderr. Windows consoles default to a legacy codepage
  (cp1252), so one emoji or CJK character in a commit message or Jira comment raised
  `UnicodeEncodeError` — *after* the JSON artifact had been written, making a successful fetch look
  like a crash. The JSON was always written as UTF-8 and was never affected.
- Fixed commit attribution in `github_fetch.py`: filtering on an exact `author == login` match dropped
  every commit whose email isn't linked to a GitHub account, because the author field falls back to
  the raw git name in that case. Since `author:LOGIN` in the query already constrains attribution, the
  filter now only drops commits GitHub positively attributes to someone else.
- Docs corrected: releases ship via the **GitHub marketplace** (`rdavis-pbs/weekly-515-reporting`),
  not by zipping a `.plugin` file, and `PROJECT-NOTES.md` no longer points at the long-obsolete
  `shared/config.md` location.

## 0.8.0
- `weekly-515-rollup`: now reads recent 515 records via the **Airtable connector** (MCP) instead of
  the browser — the connector is authorized in this environment. Base/table/view IDs come from
  `AIRTABLE_515_URL`. Falls back to the browser (`AIRTABLE_515_URL` via Claude in Chrome) if the
  connector isn't available. Still strictly read-only.
- `git-summary`: now reads GitHub **through the browser** (Claude in Chrome) using GitHub's search
  UI scoped to the user and week, since no GitHub MCP connector is available. Optional new config
  key `GITHUB_USER`; if unset, the login is read from the signed-in GitHub session.
- README, `config.example.md`, `docs/COLLEAGUE-SETUP.md`, and `docs/PROJECT-NOTES.md` updated to
  match the new connector/browser split.

## 0.7.0
- Config location moved again — this time to make it work in **remote Cowork sessions**. The v0.6.0
  home-dir path (`~/.weekly-515-reporting/config.md`) breaks in Cowork because the sandbox's home
  directory is ephemeral (wiped each session) and isn't the user's real machine home. Config now
  lives in a **connected/workspace folder**: `<folder you connect to Cowork>/.weekly-515-reporting/config.md`.
- New portable, self-discovering config resolution in `shared/work-week.md`, used by every
  config-reading skill (`chat-summary`, `jira-summary`, `onenote-summary`, `weekly-515-rollup`):
  scans `$HOME/mnt/*` (Cowork connected folders) → `$PWD` (local project) → `~` (fallback). No
  hardcoded absolute paths, so it behaves the same on Windows, macOS, and the Cowork sandbox.
- First-run setup: when no config is found, the plugin asks which connected folder to use and
  creates the config there (or tells the user to connect a folder first — the one step an agent
  can't do itself).
- `OUTPUT_ROOT` is now **optional**: reports default to the connected folder the config lives in
  (`<folder>/<FRIDAY>/`), removing the old absolute `C:\…` path that was meaningless in a Linux
  sandbox. Set `OUTPUT_ROOT` only to override.
- README, `config.example.md`, and `docs/COLLEAGUE-SETUP.md` updated to document the connected-folder
  location and the connect-a-folder-first setup step.
- `claude-summary`: Cowork is now read from the **desktop app** (its task list / on-disk history)
  rather than the browser — Cowork is desktop-only and has no browsable web URL.
- `claude-summary`: the Claude Code transcript scan now picks a working Python interpreter first
  (`python3` vs `python`) — on Windows `python3` is often a Microsoft Store stub that prints "Python
  was not found" and exits; that is no longer mistaken for "no sessions."

## 0.6.0
- Config moved out of the plugin folder to `~/.weekly-515-reporting/config.md` so it survives
  plugin auto-updates (the installed plugin folder is a cache that gets replaced on each update).
  All skills that read config (`chat-summary`, `jira-summary`, `onenote-summary`,
  `weekly-515-rollup`) and `shared/work-week.md` now point at the persistent home-directory path;
  README and `config.example.md` updated to match.

## 0.5.0
- `weekly-515-rollup`: added a "Level of detail and focus" rule set to Step 4 so proposals come out
  high-level by default — 1–2 sentences per item, centered on the user's own actions, no ticket
  numbers in the body, and status matched to reality (no in-progress work described as done).
  Rules apply to every section, not just the accomplishments.
- `chat-summary`: sharpened the Slackbot prompt — concrete week dates, focus on what the user drove
  and decisions landed, grouped by topic/project.
- `claude-summary`: made all three surfaces mandatory — Cowork is captured even when the skill runs
  inside Cowork, and the Claude Code transcript scan must be attempted before being marked
  unavailable.
- `onenote-summary`: documented how the user actually structures notes — dates inside page bodies
  (not titles), main journal at "BI Tech Group → Journal 2026," skip Archive/Credentials, `m/d/yy`
  search format, and per-section search.

## 0.4.0
- New `claude-summary` collector: summarizes Claude activity for the week — Claude Code sessions
  (read from local `~/.claude/projects` transcripts), claude.ai chat, and Cowork (both via browser).
  Wired into `run-weekly-515` and read by `weekly-515-rollup`.

## 0.3.0
- Jira window aligned to the output folder's Friday (still a 7-day Fri→Fri span).
- OneNote now reads the SharePoint-hosted notebook via the browser (was: local export folder).
- Set ONENOTE_URL and JIRA_FILTER_URL defaults.

## 0.2.0
- jira-summary: baked in the saved filter URL; filter on a computed Fri→Fri window instead of the
  filter's hardcoded dates.

## 0.1.0
- Initial plugin: collector skills (chat, email, calendar, onenote, git, jira), weekly-515-rollup,
  and the run-weekly-515 orchestrator. Shared Mon–Fri week logic and dated output folder.
