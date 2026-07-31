# Setup guide (for colleagues)

This plugin assembles your weekly **515** report by gathering a week's work activity from chat,
email, calendar, OneNote, GitHub, Jira, and Claude, then distilling it into a proposed 515 entry.
It runs in the **Claude desktop app (Cowork)**. Follow these steps once to get set up.

## Prerequisites

- The **Claude desktop app** with Cowork.
- A **Microsoft 365** account (Outlook mail/calendar, Teams) connected in Claude.
- The **Airtable** connector authorized (used by `weekly-515-rollup`).
- **Claude in Chrome** (the browser extension) for the sources read through the browser:
  Slack, Jira, OneNote, GitHub, and claude.ai chat — be signed in to each in Chrome.

## Step 1 — Install the plugin from the marketplace

1. In the desktop app: **Customize → Plugins → Add marketplace**.
2. Enter: `rdavis-pbs/weekly-515-reporting` (or the full URL
   `https://github.com/rdavis-pbs/weekly-515-reporting`).
3. Leave **Sync automatically** on, then **Sync**.
4. Find **weekly-515-reporting** in the plugin list and click **Install**.

With auto-sync on, you'll pick up new versions automatically as they're published.

## Step 2 — Connect a folder and create your config (required)

The plugin reads your personal URLs from **one file inside a folder you connect to Cowork**:

```
<your connected folder>/.weekly-515-reporting/config.md
```

Keeping it in a folder *you* connect — rather than in the plugin folder or the sandbox home —
matters for three reasons: it's never committed to GitHub, it survives plugin updates (the installed
plugin folder is a cache that gets replaced), **and** it survives Cowork sessions (each remote
session gets a fresh, throwaway home directory — anything stored there is gone next time). A
connected folder is the one place that persists.

Set it up once:

1. **Connect a folder** to Cowork — pick (or make) a folder to hold your 515 config and reports,
   e.g. a `515 weekly reports` folder. This is a manual step in the Cowork UI; Claude can't connect
   a folder for you.
2. **Create the config.** Easiest: just run any skill (see Step 4) — first-run setup will ask which
   connected folder to use, create `.weekly-515-reporting/config.md` there, and prompt you for the
   values. Or copy the template `shared/config.example.md` into
   `<your folder>/.weekly-515-reporting/config.md` yourself.
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

# OPTIONAL — reports default to the connected folder this config lives in.
# Set OUTPUT_ROOT only if you want them written somewhere else.
# OUTPUT_ROOT    = C:\Users\<you>\Claude\Projects\515 weekly reports
```

**Where to find each value**
- `SLACK_URL` — open Slack in the browser and copy the URL of your workspace/home.
- `JIRA_FILTER_URL` — in Jira, create/open a saved filter for your issues and copy its URL.
- `ONENOTE_URL` — open your OneNote notebook in the browser (SharePoint/OneDrive) and copy the
  `Doc.aspx?...` URL.
- `AIRTABLE_515_URL` — open your team's 515 base/view in Airtable and copy the URL.
- `OUTPUT_ROOT` — optional; leave it commented out and reports go into the connected folder your
  config lives in (`<that folder>/<FRIDAY>/`). Set it only to write reports somewhere else.

> Note: `onenote-summary` assumes a particular note structure (dates written inside page bodies,
> a main journal section). If your notes are organized differently, tell Claude how yours are laid
> out when you run it, or skip that collector.

## Step 3 — Browser access (Claude in Chrome)

The browser-based collectors (Slack, Jira, OneNote, GitHub, claude.ai) open pages via the
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
Run Mon–Fri → this week; run Sat/Sun → the week that just ended. Output goes into your connected
folder under a dated subfolder (`<your folder>/<FRIDAY>/`, e.g. `.../2026-07-17/`), one file per
source, plus `proposed 515 accomplishments.md` from the roll-up.

## Notes & troubleshooting

- **Your config is personal and local.** Each person maintains their own
  `<their connected folder>/.weekly-515-reporting/config.md`; it does not sync and is not shared.
- **Where config must live in Cowork.** Store it in a folder you've **connected** to Cowork. The
  sandbox's own home directory (`~`) is wiped after each remote session, so a config left there
  won't be found next time — the connected folder is what persists.
- **`claude-summary` reads local Claude Code transcripts** from `~/.claude/projects/` on the machine
  you run it on — so run it on the machine where you actually use Claude Code.
- **A source can be skipped.** If a connector isn't authorized or a URL isn't set, that collector
  notes it was unavailable and the rest still run.
- **Nothing writes back to your systems.** The browser collectors only read; the roll-up writes a
  local draft file — you paste it into Airtable yourself after reviewing.
