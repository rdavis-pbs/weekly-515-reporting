# Local config — template

Secrets do **not** belong in this file — the Jira API token lives in `credentials.md` alongside it
(see `shared/credentials.example.md`), so this file stays safe to share.

Copy this file to `.weekly-515-reporting/config.md` **inside a folder you own and connect to Cowork**
(e.g. your "515 weekly reports" folder), then fill in your own values. Keeping it in a connected /
workspace folder means it is never committed to GitHub, survives plugin auto-updates (the plugin's
own folder is a cache replaced on every update), **and** survives Cowork sessions (the sandbox's own
home directory is wiped each session — don't store it there). Every skill that needs one of these
values reads it from `<your folder>/.weekly-515-reporting/config.md` by key. Easiest path: just run
any skill and let first-run setup create it for you.

```
# OPTIONAL -- but chat-summary always writes a paste-stub either way (see its SKILL.md); this is
# just a convenience link, never opened automatically since Claude in Chrome is disabled org-wide
# at PBS. Leave it as the placeholder (or delete the line) if you don't use Slack and tell Claude
# so when it asks -- that's what actually skips the collector, not this key.
SLACK_URL        = <your Slack URL, e.g. https://app.slack.com/client/TXXXXXXXX/CXXXXXXXX>

# --- Jira (jira-summary reads these via the Atlassian REST API) ---
# JIRA_SITE is pre-filled below since every colleague on this plugin is at PBS, on the same
# Atlassian site -- you shouldn't need to change it.
JIRA_SITE        = pbsdistribution.atlassian.net

# JIRA_EMAIL is what actually turns Jira collection on -- there's no key for JIRA_SITE alone to
# gate on, since it's always present now. Leave this as the placeholder (or delete the line) if
# you don't use Jira, and jira-summary is skipped. Set it to your real Atlassian account email
# (the one that creates the API token in credentials.md) to opt in.
JIRA_EMAIL       = <the email on your Atlassian account, e.g. you@example.com>

# JQL selecting the issues you touched. On by default (not commented out) -- every issue you
# updated during the reporting window, with your email and the week's dates filled in per run:
#   {email}      your JIRA_EMAIL
#   {start}      window start, YYYY/MM/DD  (Jira date format)
#   {end}        window end + 1 day, YYYY/MM/DD — Jira's date-only comparisons land on midnight,
#                so the extra day keeps the final day's activity; the script then filters every
#                comment and field change to the exact window itself.
#   {start_iso}  {end_iso}   the same dates as YYYY-MM-DD
# Leave as-is unless you want a different query. Copy your saved filter's JQL here instead (Jira's
# issue search has a "Switch to JQL" toggle) and replace its hardcoded dates with the placeholders.
JIRA_JQL         = issuekey in updatedBy("{email}", "{start}", "{end}") order by updatedDate desc

# OPTIONAL. Only a convenience link for humans now — the API path does not read it.
# JIRA_FILTER_URL = <your Jira saved-filter URL, e.g. https://yourorg.atlassian.net/issues/?filter=NNNNN>

# --- Personal notes (notes-summary) --- OPTIONAL, both keys. Tool-agnostic: OneNote, Notepad,
# Word, a notebook, whatever you actually use. Omit both and the skill just asks you directly each
# run; omit NOTES_URL regardless, since it only matters if your notes live somewhere a browser
# could open directly AND Claude in Chrome is available (it's disabled org-wide at PBS).
# NOTES_LOCATION = <free text, e.g. "OneNote, BI Tech Group -> Journal 2026", or "Notepad on my desktop">
# NOTES_URL      = <a browser-openable URL for your notes, only if applicable>

# --- Airtable (weekly-515-rollup reads this via the Airtable REST API) --- REQUIRED.
# This is the one source that isn't optional: without it there's no 515 format to draft into.
# Open your 515 table in the browser and paste the whole address bar; the base (app...), table
# (tbl...) and view (viw...) ids are read out of it, and trailing query junk like ?blocks=hide is
# ignored. Point it at YOUR OWN view if the table holds the whole team's entries -- the collector
# inherits the view's filters, and an unfiltered view means the draft gets modeled on colleagues'
# records. The token goes in credentials.md, NOT here.
AIRTABLE_515_URL = <your 515 base/view URL, e.g. https://airtable.com/appXXXX/tblYYYY/viwZZZZ>

# OPTIONAL. Your FY goals/tasks view -- the work you're formally committed to. The roll-up reads it
# for Next Week's Priorities instead of inferring them from the week's chatter. Same URL rule as
# above: your own personal view, copied from the address bar. Omit the key to skip this source.
# If it IS set, remember to add BOTH bases under Access on your Airtable token -- a token missing
# one base returns 404 for it, which looks like a bad URL rather than a permissions problem.
# AIRTABLE_GOALS_URL = <your goals base/view URL, e.g. https://airtable.com/appXXXX/tblYYYY/viwZZZZ>

# OPTIONAL. Your GitHub login. If omitted, git-summary uses the account that owns GITHUB_TOKEN.
# Set it only to report on a different login than the token's own account.
# GITHUB_USER    = <your GitHub login>

# OPTIONAL. Only for GitHub Enterprise Server. Defaults to github.com.
# GITHUB_HOST    = <your GitHub host, e.g. github.mycompany.com>

# --- Azure DevOps (azure-git-summary reads these via the Azure DevOps REST API) --- OPTIONAL.
# Your Azure DevOps organization URL. A PAT is scoped to one org, so only this org is covered —
# if your work spans more than one, pick the one that matters most for your 515. Leave this out
# entirely if you don't use Azure DevOps; that collector is skipped.
# AZURE_DEVOPS_ORG_URL = <your org URL, e.g. https://dev.azure.com/yourorg>

# OPTIONAL. Comma-separated project names to scope the scan to. Omit to scan every project the
# PAT can see (slower on a large org, but nothing is missed by a typo'd project name).
# AZURE_DEVOPS_PROJECT = <YourProject>, <AnotherProject>

# OPTIONAL. Your account email, used to match Git commit authorship. Normally read automatically
# from your Azure DevOps profile — set this only if the script reports it couldn't resolve one
# (common on an on-prem Azure DevOps Server).
# AZURE_DEVOPS_EMAIL = <the email on your Azure DevOps account, e.g. you@example.com>

# OPTIONAL. By default reports are written into the same folder as this config (the folder you
# connected). Set OUTPUT_ROOT only if you want them written somewhere else.
# OUTPUT_ROOT    = <an absolute folder path, e.g. C:\Users\you\Claude\Projects\515 weekly reports>
```
