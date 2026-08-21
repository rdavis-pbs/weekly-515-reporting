# Weekly run playbook

The standing procedure for Robert's Friday 515 run. Read **this** first, then only the SKILL.md
files for the steps you actually execute — the point of this file is that you don't have to
re-derive the workflow from nine skills every week.

`run-weekly-515` is the generic orchestrator. This playbook is the local reality it runs into:
two of its eight collectors can't execute at PBS, and one source isn't used at all. Everything
below is date-agnostic — substitute the `<FRIDAY>`, `<MONDAY>`, `<LABEL>` you compute in step 1.

---

## Standing deviations from `run-weekly-515`

| Deviation | Why |
|---|---|
| **Teams is not a source.** Never collect it, never list it as a gap. | Robert doesn't use Teams. Before this was settled, two consecutive runs spent their time on Graph `chat_message_search` and then reported "0 of 38 chats, HTTP 429" as a coverage hole — a gap that was never real. |
| **Slack and OneNote are user-pasted stubs, not collector output.** Write a labeled stub, then **stop** — see the checkpoint below. | Both skills read through Claude in Chrome, which PBS has disabled outright. There is no API path for either. |
| **For Slack, name the saved skill — don't compose a prompt.** Robert maintains a Slack skill called **"Weekly Activity Summary"**; he runs it and pastes the output. | He set it up so he doesn't have to be handed a fresh prompt every week. A hand-built prompt would also drift from the one he actually maintains. |
| **Hard checkpoint before the roll-up.** Do not run `weekly-515-rollup` in the same turn as the collectors. | Slack and OneNote are consistently two of the richest sources. Drafting before they're populated produces a draft that gets thrown away. |
| **`claude-summary` runs the Claude Code surface only.** Mark claude.ai and Cowork as "not collected — treat as unknown rather than empty." | claude.ai needs the disabled browser; Cowork keeps no on-disk task history to read. Note them explicitly — never drop them silently, and never write them up as "no activity." |
| **Use `python`, never `python3`.** | On this Windows box `python3` is a Microsoft Store stub that prints "Python was not found" and exits 0. That is *not* an empty result. |

Everything else follows the stock skills unchanged.

---

## Preflight (ten seconds, saves a wasted run)

1. **Token expiry.** Check `JIRA_API_TOKEN_EXPIRES` in `.weekly-515-reporting/credentials.md` is
   still in the future. A token that lapsed mid-week cost the 8/14/2026 run its entire Jira
   coverage. `AIRTABLE_API_KEY_EXPIRES` is optional and may be absent.
2. **Config completeness.** `config.md` should carry `SLACK_URL`, `JIRA_SITE`, `JIRA_EMAIL`,
   `JIRA_JQL`, `ONENOTE_URL`, `AIRTABLE_515_URL`, `AIRTABLE_GOALS_URL`, `OUTPUT_ROOT`. List the
   keys with a grep for `^[A-Z_]* *=` — **don't** echo the values into the transcript.
3. **Already-run collectors.** `ls <FRIDAY>/` first. Robert sometimes runs `goals-summary`
   mid-week, so the three Airtable artifacts may already exist for this Friday. **Ask** whether to
   reuse or refresh — don't assume either way.

---

## Run order

Establish the week once (`shared/work-week.md` snippet → `FRIDAY`, `MONDAY`, `WEEK_START`,
`WEEK_END`, `LABEL`) and announce it. All output lands in `<FRIDAY>/`.

**Automated — run these four, from the workspace root so config discovery walks up correctly.**
They're independent; a failure in one doesn't stop the others. The two scripts can run in the
background in parallel while you do the stub and doc work.

| Skill | How | Writes |
|---|---|---|
| `jira-summary` | `python weekly-515-reporting/scripts/jira_fetch.py` | `jira-activity.json` → `jira-summary.md` |
| `git-summary` | `python weekly-515-reporting/scripts/github_fetch.py` | `github-activity.json` → `git-summary.md` |
| `email-summary` | M365 MCP `outlook_email_search`, `WEEK_START`→`WEEK_END`; **second pass** with `folderName="Sent Items"`; `read_resource` on decision-bearing threads | `email-summary.md` |
| `calendar-summary` | M365 MCP `outlook_calendar_search`, `order="oldest"`; `read_resource` per event for agenda/attendees/`meetingTranscriptUrl` | `calendar-summary.md` |

`claude-summary` — run the Step 2 transcript scan from its SKILL.md (swap in this week's dates and
`python`), then write the file with the two browser surfaces marked not-collected.

**Windows differ on purpose.** Jira is **Fri→Fri** (7 days, ending on the anchor Friday); GitHub,
email, calendar and Claude Code are **Mon–Fri**. This is deliberate — Robert's Jira reporting
period is Fri→Fri. If you ever change the anchor rule, change it in *both* `shared/work-week.md`
and `scripts/jira_fetch.py` or the Jira window and the output folder drift apart.

