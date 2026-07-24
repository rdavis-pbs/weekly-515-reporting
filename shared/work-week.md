# Shared: target work week and output folder

Every skill in this plugin writes into the **same** dated folder so the roll-up can find all
the pieces. Use this exact logic so the collectors always agree on the folder name.

## 1. Determine the target work week (Mon–Fri)

The target week is anchored to a Friday:

- If **today is Monday–Friday**, use **this** week (this Monday through this Friday).
- If **today is Saturday or Sunday**, use the week that just finished (the previous Mon–Fri).

Run this to get the anchor Friday date as `YYYY-MM-DD`. It also prints the Monday and the
ISO start/end timestamps you can hand to search tools:

```bash
python3 - <<'PY'
import datetime
today = datetime.date.today()
wd = today.weekday()            # Mon=0 ... Sun=6
monday = today - datetime.timedelta(days=wd)   # weekend falls back to the week just ended
friday = monday + datetime.timedelta(days=4)
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
itself (`chat-summary.md`, `email-summary.md`, `calendar-summary.md`, `onenote-summary.md`,
`git-summary.md`). The roll-up writes `proposed 515 accomplishments.md` into the same folder.

## 2b. Config location (persistent, portable across Windows / macOS / Cowork)

All person-specific values (`SLACK_URL`, `JIRA_FILTER_URL`, `ONENOTE_URL`, `AIRTABLE_515_URL`, and
optionally `OUTPUT_ROOT`) live in **one** file inside a folder you control:

```
<WORKSPACE>/.weekly-515-reporting/config.md
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
