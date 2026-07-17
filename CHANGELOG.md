# Changelog

All notable changes to the weekly-515-reporting plugin.

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