**Stubs — write both, then checkpoint.** Templates below.

**Checkpoint.** Report what was collected, 2–3 sentences on the week, and an explicit list of what
needs Robert. Then stop. The roll-up happens in a later turn, after he confirms the stubs are
filled.

**Roll-up (next turn).** Summarize the pasted OneNote raw notes into the file's proper sections
first, then run `weekly-515-rollup` over everything in `<FRIDAY>/`.

---

## Stub templates

Both must be *obviously* unpopulated, so a later roll-up can't mistake an empty stub for a quiet
week. Fill in `<LABEL>`, the real dates, and `SLACK_URL` from config.

### `<FRIDAY>/chat-summary.md`

```markdown
# Chat summary — week of <LABEL>
_Source: Slack via the **Weekly Activity Summary** skill — **awaiting manual paste** (Claude in Chrome is disabled at PBS,
so the workspace can't be read directly). Teams is not a source. Generated <TODAY>._

## Status: AWAITING INPUT — paste your Slack recap below

Open <SLACK_URL> and run your saved **Weekly Activity Summary** skill, then paste the reply into the
block below. **A raw paste is fine** — no cleanup needed; the roll-up reads Slack's own formatting.

## Slack

<!-- PASTE SLACKBOT RECAP HERE -->

## Teams

Not a source — Robert doesn't use Teams. Excluded by preference, **not** a gap in coverage.
```

### `<FRIDAY>/onenote-summary.md`

```markdown
# OneNote summary — week of <LABEL>
_Source: journal notes **awaiting manual paste** (Claude in Chrome is disabled at PBS, so the
notebook can't be read directly). Generated <TODAY>._

## Status: AWAITING INPUT — paste your journal notes below

Where to look:
- **BI Tech Group → Journal 2026** — the main journal, start here.
- **Projects Experiments** — per-person / per-project pages with dated entries.
- Skip anything under **Archive**. **Never open the `Credentials` page.**
- Dates live *inside* page bodies, not in titles, written `m/d/yy` with no leading zeros. Search
  each date **wrapped in double quotes** (`"<M/D/YY>"`), and run the search **per section** —
  OneNote search is scoped to one section at a time.

## Raw notes as supplied

(a fenced code block containing one `<M/D/YY>:` heading per working day, blank underneath)
```

On the next turn, summarize the pasted notes into **Accomplishments & progress / Decisions /
Ideas & proposals / Open items & blockers**, and keep the raw text at the bottom under
`## Raw notes as supplied`. That's the shape the 8/14/2026 file settled on and it worked well —
the raw block is what makes the summary auditable.

---

## Roll-up rules drafts keep violating

From `weekly-515-rollup/SKILL.md`, repeated here because these are the ones that come back:

- **1–2 sentences per item.** Write high, not deep. No SQL, no pipeline diagrams, no field-by-field
  specs.
- **No ticket IDs in the body** (Jira, CAB, TR, AIR…). They belong in the footer only.
- **~1 Goal per accomplishment.** Drafts have historically assigned about twice what the saved
  Airtable records carry, and Robert has to undo the excess by hand.
- **Center Robert's own actions.** Cut commentary about what other people did or how they reacted.
- **Match status to reality** — don't write in-progress work as done.
- **Don't filter the goals list by `Status`.** Most upcoming rows have a blank status while nearly
  every row carrying one is already overdue, so a `Status in (To Do, In Progress)` filter returns
  nothing and reads as "no upcoming work."
- **Local draft only.** Nothing is ever written to Airtable.

---

## Verification

1. `ls <FRIDAY>/` — expect `jira-summary.md` + `jira-activity.json`, `git-summary.md` +
   `github-activity.json`, `email-summary.md`, `calendar-summary.md`, `claude-summary.md`, the two
   stubs, and the three Airtable/goals artifacts. Compare against the previous week's folder.
2. Confirm the window inside `jira-activity.json` is Fri→Fri and GitHub's is Mon–Fri.
3. Every `*-summary.md` opens with `# … — week of <LABEL>` and an italic `_Source: …_` line.
4. Both stubs still say `AWAITING INPUT`, and nothing in the folder claims missing Teams coverage.
5. After the roll-up: `proposed 515 accomplishments.md` mirrors the field structure in
   `<FRIDAY>/airtable-515-records.json` — Month and Year, Week Ending Date, User, numbered
   Accomplishment / Goals / Highlight blocks, Next Week's Priorities, Challenges and Opportunities,
   Other Goals and Activities, then the assumptions / gaps / sources footer.

---

## A note on scope

This playbook records **Robert's** environment. A colleague running the plugin should start from
[COLLEAGUE-SETUP.md](COLLEAGUE-SETUP.md) instead — the Teams removal and the Chrome-disabled
workarounds here are local facts, not plugin design. Background on how the plugin got this way is
in [PROJECT-NOTES.md](PROJECT-NOTES.md).
