# Setup guide (for colleagues)

This plugin assembles your weekly **515** report by gathering a week's work activity from
whichever sources you actually use — chat, email, calendar, personal notes, GitHub, Azure DevOps,
Jira, and Claude — then distilling it into a proposed 515 entry. It runs in the **Claude desktop
app (Cowork)**. Follow these steps once to get set up.

> **If you use Claude Code and want that session history in your 515, run from Code, not
> Cowork — but you'll need to run twice.** Cowork tasks execute in a separate sandboxed, ephemeral
> home directory, so the `claude-summary` collector can't see your real `~/.claude/projects/`
> transcripts from inside a Cowork task — only from a genuine Claude Code session (the CLI, the
> VS Code/JetBrains extension, or the desktop app's own **Code** surface). Jira, GitHub, Azure
> DevOps, and Airtable work the same either way (plain REST API calls, no connector). **Microsoft
> 365 is where it gets uneven, and there's no way around it: no Claude Code surface has it.**
> Confirmed by a colleague — not just the VS Code/JetBrains extensions, but the desktop app's own
> **Code** surface too, even though it's the same app as Cowork. So there's no single surface that
> gets you both Claude Code history and automatic email/calendar. The practical fix: **run the
> workflow from Code** for everything except email/calendar, **then run `email-summary` and
> `calendar-summary` separately from Cowork/Claude Desktop** and paste their results into the same
> `<FRIDAY>/` folder before the roll-up — the same manual-paste pattern Slack and personal notes
> already use. See Step 5 for the exact steps.

**Every source is optional except Airtable.** Nobody has to set up all of them — different people
rely on different tools. Set up only the sources that apply to you; anything you skip is left out
of the run automatically, with no error and no coverage gap reported. `run-weekly-515` tells you,
at the start of every run, which sources are configured and which are available but not set up
yet, so you always know what's included.

## Prerequisites

- The **Claude desktop app** with Cowork.
- An **Airtable personal access token** (`weekly-515-rollup`) — Step 3. **This is the one
  requirement**; without it there's no 515 format to draft into. Everything else below is only
  needed for the specific sources you want captured.
- A **Microsoft 365** account (Outlook mail/calendar) connected in Claude — only if you want
  `email-summary`/`calendar-summary`. The connector works in **Cowork**; **no Claude Code surface
  has it** (confirmed — not the VS Code/JetBrains extensions, and not the desktop app's own Code
  surface either), so running the plugin from Code means pasting email/calendar in manually
  instead — see the note below.
- An **Atlassian API token** (`jira-summary`) — only if you use Jira.
- A **GitHub token** (`git-summary`) — only if you use GitHub.
- An **Azure DevOps personal access token** (`azure-git-summary`) — only if you use Azure DevOps.
- **Python 3** on the machine you run this from, for whichever of the Jira, GitHub, Azure DevOps,
  and Airtable fetch scripts you actually use. Any recent version works; no packages to install.
  Already present on most machines. Needed for Airtable regardless, since that one's required.
- **Claude in Chrome** (the browser extension), only as a fallback. At PBS, this extension is
  **disabled org-wide**, so Slack and personal notes default to a manual-paste workflow instead —
  see Step 4. Jira, GitHub, Azure DevOps, and the Microsoft 365 sources never needed the browser.

## Step 1 — Install the plugin from the marketplace

This is **two separate actions**, not one — adding the marketplace only tells Claude *where* to
look; it does not install anything by itself. A colleague stopped after adding the marketplace and
assumed they were done, then found none of the skills below existed. Don't skip part B.

**Part A — add the marketplace (a source, not the plugin):**

1. In the desktop app: **Customize → Plugins → Add marketplace**.
2. Enter: `rdavis-pbs/weekly-515-reporting` (or the full URL
   `https://github.com/rdavis-pbs/weekly-515-reporting`).
3. Leave **Sync automatically** on, then **Sync**.

At this point you've only registered the marketplace — the plugin itself is **not** installed yet.

**Part B — install the plugin itself (a separate, required click):**

4. Find **weekly-515-reporting** in the plugin list that now appears and click **Install**.

Only after Part B will the plugin's skills (`run-weekly-515`, `chat-summary`, etc.) actually be
available to use. With auto-sync on, you'll pick up new versions automatically as they're
published — you won't need to repeat either part for updates, only for the first install.

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

**Use a brand-new, dedicated folder — not an existing one like your whole Documents folder.**
Connecting a folder gives Claude read/write reach over everything in it, so the right size is "just
this plugin's config and reports," not "everything I own." A colleague connected their entire
Documents folder when first prompted, which was far broader than intended.

Set it up once:

1. **Create a new, empty folder first**, before you connect anything — e.g.
   `Documents\515 weekly reports` (Windows) or `~/Documents/515 weekly reports` (macOS). It should
   contain nothing but this plugin's config and its weekly output; don't reuse a folder that
   already holds unrelated files.
2. **Connect *that* folder** to Cowork (not Documents itself, not your whole home directory). This
   is a manual step in the Cowork UI — Claude can't connect a folder for you. In the desktop app,
   look for a folder/connector picker (often prompted automatically the first time a skill needs
   one, or reachable from Cowork's own settings) and point it at the new folder from step 1.
   - **If you're prompted mid-run** ("this task needs a folder" or similar) rather than doing this
     ahead of time, the same rule applies: browse to and select the new dedicated folder, not a
     convenient broad one like Documents or Desktop.
   - **If you already connected something too broad,** disconnect it and reconnect the narrower
     folder instead: look in the desktop app's folder/connector settings (near where you connected
     it) for a way to remove or disconnect that folder, then repeat this step with the new one.
     Any `.weekly-515-reporting/config.md` or `<FRIDAY>/` output already written under the old
     connection should be moved into the new folder so the plugin keeps finding it.
3. **Create the config.** Easiest: just run any skill (see Step 5) — first-run setup will ask which
   connected folder to use, create `.weekly-515-reporting/config.md` there, and prompt you for the
   values. Or copy the template `shared/config.example.md` into
   `<your folder>/.weekly-515-reporting/config.md` yourself.
4. Fill in **your own** values:

Every key below is **optional** except `AIRTABLE_515_URL` — only fill in the ones for sources you
actually use. Leaving the rest commented out just means that collector is skipped.

```
# OPTIONAL. Your Slack workspace/channel URL (chat-summary points you here to run your saved
# recap skill and paste the result). Omit it entirely if you don't use Slack.
SLACK_URL        = https://app.slack.com/client/TXXXXXXXX/CXXXXXXXX

# JIRA_SITE is pre-filled below since everyone on this plugin is at PBS, on the same Jira site —
# you shouldn't need to change it. JIRA_EMAIL is what actually turns Jira collection on: leave it
# as the placeholder (or delete the line) if you don't use Jira, and jira-summary is skipped. Set
# it to your real Atlassian account email to opt in. The token itself goes in credentials.md, NOT
# here — see Step 3.
JIRA_SITE        = pbsdistribution.atlassian.net
JIRA_EMAIL       = you@example.com

# JIRA_JQL is on by default (not commented out) -- it's the standard "issues I updated this
# window" query, with your email and the week's dates filled in automatically each run. Leave it
# as-is unless you want to scope it differently; see the OPTIONAL note further down for how.
JIRA_JQL         = issuekey in updatedBy("{email}", "{start}", "{end}") order by updatedDate desc

# OPTIONAL, both keys. Personal notes, any tool — OneNote, Notepad, Word, a notebook, whatever you
# actually use (notes-summary reads these). NOTES_LOCATION is just free text to make the paste
# prompt specific; omit both and it asks you directly each run.
# NOTES_LOCATION = <e.g. "OneNote" or "Notepad file on my desktop">
# NOTES_URL      = <only if your notes live somewhere a browser could open directly>

# REQUIRED. Your Airtable 515 base/view URL (weekly-515-rollup reads this; token goes in
# credentials.md). This is the one source that isn't optional.
AIRTABLE_515_URL = https://airtable.com/appXXXX/tblYYYY/viwZZZZ

# OPTIONAL — your Azure DevOps organization, if you use it alongside or instead of GitHub
# (azure-git-summary reads this; token goes in credentials.md, NOT here — see Step 3)
# AZURE_DEVOPS_ORG_URL = https://dev.azure.com/yourorg

# OPTIONAL — your FY goals/tasks view, used for Next Week's Priorities
# AIRTABLE_GOALS_URL = https://airtable.com/appXXXX/tblYYYY/viwZZZZ

# OPTIONAL — reports default to the connected folder this config lives in.
# Set OUTPUT_ROOT only if you want them written somewhere else.
# OUTPUT_ROOT    = C:\Users\<you>\Claude\Projects\515 weekly reports
```

**Where to find each value**
- `SLACK_URL` — open Slack in the browser and copy the URL of your workspace/home.
- `JIRA_SITE` — already filled in correctly for everyone at PBS; only change it if you're on a
  different Atlassian site than `pbsdistribution.atlassian.net`.
- `JIRA_EMAIL` — **this is what turns Jira collection on.** Set it to the email address on your
  Atlassian account (must be the account that creates the API token in Step 3). Leave it as the
  placeholder, or remove the line, and `jira-summary` is skipped — `JIRA_SITE` being pre-filled
  doesn't opt you in by itself.
- `NOTES_LOCATION` / `NOTES_URL` — optional. A short reminder of where you keep notes (free text),
  and, only if applicable, a browser-openable URL for them. See Step 4 for why most people at PBS
  leave `NOTES_URL` unset.
- `AIRTABLE_515_URL` — open your 515 base/view in Airtable and copy the whole address bar (trailing
  query junk like `?blocks=hide` is ignored). Prefer **your own** filtered view over a team-wide one.
- `AIRTABLE_GOALS_URL` — optional. Your personal view of your team's FY goals/tasks resource tracker.
  Setting it enables the `goals-summary` collector, so Next Week's Priorities comes from work you're
  actually committed to, with due dates, instead of being inferred from the week's activity. It also
  lets you ask "what's due soon?" on any day without running a 515. Leave it out and that collector is
  skipped.
- `AZURE_DEVOPS_ORG_URL` — optional. Your Azure DevOps organization URL, e.g.
  `https://dev.azure.com/yourorg`. Setting it enables the `azure-git-summary` collector. Leave it out
  if you don't use Azure DevOps and that collector is skipped entirely. A PAT is scoped to one
  organization, so if your work spans more than one, pick the one that matters for your 515.
- `OUTPUT_ROOT` — optional; leave it commented out and reports go into the connected folder your
  config lives in (`<that folder>/<FRIDAY>/`). Set it only to write reports somewhere else.

> Note: `notes-summary` doesn't assume any particular note-taking tool or structure — it just asks
> you to paste the week's entries. If you want it to prompt more specifically (e.g. naming your
> OneNote section), set `NOTES_LOCATION`.

