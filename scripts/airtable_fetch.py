#!/usr/bin/env python
"""
Fetch the user's Airtable inputs for the weekly 515 via the Airtable REST API.

Replaces the connector/browser-based Airtable reads for the weekly-515-rollup skill. Stdlib only --
no pip installs. Works with `python` or `python3`.

Two independent sources, each written to its own artifact:

  515   (AIRTABLE_515_URL)   -> <FRIDAY>/airtable-515-records.json
        The user's recent 515 records plus the table SCHEMA -- field names, types, and the valid
        choices for single/multi-selects. The choices matter: the draft has to pick real option
        values (e.g. the Goals list), and guessing them means fixing every one by hand on paste.

  goals (AIRTABLE_GOALS_URL) -> <FRIDAY>/airtable-goals.json
        The user's committed FY tasks, ordered by urgency, so the roll-up can write Next Week's
        Priorities from what is actually on the hook rather than inferring it from chatter.

        Selection is by DATE and completion, deliberately not by status. In the real table most
        near-term rows have a BLANK status while every row that carries one is already overdue, so
        filtering on `Status in (To Do, In Progress)` returns nothing and reads as "no upcoming
        work" -- a silent wrong answer. Anything not Done/Delivered/Cancelled is treated as
        committed, and the value added here is ordering, not filtering.

STRICTLY READ-ONLY: only GETs. It never creates, updates, or deletes an Airtable record, and the
token it asks for does not need write scope.

Usage:
  python airtable_fetch.py                     # both sources
  python airtable_fetch.py --check             # verify auth and reachability only, write nothing
  python airtable_fetch.py --source goals      # just the FY goals/tasks
  python airtable_fetch.py --records 8         # sample more 515 records to learn the format
  python airtable_fetch.py --end 2026-08-14    # write into a specific week's folder
"""

import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c                                                          # noqa: E402

# Long-text 515 answers are the whole point of the sample -- the skill is learning length and tone
# from them -- so clip generously, and only to stop one pathological record blowing up the artifact.
MAX_CELL_CHARS = 3000

DEFAULT_RECORDS = 4

# Local-sort fallback only: how many records to page through when the API can't sort for us
# (no schema access => no field name to sort on). Keeps a big shared team table bounded.
LOCAL_SORT_SCAN_CAP = 1000

# How many distinct linked records to resolve to display names. A person-link field holds one or two
# per record; this only bounds a link field pointing at something large.
LINK_RESOLVE_CAP = 100

# Resolved link names are display labels, not content. In a self-referencing link (a task's
# predecessor is another task) the "name" is that task's whole description, so cap it.
LINK_NAME_CLIP = 150

# Only these statuses mean "no longer on the hook". Everything else -- including blank -- counts as
# committed. See the module docstring: blank is the normal state for upcoming work in this table.
GOALS_DONE_STATUSES = ("done", "delivered", "cancelled", "canceled", "complete", "completed")

# Bookkeeping columns that add bulk without informing the report. `Created By` also carries a
# colleague's name and email, which has no business being copied into a weekly report artifact.
# `From field: *` is a duplicate lookup Airtable generates for a link field shown from the other
# side; `Source Row`/`Source Text` are raw leftovers from the FY26-tracker import; `Is Done` and
# `Is Countable` are internal formula flags the Airtable UI uses for its own rollups, not prose.
GOALS_SKIP_FIELDS = ("Created By", "Availability", "From field: Dependency", "Duration (with unit)",
                     "From field: Blocked By", "Source Row", "Source Text", "Is Done", "Is Countable")

TOKEN_HELP = (
    "Create a personal access token at https://airtable.com/create/tokens\n"
    "  Scopes:  data.records:read  and  schema.bases:read\n"
    "  Access:  add EVERY base you point the plugin at -- the 515 tracker (app... in\n"
    "           AIRTABLE_515_URL) and, if set, the goals base (AIRTABLE_GOALS_URL).\n"
    "A token missing a base authenticates fine but sees nothing -- Airtable returns 404 for that\n"
    "base rather than a permission error, so check Access if that happens."
)

