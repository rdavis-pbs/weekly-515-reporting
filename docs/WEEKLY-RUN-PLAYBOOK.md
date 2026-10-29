# Weekly run playbook

The standing procedure for Robert's Friday 515 run. Read **this** first, then only the SKILL.md
files for the steps you actually execute — the point of this file is that you don't have to
re-derive the workflow from nine skills every week.

`run-weekly-515` is the generic orchestrator, and as of v0.13.0 its defaults already cover most of
what used to be recorded here as a local deviation: every collector is optional and the orchestrator
reports what's configured before it runs anything (`shared/work-week.md` §2c), and `chat-summary` /
`notes-summary` default to a manual-paste stub with a hard checkpoint before the roll-up, since
Claude in Chrome is disabled **org-wide** at PBS, not just on this machine. What's left below is
genuinely **Robert-specific**: preferences and local facts the generic skills can't know on their
own. Everything else below is date-agnostic — substitute the `<FRIDAY>`, `<MONDAY>`, `<LABEL>` you
compute in step 1.

> **Resolved, not an open question: Robert runs this workflow from Claude Code (the VS Code
> extension), not Cowork.** He switched as of 2026-10-02 — originally for an unrelated reason
> (Cowork's plugin resync lagged behind his newer local plugin version, see `PROJECT-NOTES.md`),
> but the side effect is favorable here: Claude Code writes transcripts to the real machine's home
> directory, so `claude-summary`'s Claude Code surface genuinely finds his real
> `~/.claude/projects/` history when run this way. The tradeoff he's accepted in exchange: **the
> VS Code extension has no Microsoft 365 connector surface at all** (confirmed 2026-10-02 — M365
> shows connected in Claude Desktop, but the extension's settings have no Connectors UI), so
> `email-summary`/`calendar-summary` can't make their M365 calls from inside this same session. He
> bridges those two the same way as Slack and personal notes: run them from Cowork/Claude Desktop
> separately, then paste the result into `email-summary.md`/`calendar-summary.md`. See the
> deviations table and Run order below.

---

## Standing deviations from `run-weekly-515`

| Deviation | Why |
|---|---|
| **Teams is not a source.** Never collect it, never list it as a gap. | Robert doesn't use Teams. Before this was settled, two consecutive runs spent their time on Graph `chat_message_search` and then reported "0 of 38 chats, HTTP 429" as a coverage hole — a gap that was never real. |
| **For Slack, name the saved skill — don't compose a prompt.** Robert maintains a Slack skill called **"Weekly Activity Summary"**; he runs it and pastes the output. | He set it up so he doesn't have to be handed a fresh prompt every week. A hand-built prompt would also drift from the one he actually maintains. (`chat-summary`'s SKILL.md already prefers this; recorded here too since it's the kind of personal fact this file exists for.) |
| **For personal notes, prompt toward OneNote specifically** — see "Where Robert's notes live" below — rather than asking a fully generic "where do you keep notes?" question. | Robert's actual note-taking tool, kept here as a `NOTES_LOCATION`-equivalent since it's detailed enough that it's easier to read here than type into `config.md` every time. |
| **`claude-summary`'s Cowork surface has nothing to read on this machine.** Mark it "not collected — treat as unknown rather than empty," same treatment as claude.ai. | Cowork keeps no on-disk task history to read here. Note it explicitly — never drop it silently, and never write it up as "no activity." |
| **`email-summary` and `calendar-summary` are user-pasted stubs too, like Slack and notes.** Run them from Cowork/Claude Desktop separately, then paste the result in — don't attempt `outlook_email_search`/`outlook_calendar_search` directly in this turn. | This run happens from the Claude Code VS Code extension (see above), which has no Microsoft 365 Connectors UI at all — confirmed 2026-10-02, not a policy change or revoked auth, just a surface gap. Re-check if VS Code-extension connector support ever ships. |
| **Use `python`, never `python3`.** | On this Windows box `python3` is a Microsoft Store stub that prints "Python was not found" and exits 0. That is *not* an empty result. |

Everything else follows the stock skills unchanged — including the manual-paste default for Slack
and personal notes, and the checkpoint before the roll-up, which are now baked into those skills
directly rather than recorded here as a deviation.

---

## Preflight (ten seconds, saves a wasted run)

1. **Token expiry — never by opening `credentials.md`.** Run
   `python weekly-515-reporting/scripts/jira_fetch.py --check` and read *its* stdout: `_common.py`
   already reads `JIRA_API_TOKEN_EXPIRES` internally and prints its own `WARNING: ... expires in N
   day(s)` note when it's close, without you ever opening the file. A token that lapsed mid-week
   cost the 8/14/2026 run its entire Jira coverage — this is the check that would have caught it.
   There's no `AIRTABLE_API_KEY_EXPIRES` to worry about — that token was created with "No
   expiration," deliberately, so it's not on a rotation schedule the way Jira/GitHub tokens are.
2. **Config completeness.** `config.md` should carry `JIRA_EMAIL`, `AIRTABLE_515_URL`,
   `AIRTABLE_GOALS_URL`, `OUTPUT_ROOT` — `JIRA_SITE` and `JIRA_JQL` ship pre-filled by default and
   don't need checking, and `SLACK_URL` was never required (Slack's stub always gets written
   regardless). List the keys with a grep for `^[A-Z_]* *=` — **don't** echo the values into the
   transcript. `NOTES_LOCATION`/`NOTES_URL` are deliberately unset — see "Where Robert's notes
   live" below instead; the notes stub gets written either way. `AZURE_DEVOPS_ORG_URL`
   is not yet set, so `azure-git-summary` is skipped — that's expected until it's added, not a
   failure to flag. This whole check is just the generic "Source availability" step
   (`shared/work-week.md` §2c) with Robert's own current state as the example.
3. **Already-run collectors.** `ls <FRIDAY>/` first. Robert sometimes runs `goals-summary`
   mid-week, so the three Airtable artifacts may already exist for this Friday. **Ask** whether to
   reuse or refresh — don't assume either way.

---

## Run order

Establish the week once (`shared/work-week.md` snippet → `FRIDAY`, `MONDAY`, `WEEK_START`,
`WEEK_END`, `LABEL`) and announce it. All output lands in `<FRIDAY>/`.

**Automated — run these three, from the workspace root so config discovery walks up correctly.**
They're independent; a failure in one doesn't stop the others.

| Skill | How | Writes |
|---|---|---|
| `jira-summary` | `python weekly-515-reporting/scripts/jira_fetch.py` | `jira-activity.json` → `jira-summary.md` |
| `git-summary` | `python weekly-515-reporting/scripts/github_fetch.py` | `github-activity.json` → `git-summary.md` |
| `azure-git-summary` *(only once `AZURE_DEVOPS_ORG_URL` is set — see preflight)* | `python weekly-515-reporting/scripts/azure_devops_fetch.py` | `azure-git-activity.json` → `azure-git-summary.md` |

`claude-summary` — run the Step 2 transcript scan from its SKILL.md (swap in this week's dates and
`python`); this run is itself a Claude Code session, so the scan genuinely finds Robert's real
history. Write the file with claude.ai and Cowork both marked not-collected (see the deviations
table above for why).

`email-summary` and `calendar-summary` — **paste-only here**, same as Slack and notes: this
session has no M365 Connectors UI to call `outlook_email_search`/`outlook_calendar_search`
directly (see the resolved note above). Ask Robert to run those from Cowork/Claude Desktop for the
week and paste the results in; write their stubs the same way as the chat-summary/notes-summary
templates.

**Windows differ on purpose.** Jira is **Fri→Fri** (7 days, ending on the anchor Friday); GitHub,
Azure DevOps, email, calendar and Claude Code are **Mon–Fri**. This is deliberate — Robert's Jira reporting
period is Fri→Fri. If you ever change the anchor rule, change it in *both* `shared/work-week.md`
and `scripts/jira_fetch.py` or the Jira window and the output folder drift apart.

**Stubs — write all four, then checkpoint.** `chat-summary` and `notes-summary` each write their
own `AWAITING INPUT` stub per their SKILL.md — no need to reproduce the templates here, they're the
generic default now. For the notes prompt specifically, point Robert at his real OneNote structure
rather than asking a generic "where do you keep notes" question — see below. `email-summary` and
`calendar-summary` need an equivalent hand-written stub (same `Status: AWAITING INPUT` shape,
noting the M365-connector-unavailable-from-this-session reason) since their own SKILL.md files
don't define one yet — they assume the connector is always reachable.

**Checkpoint.** Report what was collected, 2–3 sentences on the week, and an explicit list of what
needs Robert — now **four** pastes (Slack, notes, email, calendar), not two. Then stop. The
roll-up happens in a later turn, after he confirms the stubs are filled. (The chat/notes half of
this is `run-weekly-515`'s own Step 4 now, not a local deviation; email/calendar's paste need is
Robert-specific, from running this via Claude Code — repeated here only because it's the step most
likely to get skipped by accident.)

**Roll-up (next turn).** Summarize the pasted notes raw text, and the pasted email/calendar
material, into each file's proper sections first, then run `weekly-515-rollup` over everything in
`<FRIDAY>/`.

---

## Where Robert's notes live (for the `notes-summary` paste prompt)

`notes-summary` is tool-agnostic and just asks where personal notes live. For Robert, that's
**OneNote**, with a structure specific enough to repeat here instead of making him explain it every
week — use this to steer the paste request, and to navigate directly if Claude in Chrome is ever
re-enabled:

- **BI Tech Group → Journal 2026** — the main journal, start here.
- **Projects Experiments** — per-person / per-project pages with dated entries.
- Skip anything under **Archive**. **Never open the `Credentials` page.**
- Dates live *inside* page bodies, not in titles, written `m/d/yy` with no leading zeros. Search
  each date **wrapped in double quotes** (`"<M/D/YY>"`), and run the search **per section** —
  OneNote search is scoped to one section at a time.

When Robert pastes, the raw text should come back shaped as one `<M/D/YY>:` heading per working day
with his notes underneath. On the next turn, summarize it into **Accomplishments & progress /
Decisions / Ideas & proposals / Open items & blockers**, and keep the raw text at the bottom under
`## Raw notes as supplied`. That's the shape the 8/14/2026 file settled on and it worked well — the
raw block is what makes the summary auditable.

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
   `github-activity.json`, `claude-summary.md`, all **four** stubs (`chat-summary.md`,
   `notes-summary.md`, `email-summary.md`, `calendar-summary.md`), and the three Airtable/goals
   artifacts (plus `azure-git-summary.md` + `azure-git-activity.json` once `AZURE_DEVOPS_ORG_URL`
   is configured). Compare against the previous week's folder.
2. Confirm the window inside `jira-activity.json` is Fri→Fri and GitHub's (and Azure DevOps', once
   configured) is Mon–Fri.
