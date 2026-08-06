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
# Slack workspace/channel URL (chat-summary opens this in the browser)
SLACK_URL        = <your Slack URL, e.g. https://app.slack.com/client/TXXXXXXXX/CXXXXXXXX>

# --- Jira (jira-summary reads these via the Atlassian REST API) ---
# Your Atlassian Cloud site host, and the account email that owns the API token.
# The token itself goes in credentials.md, NOT here — see shared/credentials.example.md.
JIRA_SITE        = <your Atlassian host, e.g. yourorg.atlassian.net>
JIRA_EMAIL       = <the email on your Atlassian account, e.g. you@example.com>

# OPTIONAL. JQL selecting the issues you touched. Placeholders are substituted per run:
#   {email}      your JIRA_EMAIL
#   {start}      window start, YYYY/MM/DD  (Jira date format)
#   {end}        window end + 1 day, YYYY/MM/DD — Jira's date-only comparisons land on midnight,
#                so the extra day keeps the final day's activity; the script then filters every
#                comment and field change to the exact window itself.
#   {start_iso}  {end_iso}   the same dates as YYYY-MM-DD
# Omit this key to use the default below. Copy your saved filter's JQL here (Jira's issue search
# has a "Switch to JQL" toggle) and replace its hardcoded dates with the placeholders.
# JIRA_JQL       = issuekey in updatedBy("{email}", "{start}", "{end}") order by updatedDate desc

# OPTIONAL. Only a convenience link for humans now — the API path does not read it.
# JIRA_FILTER_URL = <your Jira saved-filter URL, e.g. https://yourorg.atlassian.net/issues/?filter=NNNNN>

# SharePoint/OneDrive-hosted OneNote notebook URL (onenote-summary reads this)
ONENOTE_URL      = <your OneNote Doc.aspx URL from SharePoint/OneDrive>

# Airtable 515 base/view URL (weekly-515-rollup reads this via the Airtable connector)
AIRTABLE_515_URL = <your 515 base/view URL, e.g. https://airtable.com/appXXXX/tblYYYY/viwZZZZ>

# OPTIONAL. Your GitHub login. If omitted, git-summary uses the account that owns GITHUB_TOKEN.
# Set it only to report on a different login than the token's own account.
# GITHUB_USER    = <your GitHub login>

# OPTIONAL. Only for GitHub Enterprise Server. Defaults to github.com.
# GITHUB_HOST    = <your GitHub host, e.g. github.mycompany.com>

# OPTIONAL. By default reports are written into the same folder as this config (the folder you
# connected). Set OUTPUT_ROOT only if you want them written somewhere else.
# OUTPUT_ROOT    = <an absolute folder path, e.g. C:\Users\you\Claude\Projects\515 weekly reports>
```