SELECT_TYPES = ("singleSelect", "multipleSelects")
DATE_TYPES = ("date", "dateTime")


def parse_airtable_url(url, key):
    """Pull (base, table, view) ids out of an Airtable URL. View is optional.

    Airtable ids are prefix-typed (app/tbl/viw), so scanning by prefix is more robust than
    positional path splitting -- it survives the `?blocks=hide` and other query junk Airtable
    appends when you copy a URL out of the browser.
    """
    if not url:
        c.die(
            "%s is not set in your config.\n"
            "Add it as:\n  %s = https://airtable.com/appXXXX/tblYYYY/viwZZZZ\n"
            "(open the table in the browser and copy the address bar)." % (key, key)
        )

    base = re.search(r"\bapp[A-Za-z0-9]{10,}", url)
    table = re.search(r"\btbl[A-Za-z0-9]{10,}", url)
    view = re.search(r"\bviw[A-Za-z0-9]{10,}", url)

    if not base or not table:
        c.die(
            "Could not find a base id (app...) and table id (tbl...) in %s:\n  %s\n"
            "Expected something like https://airtable.com/appXXXX/tblYYYY/viwZZZZ" % (key, url)
        )
    return base.group(0), table.group(0), (view.group(0) if view else None)


class AuthError(c.ApiError):
    """An ApiError that remembers its status code, so callers can tell 401 from 403.

    The distinction decides whether a failure is fatal: 401 means the token itself is bad and
    nothing else will work, while 403/404 on the schema endpoint usually just means the token
    lacks schema.bases:read -- which we can work around.
    """

    def __init__(self, code, message):
        c.ApiError.__init__(self, message)
        self.code = code


class Airtable(c.HttpClient):
    def __init__(self, token, **kw):
        c.HttpClient.__init__(self, "https://api.airtable.com", {
            "Authorization": "Bearer %s" % token,
            "Accept": "application/json",
            "User-Agent": "weekly-515-reporting/airtable_fetch",
        }, **kw)

    def auth_error(self, code, detail):
        return AuthError(
            code,
            "Airtable rejected the token (HTTP %d). Check it hasn't expired or been revoked, and "
            "that it has the scopes and base access listed in credentials.md.\n%s\n%s"
            % (code, TOKEN_HELP, detail)
        )

    def base_schema(self, base_id):
        return self.request("/v0/meta/bases/%s/tables" % base_id)

    def records(self, base_id, table_id, view=None, sort_field=None, max_records=None):
        """Page through records. View filters/permissions are inherited; sort overrides view order."""
        out, offset = [], None
        while True:
            params = {"pageSize": 100}
            if view:
                params["view"] = view
            if sort_field:
                params["sort[0][field]"] = sort_field
                params["sort[0][direction]"] = "desc"
            if max_records:
                # maxRecords applies AFTER sorting, so with a sort field this is the cheap path:
                # Airtable returns the newest N and we never page the rest of the table.
                params["maxRecords"] = max_records
            if offset:
                params["offset"] = offset

            page = self.request("/v0/%s/%s" % (base_id, table_id), params=params)
            out.extend(page.get("records") or [])
            offset = page.get("offset")
            if not offset or (max_records and len(out) >= max_records):
                return out[:max_records] if max_records else out
            if not max_records and len(out) >= LOCAL_SORT_SCAN_CAP:
                c.note("  NOTE: stopped after %d records (scan cap); the rest of the table was not "
                       "read." % len(out))
                return out


def find_table(schema, table_id):
    for t in schema.get("tables") or []:
        if t.get("id") == table_id:
            return t
    return None


def shape_field(field):
    """Keep the parts of a field definition that constrain what a valid draft looks like."""
    out = {"name": field.get("name"), "type": field.get("type")}
    options = field.get("options") or {}
    if field.get("type") in SELECT_TYPES:
        out["choices"] = [ch.get("name") for ch in (options.get("choices") or [])]
    if field.get("type") in DATE_TYPES:
        fmt = (options.get("dateFormat") or {}).get("name")
        if fmt:
            out["date_format"] = fmt
    if field.get("description"):
        out["description"] = c.clip(field["description"], 400)
    return out