## Step 3 — API tokens (only for the sources you use — `AIRTABLE_API_KEY` is the one required token)

These read through REST APIs rather than the browser, so each needs a personal token. Tokens
inherit **your own** permissions — they can only see what you can already see, and the plugin only
ever reads. Add only the ones for sources you actually use; all go in the same file:

```
<your connected folder>/.weekly-515-reporting/credentials.md
```

```
JIRA_API_TOKEN   = <paste>   # only if you use Jira
GITHUB_TOKEN     = <paste>   # only if you use GitHub
AZURE_DEVOPS_PAT = <paste>   # only if you set AZURE_DEVOPS_ORG_URL in config.md
AIRTABLE_API_KEY = <paste>   # required — there's no 515 format to draft into without it
```

The template is `shared/credentials.example.md`. Treat this file like a password file — it stays
separate from `config.md` so your config remains safe to share.

### 3a — Atlassian API token (Jira)

Atlassian's token page offers **two different things** — pick the first one, not the second:

- **"Create API token"** (no scopes, sometimes called a *classic* token) — **use this one.** It
  authenticates with your email + token directly against `https://yourorg.atlassian.net/...`,
  which is exactly how `jira_fetch.py` talks to Jira.
- **"Create API token with scopes"** (a *scoped*/granular token) — **don't use this for this
  plugin.** Scoped tokens only work through a different URL, `api.atlassian.com/ex/jira/{your
  cloud id}/...`, not your site's own domain — `jira_fetch.py` doesn't call that gateway, so a
  scoped token fails here (typically a 401) even with every relevant scope selected. This isn't a
  missing-permission problem; it's the wrong kind of token for how this script talks to Jira.

