# Shared: target work week and output folder

Every skill in this plugin writes into the **same** dated folder so the roll-up can find all
the pieces. Use this exact logic so the collectors always agree on the folder name.

## 1. Determine the target work week (Mon–Fri)

The target week is anchored to a Friday, and the cutover is **Wednesday**:

- If **today is Wednesday–Sunday**, use **this** week (this Monday through this Friday). Weeks are
  Monday-start, so on Saturday and Sunday "this week's Friday" is the Friday that just passed.
- If **today is Monday or Tuesday**, use **last** week — early in the week you are still reporting
  on the week that just ended, not the one barely underway.

Run this to get the anchor Friday date as `YYYY-MM-DD`. It also prints the Monday and the
ISO start/end timestamps you can hand to search tools:

```bash
# Pick a working Python. On Windows a bare `python3` can be a non-functional Store stub, so try
# `python` first and verify the interpreter actually runs before committing to it.
PY=""
for c in python python3 py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && PY="$c" && break; done
[ -z "$PY" ] && echo "No working Python found" >&2

"$PY" - <<'PY'
import datetime
today = datetime.date.today()
wd = today.weekday()                                    # Mon=0 ... Sun=6
friday = today - datetime.timedelta(days=wd - 4)        # this Monday-start week's Friday
if wd <= 1:                                             # Monday or Tuesday -> report on last week
    friday -= datetime.timedelta(days=7)
monday = friday - datetime.timedelta(days=4)
print("FRIDAY=" + friday.isoformat())
print("MONDAY=" + monday.isoformat())
print("WEEK_START=" + monday.isoformat() + "T00:00:00")
print("WEEK_END=" + (friday + datetime.timedelta(days=1)).isoformat() + "T00:00:00")
print("LABEL=" + monday.strftime("%b %d") + " - " + friday.strftime("%b %d, %Y"))
PY
```

## 2. Output folder

Write output into the **workspace folder** (the folder that holds your config — see **Config
location** below), in a subfolder named for the anchor Friday:

```
<WORKSPACE>/<FRIDAY>/            e.g.  515 weekly reports/2026-07-17/
```

By default `WORKSPACE` is the folder that contains the `.weekly-515-reporting/config.md` you
resolved in Config location — i.e. reports land right next to your config, in whatever folder you
connected. **Only** if the config sets `OUTPUT_ROOT` explicitly do you write there instead. This
keeps output on a real, persistent path with no hardcoded drive letters, so it works the same on
Windows, macOS, and a Cowork sandbox.

Use the Write tool to create files there — it creates the dated subfolder automatically if it
does not exist. (In a Cowork sandbox the shell sees this folder under `$HOME/mnt/<name>/` while your
file tools address the same folder by its real machine path; use whichever matches the tool you're
calling — the harness maps between them.) Each collector skill writes exactly one file named after
itself (`chat-summary.md`, `email-summary.md`, `calendar-summary.md`, `notes-summary.md`,
`git-summary.md`). The roll-up writes `proposed 515 accomplishments.md` into the same folder.

## 2b. Config location (persistent, portable across Windows / macOS / Cowork)

All person-specific values (`SLACK_URL`, `JIRA_SITE`, `JIRA_EMAIL`, `JIRA_JQL`, `NOTES_LOCATION`,
`NOTES_URL`, `AIRTABLE_515_URL`, and optionally `OUTPUT_ROOT`) live in **one** file inside a folder
you control:

```
<WORKSPACE>/.weekly-515-reporting/config.md
```

Secrets live in a **separate** file in the same folder, so the config stays safe to share or paste:

```
<WORKSPACE>/.weekly-515-reporting/credentials.md      # JIRA_API_TOKEN
```

`<WORKSPACE>` is a folder you own and connect to Cowork — e.g. your "515 weekly reports" folder.
The config lives **inside** that folder (never inside the plugin dir, which is a cache wiped on
every marketplace update). Because it rides in a connected/workspace folder, it persists across
plugin updates **and** across Cowork sessions (the sandbox's own `$HOME` is ephemeral and is wiped
each session — do not store config there).

**Locating the config — try these in order** (run in the shell; quoting handles spaces in names):

```bash
CONFIG=""
for c in \
  "$HOME"/mnt/*/.weekly-515-reporting/config.md \
  "$PWD"/.weekly-515-reporting/config.md \
  "$HOME"/.weekly-515-reporting/config.md ; do
  [ -f "$c" ] && CONFIG="$c" && break
done
if [ -n "$CONFIG" ]; then
  echo "CONFIG=$CONFIG"
  echo "WORKSPACE=$(dirname "$(dirname "$CONFIG")")"   # default OUTPUT_ROOT
else
  echo "CONFIG=<none — run first-run setup>"
fi
```

- `$HOME/mnt/*/…` is where Cowork mounts **connected folders** (the durable location).
- `$PWD/…` covers running inside your project folder in Claude Code.
- `$HOME/.weekly-515-reporting/…` is a last-resort fallback for a plain local home-dir setup.

Read the config with your **file tools** (they resolve the real machine path). `WORKSPACE` (the
parent of `.weekly-515-reporting`) is the default output folder unless `OUTPUT_ROOT` is set.

**First-run setup (no config found anywhere):**
1. If a folder is connected (something appears under `$HOME/mnt/`), ask the user **which connected
   folder** to use for their 515 config and reports.
