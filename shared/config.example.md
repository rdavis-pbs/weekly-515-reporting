# Local config — template

Copy this file to `~/.weekly-515-reporting/config.md` (a `.weekly-515-reporting` folder in your
home directory) and fill in your own values. That location lives **outside** the plugin folder, so
it is never committed to GitHub **and** it survives plugin auto-updates — the plugin's own folder
is a cache that gets replaced on every update. Every skill that needs one of these values reads it
from `~/.weekly-515-reporting/config.md` by key.

```
# Slack workspace/channel URL (chat-summary opens this in the browser)
SLACK_URL        = <your Slack URL, e.g. https://app.slack.com/client/TXXXXXXXX/CXXXXXXXX>

# Jira saved/custom filter URL (jira-summary reads this)
JIRA_FILTER_URL  = <your Jira saved-filter URL, e.g. https://yourorg.atlassian.net/issues/?filter=NNNNN>

# SharePoint/OneDrive-hosted OneNote notebook URL (onenote-summary reads this)
ONENOTE_URL      = <your OneNote Doc.aspx URL from SharePoint/OneDrive>

# Airtable 515 base/view URL (weekly-515-rollup reads this)
AIRTABLE_515_URL = <your 515 base/view URL, e.g. https://airtable.com/appXXXX/tblYYYY/viwZZZZ>

# Root folder where dated weekly report subfolders are written (shared/work-week.md reads this)
OUTPUT_ROOT      = <your project folder, e.g. C:\Users\you\Claude\Projects\515 weekly reports>
```