def date_sort_field(fields):
    """Pick the field to order records by: the week-ending date if there is one, else any date.

    Ordering by the *reported week* rather than by record-creation time is what makes "the most
    recent records" mean the most recent weeks -- a backfilled or re-edited record would otherwise
    jump the queue and the skill would learn the format from the wrong sample.
    """
    dates = [f for f in fields if f.get("type") in DATE_TYPES]
    if not dates:
        return None
    for pattern in (r"week.*end", r"end.*date", r"week"):
        for f in dates:
            if re.search(pattern, f.get("name") or "", re.I):
                return f["name"]
    return dates[0]["name"]


def due_date_field(fields):
    """The field that says when a task is on the hook: End, else Due/Target, else any date."""
    dates = [f for f in fields if f.get("type") in DATE_TYPES]
    if not dates:
        return None
    for pattern in (r"^end$", r"\bdue\b", r"\btarget\b", r"^end", r"finish"):
        for f in dates:
            if re.search(pattern, f.get("name") or "", re.I):
                return f["name"]
    return dates[-1]["name"]


def pick_field(fields, pattern, types=None):
    for f in fields:
        if types and f.get("type") not in types:
            continue
        if re.search(pattern, f.get("name") or "", re.I):
            return f["name"]
    return None


def load_table(at, base_id, table_id, view_id, url_key):
    """Fetch the base schema and locate one table/view. Returns a dict of what we could learn.

    The schema needs `schema.bases:read`, which a data-only token lacks -- so a failure here is
    downgraded to a warning and the caller carries on with records alone.
    """
    table, tables, schema_error = None, [], None
    try:
        schema = at.base_schema(base_id)
        tables = schema.get("tables") or []
        table = find_table(schema, table_id)
        if table is None:
            schema_error = ("table %s is not in base %s -- check %s"
                            % (table_id, base_id, url_key))
    except AuthError as e:
        # 401 = the token is bad, so the records call would fail identically. Fail once, here,
        # instead of printing a scope warning and then the same rejection a moment later.
        if e.code == 401:
            c.die(str(e))
        schema_error = str(e)
    except c.ApiError as e:
        schema_error = str(e)

    if schema_error:
        c.note("WARNING: could not read the table schema, continuing with records only.\n"
               "         %s\n"
               "         Field types and select choices will be missing; add the\n"
               "         schema.bases:read scope to the token to get them."
               % schema_error.replace("\n", "\n         "))

    fields = [shape_field(f) for f in (table.get("fields") if table else []) or []]
    view_name = None
    for v in (table.get("views") if table else []) or []:
        if v.get("id") == view_id:
            view_name = v.get("name")

    primary = None
    if table:
        primary = next((f.get("name") for f in (table.get("fields") or [])
                        if f.get("id") == table.get("primaryFieldId")), None)

    return {"table": table, "tables": tables, "schema_error": schema_error, "fields": fields,
            "field_order": [f["name"] for f in fields], "view_name": view_name,
            "primary": primary, "base": base_id, "table_id": table_id, "view": view_id}