2. If **nothing** is connected, tell the user to connect a folder to this Cowork session first (the
   agent cannot connect a folder itself — it's a user action in the Cowork UI), then continue.
3. Create `<chosen folder>/.weekly-515-reporting/config.md` from the template
   `${CLAUDE_PLUGIN_ROOT}/shared/config.example.md`, prompt for the user's real values, and write it.
   It will be found automatically on every later run.

## 2c. Source availability (every collector is optional)

Nobody has to set up every source — people use different tools. Before running the full workflow
(`run-weekly-515`), work out which collectors have what they need and tell the user, as two short
lists, so they always know what ran this week and what they could add:

| Source (skill) | Needs | Where |
|---|---|---|
| Slack (`chat-summary`) | **nothing required** — always writes its paste stub; `SLACK_URL` is just an optional convenience hint. Skipped only if the user says they don't use Slack | `config.md` (optional) |
| Personal notes (`notes-summary`) | **nothing required** — always writes its paste stub; `NOTES_LOCATION`/`NOTES_URL` are just optional hints. Skipped only if the user says they don't keep separate notes | `config.md` (optional) |
| GitHub (`git-summary`) | `GITHUB_TOKEN` | `credentials.md` |
| Azure DevOps (`azure-git-summary`) | `AZURE_DEVOPS_ORG_URL` + `AZURE_DEVOPS_PAT` | `config.md` + `credentials.md` |
| Jira (`jira-summary`) | `JIRA_EMAIL` + `JIRA_API_TOKEN` — **not** `JIRA_SITE`, which ships pre-filled with the org's shared Atlassian host and so isn't a useful signal of opt-in on its own | `config.md` + `credentials.md` |
| Outlook mail (`email-summary`) | Microsoft 365 connector authorized — works in Cowork; **no** Claude Code surface has it (confirmed: not the VS Code/JetBrains extensions, not the desktop app's own Code surface either) | Cowork/Claude connector settings |
| Outlook calendar (`calendar-summary`) | Microsoft 365 connector authorized — same caveat as above | Cowork/Claude connector settings |
| Claude Code / Cowork (`claude-summary`) | nothing to configure, but the Claude Code surface only finds data when *this run itself* is a genuine Claude Code session (CLI, VS Code/JetBrains extension, or the desktop app's Code surface) — not Cowork, whose sandboxed home directory hides the real `~/.claude/projects/` | — |
| FY goals (`goals-summary`) | `AIRTABLE_GOALS_URL` | `config.md` |
| 515 format (`weekly-515-rollup`) | `AIRTABLE_515_URL` — **required, not optional**; there's no 515 format to draft into without it | `config.md` |

**How to check, without ever touching `credentials.md` directly:**

- **`config.md` keys** (`JIRA_EMAIL`, `AZURE_DEVOPS_ORG_URL`, `AIRTABLE_GOALS_URL`,
  `AIRTABLE_515_URL`) hold no secrets, so grepping that file for **key presence only — never
  print a value** (`^KEY *=`, never echo the matched line) is fine. `SLACK_URL`,
  `NOTES_LOCATION`/`NOTES_URL`, and `JIRA_SITE` don't need checking at all for this purpose — none
  of them gate whether their collector runs (see the table above).
- **`credentials.md` keys** (`JIRA_API_TOKEN`, `GITHUB_TOKEN`, `AZURE_DEVOPS_PAT`,
  `AIRTABLE_API_KEY`) are different: **never Read, grep, `cat`, or otherwise open
  `credentials.md` with any tool, even just to check whether a key exists.** That file holds live
  secrets, and feeding them — or even confirming their presence by touching the file directly —
  into an AI tool's context is exactly what this plugin's credentials policy exists to prevent.
  Determine whether a credentials.md-gated source is configured by running **that source's own
  fetch script with `--check`** instead (`jira_fetch.py --check`, `github_fetch.py --check`,
  `azure_devops_fetch.py --check`, `airtable_fetch.py --check`) and reading only **its stdout/
  stderr** — the script resolves the secret internally and reports success/failure (and, for a
  real misconfiguration, which fix to apply) without ever printing the value, and without you
  opening the file yourself. Treat a `--check` failure as "not configured" for this list; relay
  its actual error text if the user asks why, rather than inspecting the file to find out.
- **Microsoft 365** (`email-summary`/`calendar-summary`) isn't file-based at all — just note
  whether the connector tools are callable.

Report the result before running anything, e.g.:

```
Configured this run: Jira, GitHub, Outlook mail, Outlook calendar, Claude Code
Not set up (skipped — add to config.md / credentials.md to enable): Azure DevOps, FY goals
Always included (paste-based, say so if you don't use these): Slack, personal notes
```

Then **skip calling a collector entirely when its source isn't configured** — don't invoke it and
let it fail. Note it as "not set up" in the same breath you'd otherwise report "no activity this
week," since those are different claims: one is a choice, the other is a finding. **Slack and
personal notes are the exception to this config-gated model** — they always run (writing a
paste stub) regardless of config, and are skipped only when the user explicitly says they don't
use that source, not because a key is missing.

## 3. Output file convention

Start every collector file with a small header so the roll-up can orient itself:

```markdown
# <Skill title> — week of <LABEL>
_Source: <what was searched>. Generated <timestamp>._
```

Then the summarized content. Keep it factual and specific: dates, names, decisions, numbers,
and anything that reads like an accomplishment, a decision, or a blocker — that is what the
roll-up needs. Note gaps honestly (e.g. "no GitHub activity found this week") rather than
inventing content.