1. Go to <https://id.atlassian.com/manage-profile/security/api-tokens>.
2. Click **Create API token** (plain, no scopes), name it something like `weekly-515-reporting`,
   and **copy the value immediately** — Atlassian shows it only once.
3. Save it as `JIRA_API_TOKEN` in `credentials.md`.

**On needing to read issues, comments, and attachments:** a classic token has no scope picker at
all — there's nothing to select. It simply authenticates as *you*, so it can read (and, for that
matter, write) anything your own Jira account can already see in the UI: issues, comments,
attachments, worklogs, all of it, across every project you have access to. `jira_fetch.py` itself
only reads issues, their comment text, and their field-change history (the changelog) — it never
downloads attachment files — but since the token's access is just "whatever you can see," there's
no separate attachments permission to grant either way.
4. Verify — ask Claude to *"check my Jira connection"*, or run the check mode directly:

```bash
python <plugin>/scripts/jira_fetch.py --check
```

That confirms authentication and the query, prints how many issues matched, and writes nothing.

**Optional — customize which issues are scanned.** `JIRA_JQL` in `config.md` already carries the
default query above (every issue *you* updated during the reporting window) — you don't need to
add it yourself. To scope it differently, copy your own JQL from Jira's issue search (use the
**Switch to JQL** toggle) and paste it over the default, replacing any hardcoded dates with the
`{start}` and `{end}` placeholders so the plugin can fill those in per run.

