# Setup guide (for colleagues)

This plugin assembles your weekly **515** report by gathering a week's work activity from chat,
email, calendar, OneNote, GitHub, Jira, and Claude, then distilling it into a proposed 515 entry.
It runs in the **Claude desktop app (Cowork)**. Follow these steps once to get set up.

## Prerequisites

- The **Claude desktop app** with Cowork.
- A **Microsoft 365** account (Outlook mail/calendar, Teams) connected in Claude.
- The **GitHub** connector authorized (only needed for `git-summary`).
- **Claude in Chrome** (the browser extension) for the sources read through the browser:
  Slack, Jira, OneNote, Airtable, Cowork, and claude.ai chat.

## Step 1 — Install the plugin from the marketplace

1. In the desktop app: **Customize → Plugins → Add marketplace**.
2. Enter: `rdavis-pbs/weekly-515-reporting` (or the full URL
   `https://github.com/rdavis-pbs/weekly-515-reporting`).
3. Leave **Sync automatically** on, then **Sync**.
4. Find **weekly-515-reporting** in the plugin list and click **Install**.

With auto-sync on, you'll pick up new versions automatically as they're published.

## Step 2 — Create your own config (required)

The plugin reads your personal URLs and paths from **one file in your home directory**:

```
~/.weekly-515-reporting/config.md
```

This file is **yours** — it is never committed to GitHub and never shared. It also lives outside
the plugin folder on purpose, so it survives plugin updates. Create it once:

1. Make a folder named `.weekly-515-reporting` in your home directory
   (Windows: `C:\Users\<you>\.weekly-515-reporting`).
2. Copy the template `shared/config.example.md` from the installed plugin into it as `config.md`.
   (Easiest: just run any skill — see Step 4 — and Claude will offer to create it and prompt you
   for the values.)
3. Fill in **your own** values:

```
# Your Slack workspace/channel URL (chat-summary opens this in the browser)
SLACK_URL        = https://app.slack.com/client/TXXXXXXXX/CXXXXXXXX

# Your Jira saved/custom filter URL (jira-summary reads this)
JIRA_FILTER_URL  = https://yourorg.atlassian.net/issues/?filter=NNNNN

# Your SharePoint/OneDrive-hosted OneNote notebook URL (onenote-summary reads this)
ONENOTE_URL      = <your OneNote Doc.aspx URL from SharePoint/OneDrive>

# Your Airtable 515 base/view URL (weekly-515-rollup reads this)
AIRTABLE_515_URL = https://airtable.com/appXXXX/tblYYYY/viwZZZZ

# The folder where your dated weekly report subfolders are written
OUTPUT_ROOT      = C:\Users\<you>\Claude\Projects\515 weekly reports
```

**Where to find each value**
- `SLACK_URL` — open Slack in the browser and copy the URL of your workspace/home.
- `JIRA_FILTER_URL` — in Jira, create/open a saved filter for your issues and copy its URL.
- `ONENOTE_URL` — open your OneNote notebook in the browser (SharePoint/OneDrive) and copy the
  `Doc.aspx?...` URL.
- `AIRTABLE_515_URL` — open your team's 515 base/view in Airtable and copy the URL.
- `OUTPUT_ROOT` — a folder you've connected as a project in Cowork; reports are written under it in
  dated subfolders (`<OUTPUT_ROOT>\<FRIDAY>\`).

> Note: `onenote-summary` assumes a particular note structure (dates written inside page bodies,
> a main journal section). If your notes are organized differently, tell Claude how yours are laid
> out when you run it, or skip that collector.

## Step 3 — Browser access (Claude in Chrome)

The browser-based collectors (Slack, Jira, OneNote, Airtable, Cowork, claude.ai) open pages via the
Claude-in-Chrome extension. Make sure you're already signed in to each service in Chrome before you
run the workflow.

Under PBS enterprise policy, the extension's per-site **"Always allow"** option is **not available**.
Instead, use the **plan-approval** flow:

1. When you kick off a skill, Claude proposes a **plan** of the browser actions it intends to take —
   which sites it will open and read.
2. **Review the plan** and **approve** it. Approving authorizes the browser actions for that run.
3. Claude then works through the sites in the plan. If it needs to do something outside the approved
   plan, it will pause and ask again — review and approve as needed.

You approve the plan **per run** rather than granting standing per-site access. This keeps browsing
within enterprise policy while still letting the workflow read the sources it needs.

> This is the approach that works under our enterprise rules; if your team's policy differs, follow
> whatever your admin has set for the Claude-in-Chrome extension.

## Step 4 — Run it

- **Whole workflow (Fridays):** run `run-weekly-515` — it collects every source and produces the
  proposed 515 entry. Just ask: *"run my weekly 515."*
- **A single source:** run any one skill on its own, e.g. `jira-summary`, `chat-summary`,
  `email-summary`, `calendar-summary`, `onenote-summary`, `git-summary`, `claude-summary`, or
  `weekly-515-rollup`.

**The week & output folder:** everything targets one **Mon–Fri** work week, anchored to a Friday.
Run Mon–Fri → this week; run Sat/Sun → the week that just ended. Output goes to
`<OUTPUT_ROOT>\<FRIDAY>\` (e.g. `...\2026-07-17\`), one file per source, plus
`proposed 515 accomplishments.md` from the roll-up.

## Notes & troubleshooting

- **Your config is personal and local.** Each person maintains their own
  `~/.weekly-515-reporting/config.md`; it does not sync and is not shared.
- **`claude-summary` reads local Claude Code transcripts** from `~/.claude/projects/` on the machine
  you run it on — so run it on the machine where you actually use Claude Code.
- **A source can be skipped.** If a connector isn't authorized or a URL isn't set, that collector
  notes it was unavailable and the rest still run.
- **Nothing writes back to your systems.** The browser collectors only read; the roll-up writes a
  local draft file — you paste it into Airtable yourself after reviewing.