def resolve_link_fields(at, base_id, tables, table, records):
    """Replace linked-record ids in the shaped records with the names Airtable displays.

    The REST API returns a link cell as raw record ids (`["rec123"]`) where the UI -- and the old
    connector path -- showed a person's name. Unresolved, a field like User or Assignee is unusable
    for both purposes it serves here: naming the person in the draft, and the "is this view actually
    filtered to me?" check, which would otherwise compare opaque ids.

    Returns a list of notes about anything it couldn't resolve.
    """
    notes = []
    link_fields = {f["name"]: f.get("options", {}).get("linkedTableId")
                   for f in (table.get("fields") or [])
                   if f.get("type") == "multipleRecordLinks"}
    link_fields = {k: v for k, v in link_fields.items() if v}
    if not link_fields:
        return notes

    # Group the ids we actually saw by which table they live in, so each table costs one request.
    wanted = {}
    for r in records:
        for name, linked_table_id in link_fields.items():
            for rid in (r["fields"].get(name) or []):
                if isinstance(rid, str) and rid.startswith("rec"):
                    wanted.setdefault(linked_table_id, set()).add(rid)

    resolved = {}
    for linked_table_id, ids in wanted.items():
        linked = find_table({"tables": tables}, linked_table_id)
        if linked is None:
            notes.append("Could not resolve linked records in table %s (not visible to this token)."
                         % linked_table_id)
            continue
        primary = next((f.get("name") for f in (linked.get("fields") or [])
                        if f.get("id") == linked.get("primaryFieldId")), None)
        if not primary:
            continue

        ids = sorted(ids)
        if len(ids) > LINK_RESOLVE_CAP:
            notes.append("Only the first %d linked records in %s were resolved to names."
                         % (LINK_RESOLVE_CAP, linked.get("name") or linked_table_id))
            ids = ids[:LINK_RESOLVE_CAP]

        clauses = ["RECORD_ID()='%s'" % rid for rid in ids]
        formula = clauses[0] if len(clauses) == 1 else "OR(%s)" % ",".join(clauses)
        try:
            page = at.request("/v0/%s/%s" % (base_id, linked_table_id),
                              params={"filterByFormula": formula, "pageSize": 100,
                                      "fields[]": primary})
        except c.ApiError as e:
            notes.append("Could not read names from linked table %s: %s"
                         % (linked.get("name") or linked_table_id, str(e).splitlines()[0]))
            continue
        for rec in page.get("records") or []:
            value = (rec.get("fields") or {}).get(primary)
            if isinstance(value, str) and value.strip():
                # Primary-field values carry stray newlines (a People row reads "Robert\nDavis"),
                # which would land mid-name in the report. Collapse to single spaces.
                resolved[rec["id"]] = c.clip(" ".join(value.split()), LINK_NAME_CLIP)

    if resolved:
        for r in records:
            for name in link_fields:
                v = r["fields"].get(name)
                if isinstance(v, list):
                    r["fields"][name] = [resolved.get(x, x) if isinstance(x, str) else x for x in v]
    return notes


def shape_record(record, fields_order, skip=()):
    """Flatten a record to {field: value}, in the table's own field order, clipping long text."""
    raw = record.get("fields") or {}
    values = {}

    def keep(name, v):
        if name in skip:
            return
        if isinstance(v, str):
            v = c.clip(v, MAX_CELL_CHARS)
        elif isinstance(v, list):
            v = [c.clip(x, MAX_CELL_CHARS) if isinstance(x, str) else x for x in v]
        values[name] = v

    for name in fields_order:
        if name in raw:                    # Airtable omits empty cells entirely
            keep(name, raw[name])
    # Anything the schema didn't describe (or a schema-less run) still gets through.
    for name, v in raw.items():
        if name not in values:
            keep(name, v)
    return {"id": record.get("id"), "created_time": record.get("createdTime"), "fields": values}


def infer_field_order(records):
    seen = []
    for r in records:
        for name in r["fields"]:
            if name not in seen:
                seen.append(name)
    return seen


# --------------------------------------------------------------------------- 515 source


