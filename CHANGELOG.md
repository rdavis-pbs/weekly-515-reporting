# Changelog

All notable changes to the weekly-515-reporting plugin.

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