### 3b — GitHub token (`git-summary`)

1. Go to <https://github.com/settings/tokens>.
2. Create a token:
   - **Classic** (simplest): tick **`repo`** and **`read:org`**.
   - **Fine-grained**: grant read-only **Contents**, **Pull requests**, **Issues**, and **Metadata**
     on the repos or orgs you work in.
3. Save it as `GITHUB_TOKEN` in `credentials.md`.
4. Verify:

```bash
python <plugin>/scripts/github_fetch.py --check
```

> **The `repo` / Contents permission is the one that matters.** Without it the API sees only your
> *public* activity, so a week of private-repo work reports as "no activity" — a silent wrong answer
> rather than an error. If `--check` shows suspiciously few PRs, that's almost always the cause.

**On GitHub Enterprise Server?** Add `GITHUB_HOST = github.yourcompany.com` to `config.md`; the
script switches to that host's API automatically.

### 3c — Azure DevOps personal access token (`azure-git-summary`) — optional

Skip this if you don't use Azure DevOps; the collector is simply left out of your run.

1. Go to `https://dev.azure.com/{your org}/_usersSettings/tokens`.
2. Create a token with scope **Code (Read)**. That's enough for commits, PRs, and reviews.
3. Save it as `AZURE_DEVOPS_PAT` in `credentials.md`, and set `AZURE_DEVOPS_ORG_URL` in `config.md`
   (Step 2) to your org, e.g. `https://dev.azure.com/yourorg`.
4. Verify:

```bash
python <plugin>/scripts/azure_devops_fetch.py --check
```