def run_515(at, args, config, config_path, folder):
    base_id, table_id, view_id = parse_airtable_url(config.get("AIRTABLE_515_URL"),
                                                    "AIRTABLE_515_URL")
    c.note("515:    %s / %s%s" % (base_id, table_id, (" / %s" % view_id) if view_id else ""))

    meta = load_table(at, base_id, table_id, view_id, "AIRTABLE_515_URL")
    fields, fields_order = meta["fields"], meta["field_order"]
    sort_field = date_sort_field(fields)

    if args.check:
        try:
            probe = at.records(base_id, table_id, view=view_id, sort_field=sort_field, max_records=1)
        except c.ApiError as e:
            c.die(str(e))
        print("\n[515] OK: read base %s." % base_id)
        print("  Table: %s" % (meta["table"].get("name") if meta["table"]
                               else "%s (schema unavailable)" % table_id))
        if view_id:
            print("  View:  %s" % (meta["view_name"] or "%s (name unavailable)" % view_id))
        print("  Fields: %s" % (", ".join(fields_order) if fields_order else "(schema unavailable)"))
        print("  Records visible: %s" % ("at least 1" if probe else "0 -- check the view's filters "
              "and that the token has access to this base"))
        return None

    try:
        if sort_field:
            raw = at.records(base_id, table_id, view=view_id, sort_field=sort_field,
                             max_records=args.records)
        else:
            # No sortable date field known: page the view and sort locally on createdTime, which is
            # the only ordering signal available without the schema.
            c.note("  no date field to sort on; paging the view and sorting by created time")
            raw = at.records(base_id, table_id, view=view_id)
            raw.sort(key=lambda r: r.get("createdTime") or "", reverse=True)
            raw = raw[:args.records]
    except c.ApiError as e:
        c.die("Airtable read failed for the 515 table.\n%s" % e)

    records = [shape_record(r, fields_order) for r in raw]
    notes = resolve_link_fields(at, base_id, meta["tables"], meta["table"], records) \
        if meta["table"] else []
    if not fields_order:
        fields_order = infer_field_order(records)

    # A team-wide table reached through an unfiltered view returns everyone's rows. The draft would
    # then be modeled on colleagues' entries, which reads as a formatting choice rather than a bug,
    # so surface it instead of silently proceeding.
    people_field = next((n for n in fields_order
                         if re.search(r"^(user|person|name|owner|employee)", n, re.I)), None)
    people = []
    if people_field:
        for r in records:
            v = r["fields"].get(people_field)
            for name in (v if isinstance(v, list) else [v]):
                if isinstance(name, str) and name not in people:
                    people.append(name)
    if len(people) > 1:
        notes.append(
            "The sampled records span %d people (%s field: %s). This view is probably not filtered "
            "to you -- narrow the view, or point AIRTABLE_515_URL at your personal view, so the "
            "draft is modeled on your own entries."
            % (len(people), people_field, ", ".join(people)))
    if meta["schema_error"]:
        notes.append("Table schema unavailable (%s). Field types and select choices are missing; "
                     "add schema.bases:read to the token."
                     % meta["schema_error"].splitlines()[0])

    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": {"base": base_id, "table": table_id,
                   "table_name": meta["table"].get("name") if meta["table"] else None,
                   "view": view_id, "view_name": meta["view_name"],
                   "url": config.get("AIRTABLE_515_URL")},
        "access": "read-only",
        "purpose": "format sample -- the shape and voice this week's draft should match",
        "sorted_by": sort_field or "createdTime (local sort)",
        "fields": fields,
        "field_order": fields_order,
        "records": records,
        "notes": notes,
    }

    out_path = c.output_path(args.out_515, config_path, config, folder,
                             "airtable-515-records.json")
    c.write_json(out_path, payload)

    print("\n[515] Wrote %s" % out_path)
    print("  Table: %s%s" % (meta["table"].get("name") if meta["table"] else table_id,
                             ("  /  view: %s" % meta["view_name"]) if meta["view_name"] else ""))
    print("  Records: %d (newest first by %s)" % (len(records), payload["sorted_by"]))
    if fields:
        for f in fields:
            extra = ""
            if f.get("choices"):
                shown = ", ".join(f["choices"][:6])
                extra = "  [%s%s]" % (shown, ", ..." if len(f["choices"]) > 6 else "")
            print("    %-30s %-20s%s" % (f["name"], f["type"], extra))
    # Show the reported week and what it said, not whichever field happens to come first -- in this
    # table that's an autoNumber, which tells you nothing about the record.
    text_fields = [f["name"] for f in fields
                   if f.get("type") in ("multilineText", "singleLineText", "richText")] \
        or list(fields_order)
    if records:
        print("\n  Sampled records (%s):" % (sort_field or "created"))
        for r in records:
            week = r["fields"].get(sort_field) if sort_field else None
            gist = next((r["fields"][n] for n in text_fields
                         if isinstance(r["fields"].get(n), str) and r["fields"][n].strip()), "")
            print("    %-12s %s" % (str(week)[:10] if week else (r["created_time"] or "?")[:10],
                                    c.clip(gist.replace("\n", " "), 96) or r["id"]))
        if people:
            print("\n  User(s) in the sample: %s" % ", ".join(people))
    else:
        print("\n  No records returned. Check the view's filters and that the token has access to "
              "this base.")
    for n in notes:
        print("\n  NOTE: %s" % n)
    return payload


