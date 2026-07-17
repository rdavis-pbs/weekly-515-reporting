# Local config — template

Copy this file to `config.md` in the same folder and fill in your own values. `config.md` is
git-ignored, so your real URLs and paths stay off GitHub. Every skill that needs one of these
values reads it from `config.md` by key.

```
# Jira saved/custom filter URL (jira-summary reads this)
JIRA_FILTER_URL  = <your Jira saved-filter URL, e.g. https://yourorg.atlassian.net/issues/?filter=NNNNN>

# SharePoint/OneDrive-hosted OneNote notebook URL (onenote-summary reads this)
ONENOTE_URL      = <your OneNote Doc.aspx URL from SharePoint/OneDrive>

# Airtable 515 base/view URL (weekly-515-rollup reads this)
AIRTABLE_515_URL = <your 515 base/view URL, e.g. https://airtable.com/appXXXX/tblYYYY/viwZZZZ>

# Root folder where dated weekly report subfolders are written (shared/work-week.md reads this)
OUTPUT_ROOT      = <your project folder, e.g. C:\Users\you\Claude\Projects\515 weekly reports>
```