> **Code (Read) is per-project.** A PAT missing it on a given project just doesn't see that
> project's repos — no error, an empty result. If `--check` or a run shows suspiciously little,
> that's the first thing to check, same as the GitHub `repo` scope trap above.
>
> **A PAT is scoped to one organization.** If your Azure DevOps work spans more than one org, only
> the one in `AZURE_DEVOPS_ORG_URL` is covered. Pick the one that matters most for your 515, or set
> up a second config if you genuinely need both (not the common case).
>
> **Large orgs:** set `AZURE_DEVOPS_PROJECT` in `config.md` to a comma-separated list of project
> names to scope the scan and speed it up, rather than enumerating every project you can see.

### 3d — Airtable personal access token (`weekly-515-rollup`)

1. Go to <https://airtable.com/create/tokens> and click **Create token**.
2. Under **Scopes**, add **only** `data.records:read` and `schema.bases:read` — read-only, no
   write scopes. The roll-up never needs to write to Airtable (see below), so don't add
   `data.records:write` or anything else just in case.
3. Under **Access**, add **exactly two bases** — no more, no less:
   - The **515 weekly tracker** base (the one `AIRTABLE_515_URL` points into) — always required.
   - The **FY27 Resource Planner** base (the one `AIRTABLE_GOALS_URL` points into, if you set it)
     — only needed if you're using the `goals-summary` collector.
   Both need to be on the **Access** list for the token to see them; adding scopes alone isn't
   enough (see the warning below).
4. **Expiration: choose "No expiration."** Unlike the Jira and GitHub tokens below, this one is
   meant to be set up once and left alone — there's no scheduled rotation for it. Leave
   `AIRTABLE_API_KEY_EXPIRES` out of `credentials.md` entirely; it doesn't apply here, and adding a
   date would make the collector warn about an expiry that was never going to happen.
5. Save the token itself as `AIRTABLE_API_KEY` in `credentials.md`.
6. Verify:

```bash
python <plugin>/scripts/airtable_fetch.py --check
```

That prints each table and view name, the field list, and whether the view returns any records.

> **Don't skip the Access step.** A token with scopes but no base added authenticates fine and then
> returns **HTTP 404 for the base** — it reads like a wrong URL rather than a permissions problem.
> This is also the trap when you *add* a second base later: the token keeps working for the first one
> and 404s only for the new one. If you add `AIRTABLE_GOALS_URL` after the fact, come back here and
> add the FY27 Resource Planner base to the same token's **Access** list — don't create a second
> token for it.
>
> **`schema.bases:read` is worth adding.** It's what supplies your real field names and the valid
> options for select fields like Goals. Without it the roll-up still runs, but it has to guess those
> values and you end up fixing them by hand on every paste.
>
> **Point `AIRTABLE_515_URL` at your own view** if your table holds the whole team's entries. The
> collector inherits that view's filters, so an unfiltered view means your draft gets modeled on
> colleagues' records. It warns you when the records it sampled span several people.

Read-only is deliberate here: the roll-up writes a local draft you review and paste into Airtable
yourself, so no token in this plugin ever needs write access.

**Tokens expire** (Atlassian defaults to about a year; GitHub uses whatever expiry you pick).
**Airtable is the exception — set it to "No expiration" when you create it (see above)** and don't
track an expiry date for it. When a Jira or GitHub token does lapse, that collector fails with a
clear `HTTP 401`; create a replacement, paste it into `credentials.md`, and revoke the old one. If
you record the
expiry date alongside those two — `JIRA_API_TOKEN_EXPIRES`, `AZURE_DEVOPS_PAT_EXPIRES` — the collector
warns you for the three weeks beforehand instead of failing mid-week.

## Step 4 — Slack and personal notes (manual paste, by default)

**Claude in Chrome is disabled org-wide at PBS**, so `chat-summary` and `notes-summary` don't try
to open anything in a browser. Instead, each writes a stub file labeled `Status: AWAITING INPUT`
and the run pauses there:

- **Slack** — open your saved **"Weekly Activity Summary"** skill (or whatever recap you use) in
  Slack yourself, run it, and paste the reply into the stub when Claude asks. Don't have that
  skill yet? See **"Creating the Weekly Activity Summary Slack skill"** below — it's a one-time,
  few-minute setup.