# --------------------------------------------------------------------------- goals source


def urgency_of(due_iso, anchor):
    """Bucket a due date relative to the reporting week's Friday. Returns (bucket, days_until).

    The anchor is the END of the week being reported on, so 0-7 days past it is the week *after*
    the report -- which is exactly the "Next Week's Priorities" field. Naming that bucket
    "due_this_week" would put next week's work under this week's heading.
    """
    if not due_iso:
        return "undated", None
    try:
        due = datetime.date.fromisoformat(str(due_iso)[:10])
    except ValueError:
        return "undated", None
    days = (due - anchor).days
    if days < 0:
        return "overdue", days
    if days <= 7:
        return "due_next_7d", days
    if days <= 30:
        return "due_within_30d", days
    return "later", days


BUCKET_ORDER = ("overdue", "due_next_7d", "due_within_30d", "later", "undated")


def run_goals(at, args, config, config_path, folder, anchor):
    url = config.get("AIRTABLE_GOALS_URL")
    if not url:
        # Asked for explicitly => a missing key is an error worth explaining. Part of a `both` run
        # => the 515 read still stands on its own, so note it and carry on.
        if args.source == "goals":
            c.die("AIRTABLE_GOALS_URL is not set in your config (%s).\n"
                  "Open your goals/tasks view in Airtable, copy the address bar, and add:\n"
                  "  AIRTABLE_GOALS_URL = https://airtable.com/appXXXX/tblYYYY/viwZZZZ\n"
                  "Use your own personal view, not a team-wide one." % config_path)
        c.note("goals:  AIRTABLE_GOALS_URL not set -- skipping the goals/commitments source.")
        return None

    base_id, table_id, view_id = parse_airtable_url(url, "AIRTABLE_GOALS_URL")
    c.note("goals:  %s / %s%s" % (base_id, table_id, (" / %s" % view_id) if view_id else ""))

    meta = load_table(at, base_id, table_id, view_id, "AIRTABLE_GOALS_URL")
    fields, fields_order = meta["fields"], meta["field_order"]

    due_field = due_date_field(fields)
    status_field = pick_field(fields, r"status", ("singleSelect", "singleLineText"))
    start_field = pick_field(fields, r"^start", DATE_TYPES)
    completed_field = pick_field(fields, r"completed", DATE_TYPES)
    assignee_field = pick_field(fields, r"assignee|owner|person")

    if args.check:
        try:
            probe = at.records(base_id, table_id, view=view_id, max_records=1)
        except c.ApiError as e:
            c.die(str(e))
        print("\n[goals] OK: read base %s." % base_id)
        print("  Table: %s" % (meta["table"].get("name") if meta["table"]
                               else "%s (schema unavailable)" % table_id))
        if view_id:
            print("  View:  %s" % (meta["view_name"] or "%s (name unavailable)" % view_id))
        print("  Due-date field: %s   Status field: %s" % (due_field, status_field))
        print("  Records visible: %s" % ("at least 1" if probe else "0 -- check the view's filters "
              "and that the token has access to this base"))
        return None

    try:
        raw = at.records(base_id, table_id, view=view_id)
    except c.ApiError as e:
        c.die("Airtable read failed for the goals table.\n%s" % e)

    all_records = [shape_record(r, fields_order, skip=GOALS_SKIP_FIELDS) for r in raw]
    notes = resolve_link_fields(at, base_id, meta["tables"], meta["table"], all_records) \
        if meta["table"] else []
    if not fields_order:
        fields_order = infer_field_order(all_records)
    if not due_field:
        notes.append("No due-date field found in this table, so nothing can be ordered by urgency; "
                     "every item is reported as undated.")

    # Completion is the only exclusion. Blank status is the NORMAL state for upcoming work in this
    # table, so treating a missing status as "not committed" would drop exactly the rows the report
    # needs. Count what we drop rather than dropping quietly.
    items, dropped = [], []
    for r in all_records:
        f = r["fields"]
        status = f.get(status_field) if status_field else None
        status_text = (status if isinstance(status, str) else "") or ""
        done_by_status = status_text.strip().lower() in GOALS_DONE_STATUSES
        done_by_date = bool(completed_field and f.get(completed_field))
        if done_by_status or done_by_date:
            dropped.append((r, status_text or "completed date set"))
            continue

        bucket, days = urgency_of(f.get(due_field) if due_field else None, anchor)
        items.append({
            "id": r["id"],
            "title": c.clip(str(f.get(meta["primary"]) or "").replace("\n", " "), 300)
                     if meta["primary"] else None,
            "status": status_text or None,
            "start": f.get(start_field) if start_field else None,
            "due": f.get(due_field) if due_field else None,
            "days_until_due": days,
            "urgency": bucket,
            "assignee": f.get(assignee_field) if assignee_field else None,
            "fields": f,
        })

    # Soonest first; undated last. Within a bucket, earlier due dates come first.
    items.sort(key=lambda i: (BUCKET_ORDER.index(i["urgency"]),
                              i["due"] or "9999-12-31", (i["title"] or "")))

    by_urgency = {b: sum(1 for i in items if i["urgency"] == b) for b in BUCKET_ORDER}
    by_status = {}
    for i in items:
        key = i["status"] or "(blank)"
        by_status[key] = by_status.get(key, 0) + 1

    people = []
    for i in items:
        v = i.get("assignee")
        for name in (v if isinstance(v, list) else [v]):
            if isinstance(name, str) and name not in people:
                people.append(name)
    assignee_is_link = next((f.get("type") for f in fields if f.get("name") == assignee_field),
                            None) == "multipleRecordLinks"
    if len(people) > 1 and assignee_is_link:
        # A link-type assignee field holds co-owners per record, not one owner per row, so seeing
        # several names across the view is normal shared ownership -- not evidence the view is
        # someone else's. Report it as information, not a warning to go fix the view.
        notes.append("These items are co-owned across %d people (%s), via a shared-ownership link "
                     "field -- normal for this table, not a sign the view is unfiltered."
                     % (len(people), ", ".join(people)))
    elif len(people) > 1:
        notes.append(
            "These items span %d assignees (%s). This view is probably not filtered to you -- point "
            "AIRTABLE_GOALS_URL at your personal view so the priorities are yours."
            % (len(people), ", ".join(people)))
    if status_field and by_status.get("(blank)"):
        notes.append(
            "%d of %d committed items have no status set. Selection here is by due date and "
            "completion, not status, precisely because of that -- do not read a blank status as "
            "'not started' or as missing data."
            % (by_status["(blank)"], len(items)))
    if meta["schema_error"]:
        notes.append("Table schema unavailable (%s); field detection fell back to record contents."
                     % meta["schema_error"].splitlines()[0])

    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": {"base": base_id, "table": table_id,
                   "table_name": meta["table"].get("name") if meta["table"] else None,
                   "view": view_id, "view_name": meta["view_name"], "url": url},
        "access": "read-only",
        "purpose": "committed and upcoming work -- input for Next Week's Priorities",
        "as_of": anchor.isoformat(),
        "selection": {
            "horizon": "none -- the whole remaining fiscal year",
            "excluded": "only items that are completed (status %s, or a completed date set)"
                        % "/".join(GOALS_DONE_STATUSES[:3]),
            "included_blank_status": True,
            "due_date_field": due_field,
            "status_field": status_field,
            "ordering": "urgency bucket, then due date",
        },
        "counts": {
            "in_view": len(all_records),
            "committed": len(items),
            "excluded_completed": len(dropped),
            "by_urgency": by_urgency,
            "by_status": by_status,
        },
        "fields": fields,
        "items": items,
        "notes": notes,
    }

    out_path = c.output_path(args.out_goals, config_path, config, folder, "airtable-goals.json")
    c.write_json(out_path, payload)

    print("\n[goals] Wrote %s" % out_path)
    print("  Table: %s%s" % (meta["table"].get("name") if meta["table"] else table_id,
                             ("  /  view: %s" % meta["view_name"]) if meta["view_name"] else ""))
    print("  %d in view, %d committed, %d completed/excluded  (as of %s)"
          % (len(all_records), len(items), len(dropped), anchor.isoformat()))
    print("  By urgency: %s" % ", ".join("%s=%d" % (b, by_urgency[b]) for b in BUCKET_ORDER
                                         if by_urgency[b]))
    for bucket in BUCKET_ORDER:
        rows = [i for i in items if i["urgency"] == bucket]
        if not rows:
            continue
        print("\n  %s:" % bucket.replace("_", " ").upper())
        for i in rows:
            when = i["due"][:10] if i["due"] else "no date"
            days = ("%+dd" % i["days_until_due"]) if i["days_until_due"] is not None else "    "
            print("    %-11s %-6s %-22s %s" % (when, days, c.clip(i["status"] or "(blank)", 20),
                                               c.clip(i["title"] or i["id"], 88)))
    if people:
        print("\n  Assignee(s): %s" % ", ".join(people))
    for n in notes:
        print("\n  NOTE: %s" % n)
    return payload


