# Local config — template

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

# Jira saved/custom filter URL (jira-summary reads this)
JIRA_FILTER_URL  = <your Jira saved-filter URL, e.g. https://yourorg.atlassian.net/issues/?filter=NNNNN>

# SharePoint/OneDrive-hosted OneNote notebook URL (onenote-summary reads this)
ONENOTE_URL      = <your OneNote Doc.aspx URL from SharePoint/OneDrive>

# Airtable 515 base/view URL (weekly-515-rollup reads this)
AIRTABLE_515_URL = <your 515 base/view URL, e.g. https://airtable.com/appXXXX/tblYYYY/viwZZZZ>

# OPTIONAL. By default reports are written into the same folder as this config (the folder you
# connected). Set OUTPUT_ROOT only if you want them written somewhere else.
# OUTPUT_ROOT    = <an absolute folder path, e.g. C:\Users\you\Claude\Projects\515 weekly reports>
```