3. Every `*-summary.md` opens with `# … — week of <LABEL>` and an italic `_Source: …_` line.
4. All four stubs still say `AWAITING INPUT`, and nothing in the folder claims missing Teams
   coverage.
5. After the roll-up: `proposed 515 accomplishments.md` mirrors the field structure in
   `<FRIDAY>/airtable-515-records.json` — Month and Year, Week Ending Date, User, numbered
   Accomplishment / Goals / Highlight blocks, Next Week's Priorities, Challenges and Opportunities,
   Other Goals and Activities, then the assumptions / gaps / sources footer.

---

## A note on scope

This playbook records **Robert's** environment. A colleague running the plugin should start from
[COLLEAGUE-SETUP.md](COLLEAGUE-SETUP.md) instead — the Teams removal, the named Slack skill,
Robert's own OneNote structure, and running this specific instance from the **Claude Code VS Code
extension rather than Cowork** (with the email/calendar paste-bridge that comes with it) are all
local facts here, not plugin design. A colleague running from Cowork instead gets the Microsoft
365 connector automatically but loses the Claude Code surface of `claude-summary` — see
`COLLEAGUE-SETUP.md`'s note on that tradeoff. The Chrome-disabled manual-paste behavior and the
"every source is optional" reporting, by contrast, **are** plugin design now (as of v0.13.0) — they
apply to every colleague at PBS and are documented in the SKILL.md files themselves, not just here.
Background on how the plugin got this way is in [PROJECT-NOTES.md](PROJECT-NOTES.md).