# --------------------------------------------------------------------------- main


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Read your 515 format sample and your committed FY work from Airtable "
                    "(read-only).")
    ap.add_argument("--config", help="path to .weekly-515-reporting/config.md (auto-discovered if omitted)")
    ap.add_argument("--source", choices=("both", "515", "goals"), default="both",
                    help="which Airtable source to read (default both)")
    ap.add_argument("--records", type=int, default=DEFAULT_RECORDS,
                    help="how many recent 515 records to sample (default %d)" % DEFAULT_RECORDS)
    ap.add_argument("--end", help="week folder to write into, YYYY-MM-DD (default: this week's Friday)")
    ap.add_argument("--out-515", help="exact output path for the 515 artifact")
    ap.add_argument("--out-goals", help="exact output path for the goals artifact")
    ap.add_argument("--check", action="store_true", help="verify auth and reachability; write nothing")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (TLS-inspecting networks)")
    ap.add_argument("--verbose", action="store_true", help="log each HTTP request to stderr")
    args = ap.parse_args(argv)

    c.force_utf8_output()
    config_path = c.find_config(args.config)
    config = c.parse_kv(config_path)
    c.note("config: %s" % config_path)

    token, token_src = c.resolve_secret("AIRTABLE_API_KEY", config_path, config, TOKEN_HELP)
    c.note("token:  %s" % token_src)
    c.warn_if_expiring("AIRTABLE_API_KEY", config_path, config, TOKEN_HELP)

    if args.end:
        try:
            anchor = datetime.date.fromisoformat(args.end)
        except ValueError as e:
            c.die("Bad --end (expected YYYY-MM-DD): %s" % e)
    else:
        anchor = c.anchor_friday(datetime.date.today())
    folder = anchor.isoformat()

    at = Airtable(token, insecure=args.insecure, verbose=args.verbose)

    wrote = 0
    if args.source in ("both", "515"):
        if run_515(at, args, config, config_path, folder) is not None:
            wrote += 1
    if args.source in ("both", "goals"):
        if run_goals(at, args, config, config_path, folder, anchor) is not None:
            wrote += 1

    if not args.check and not wrote:
        c.die("Nothing was written -- no Airtable source produced an artifact.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