- **Personal notes** — open wherever you keep notes yourself (OneNote, Notepad, Word, a notebook,
  whatever) and paste the week's entries into the stub when Claude asks. The stub itself spells out
  how (find the week's entries, keep original dates if you have them, a raw/unordered paste is
  fine) — you don't need to prepare anything beforehand.

**Both stubs get written every time, whether or not you've set `SLACK_URL`/`NOTES_LOCATION`/
`NOTES_URL`** — those were never required for the paste workflow, only nice-to-have hints. A raw
paste is fine for both — no cleanup needed. `run-weekly-515` won't draft the final roll-up until
both stubs are filled; the **only** way either gets skipped instead is by telling Claude directly
that you don't use Slack, or don't keep separate notes — it won't ask that proactively, so say so
whenever it's true for you.

Jira, GitHub, Azure DevOps, and the Microsoft 365 sources (mail, calendar) all still work normally
— none of them has ever used the browser.

### Creating the "Weekly Activity Summary" Slack skill

This is a **Slackbot skill** (Slack's own saved-prompt AI feature, not a Claude or PBS-specific
thing) — a reusable prompt you build once inside Slack and run every week:

1. In Slack's desktop app, click **Slackbot** in your sidebar (click **More** first if you don't
   see it), then open the **Skills** tab.
2. Click **Add skill → Create a skill → Build from scratch**.
3. Under **Description**, write something like: *"Summarizes what I worked on, decided, and
   flagged as blocked across my Slack channels and DMs for the current work week — for my weekly
   515 report."* This is what Slackbot uses to know when to apply the skill.
4. Name it by clicking **[New Skill]** — call it **Weekly Activity Summary** (this plugin's docs
   and stubs refer to it by that exact name, so Claude knows what to ask for).
5. Under **Steps**, write the actual instructions, e.g.:
   > Figure out the most recently completed Monday–Friday work week relative to today. Search my
   > activity — messages I sent and threads I participated in — across all the channels and DMs
   > I'm in, within that range. Summarize it, grouped by topic or project: decisions I made or
   > helped land, things I moved forward or unblocked, anything I flagged as blocked or waiting
   > on, and other notable discussions worth remembering. Be factual and specific — dates, names,
   > concrete outcomes, no editorializing.
6. Under **Output**, describe the format: *"A plain-text reply in this chat, organized under
   Decisions / Progress & Accomplishments / Blockers & Open Threads / Notable Discussions headers,
   ready to copy and paste elsewhere."* Matching `chat-summary`'s own section headers here means
   your paste drops in almost as-is.
7. Click **Use skill** to test it, then adjust the description/steps/output (directly, or by
   asking Slackbot to revise them) until the output looks right.

Once saved, it shows up under the **Skills** tab any time — run it each Friday (or whenever you're
doing your 515) and paste the reply into the `chat-summary.md` stub.

> **If your organization has since re-enabled Claude in Chrome**, both collectors can read their
> source directly instead of asking for a paste — see the SKILL.md files if you want to switch.
> Under PBS enterprise policy when the extension *was* available, its per-site **"Always allow"**
> option wasn't available either; Claude would instead propose a **plan** of the sites it intended
> to open, you'd review and approve it per run, and it would stop and ask again for anything
> outside that plan. That flow only applies if the extension is enabled — it is not currently, so
> the manual-paste path above is what you'll actually use.

## Step 5 — Run it

- **Whole workflow (Fridays):** run `run-weekly-515` — it reports which of your configured sources
  it's collecting, runs each, then produces the proposed 515 entry. Just ask: *"run my weekly 515."*
- **A single source:** run any one skill on its own, e.g. `jira-summary`, `chat-summary`,
  `email-summary`, `calendar-summary`, `notes-summary`, `git-summary`, `azure-git-summary`,
  `claude-summary`, or `weekly-515-rollup`.
- **Just want to see what's configured?** Ask *"what sources do I have set up for my 515?"* — the
  same check `run-weekly-515` does at the start of every run.
