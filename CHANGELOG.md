# Changelog

All notable changes to the weekly-515-reporting plugin.

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
