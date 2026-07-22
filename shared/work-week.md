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

Write output into the connected **"515 weekly reports"** project folder, in a subfolder named
for the anchor Friday:

```
515 weekly reports/<FRIDAY>/            e.g.  515 weekly reports/2026-07-17/
```

The root folder is set as `OUTPUT_ROOT` in the plugin's config file (see **Config location** below).
The full path is:

```
<OUTPUT_ROOT>\<FRIDAY>\      e.g.  <OUTPUT_ROOT>\2026-07-17\
```

Use the Write tool to create files there — it creates the dated subfolder automatically if it
does not exist. Each collector skill writes exactly one file named after itself
(`chat-summary.md`, `email-summary.md`, `calendar-summary.md`, `onenote-summary.md`,
`git-summary.md`). The roll-up writes `proposed 515 accomplishments.md` into the same folder.

## 2b. Config location (persistent — survives plugin updates)

All person/machine-specific values (`SLACK_URL`, `JIRA_FILTER_URL`, `ONENOTE_URL`,
`AIRTABLE_515_URL`, `OUTPUT_ROOT`) live in **one** file:

```
~/.weekly-515-reporting/config.md      (i.e. config.md in a .weekly-515-reporting folder in your home directory)
```

This path is deliberately **outside** the plugin's own folder. The plugin dir
(`${CLAUDE_PLUGIN_ROOT}`) is a cache that gets replaced whenever the plugin auto-updates from its
marketplace, so anything stored there is lost on update. The home-directory path is stable and
survives updates, and it does not depend on `OUTPUT_ROOT` (so there's no bootstrap chicken-and-egg).

If `~/.weekly-515-reporting/config.md` does not exist yet, create the `~/.weekly-515-reporting`
folder, copy the template `${CLAUDE_PLUGIN_ROOT}/shared/config.example.md` into it as `config.md`,
then fill in the user's real values. Every skill reads its keys from this one file.

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