- **Where to run it, if you use Claude Code — and why you may need to run twice:** run from a
  genuine Claude Code session (the CLI, the VS Code/JetBrains extension, or the desktop app's own
  **Code** surface) rather than Cowork, so `claude-summary` can see your real
  `~/.claude/projects/` transcripts. Run from Cowork and that one surface comes back not-collected
  instead. The catch, confirmed: **no Code surface has the Microsoft 365 connector**, including the
  desktop app's own Code surface — so if you run from Code, `email-summary`/`calendar-summary`
  can't reach Outlook from that same session. Two ways to handle it:
  1. **Run `run-weekly-515` from Code**, letting it skip email/calendar as "not configured" (or
     mark them not-collected). Then separately, **from Cowork or Claude Desktop**, run
     `email-summary` and `calendar-summary` on their own for the same week and let them write into
     the *same* `<your folder>/<FRIDAY>/` folder your Code run used. Finally run `weekly-515-rollup`
     (from either surface) once both runs have landed their files there.
  2. Or skip email/calendar from your 515 entirely if they're not worth the extra pass — they're
     optional like everything else.

  Either way, don't run `weekly-515-rollup` until you've decided — it reads whatever's in the
  folder at that moment, so a rollup run between the two passes will draft without email/calendar.

**The week & output folder:** everything targets one **Mon–Fri** work week, anchored to a Friday,
with the cutover on **Wednesday**:

- Run **Wednesday–Sunday** → this week (on Sat/Sun, that's the Friday just passed).
- Run **Monday or Tuesday** → last week, since early in the week you're still reporting on the week
  that just ended rather than the one barely underway.

Output goes into your connected folder under a dated subfolder (`<your folder>/<FRIDAY>/`, e.g.
`.../2026-07-17/`), one file per source, plus `proposed 515 accomplishments.md` from the roll-up.

`jira-summary` is the one exception to Mon–Fri: it reports a 7-day **Friday→Friday** span ending on
that same anchor Friday, so its window lines up with the folder.

## Notes & troubleshooting

- **Your config is personal and local.** Each person maintains their own
  `<their connected folder>/.weekly-515-reporting/config.md`; it does not sync and is not shared.
- **Keep exactly one config.** The plugin searches your Cowork connected folders, then upward from
  the working directory, then your home directory. If it finds more than one `config.md` it warns
  and uses the first — delete the extras rather than leaving a stale copy to shadow the real one.
- **Your token stays in `credentials.md`**, never in `config.md` and never in a report file. Nothing
  in the plugin prints it.
- **Where config must live in Cowork.** Store it in a folder you've **connected** to Cowork. The
  sandbox's own home directory (`~`) is wiped after each remote session, so a config left there
  won't be found next time — the connected folder is what persists.
- **`claude-summary` reads local Claude Code transcripts** from `~/.claude/projects/` on the machine
  you run it on — so run it on the machine where you actually use Claude Code. **If you use Claude
  Code, run the plugin from a genuine Claude Code session** — the CLI in a terminal, the VS Code or
  JetBrains extension, or the desktop app's own **Code** surface — **not from Cowork**, to have
  that session history included in the roll-up. Cowork tasks run in a separate sandboxed, ephemeral
  home directory, so `~/.claude/projects/` resolves to Cowork's own (empty) copy rather than your
  real history when run that way; the Claude Code surface then comes back not-collected instead of
  showing your actual sessions.
- **Every source can be skipped — that's the normal case, not an error.** If a connector isn't
  authorized or a key isn't set in `config.md`/`credentials.md`, that collector is simply left out
  and the rest still run. `run-weekly-515` lists what's configured vs. not set up before it runs
  anything, so you don't have to remember your own setup.
- **Nothing writes back to your systems.** The Jira, GitHub, Azure DevOps, and Airtable API calls
  and the browser collectors only read; the roll-up writes a local draft file — you paste it into
  Airtable yourself after reviewing. None of the tokens needs write scope.
- **TLS errors.** If your network inspects TLS and a fetch fails on certificate validation, every
  fetch script takes `--insecure` to skip verification. Check with your admin before relying on it.
