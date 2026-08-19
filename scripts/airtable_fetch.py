#!/usr/bin/env python
"""
Fetch the user's recent 515 records + the table schema from Airtable via the Airtable REST API.

Replaces the connector/browser-based Airtable read for the weekly-515-rollup skill, which needs to
know what shape a 515 record actually takes before drafting one. Stdlib only -- no pip installs.
Works with `python` or `python3`.

What it does:
  1. Resolves config (.weekly-515-reporting/config.md) and the Airtable token.
  2. Pulls base/table/view IDs out of AIRTABLE_515_URL.
  3. Reads the table SCHEMA -- field names, types, and the valid choices for single/multi-selects.
     The choices matter: the draft has to pick real option values (e.g. the Goals list), and
     guessing them means the user has to fix every one by hand on paste.
  4. Reads the most recent N records from that view, newest first, so the draft can match the
     user's own voice, length, and conventions.
  5. Writes a JSON artifact the weekly-515-rollup skill reads.

STRICTLY READ-ONLY: only GETs. It never creates, updates, or deletes an Airtable record, and the
token it asks for does not need write scope.

Usage:
  python airtable_fetch.py                    # schema + 4 most recent records
  python airtable_fetch.py --check            # verify auth and reachability only, write nothing
  python airtable_fetch.py --records 8        # look further back to learn the format
  python airtable_fetch.py --end 2026-08-14   # write into a specific week's folder
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

TOKEN_HELP = (
    "Create a personal access token at https://airtable.com/create/tokens\n"
    "  Scopes:  data.records:read  and  schema.bases:read\n"
    "  Access:  add the base your 515 tracker lives in (the app... id in AIRTABLE_515_URL).\n"
    "A token with no base added to it authenticates fine but sees nothing -- Airtable returns 404\n"
    "for the base rather than a permission error, so check Access if that happens."
)

SELECT_TYPES = ("singleSelect", "multipleSelects")


def parse_airtable_url(url):
    """Pull (base, table, view) ids out of an Airtable URL. View is optional.

    Airtable ids are prefix-typed (app/tbl/viw), so scanning by prefix is more robust than
    positional path splitting -- it survives the `?blocks=hide` and other query junk Airtable
    appends when you copy a URL out of the browser.
    """
    if not url:
        c.die(
            "AIRTABLE_515_URL is not set in your config.\n"
            "Add it as:\n  AIRTABLE_515_URL = https://airtable.com/appXXXX/tblYYYY/viwZZZZ\n"
            "(open your 515 table in the browser and copy the address bar)."
        )

    base = re.search(r"\bapp[A-Za-z0-9]{10,}", url)
    table = re.search(r"\btbl[A-Za-z0-9]{10,}", url)
    view = re.search(r"\bviw[A-Za-z0-9]{10,}", url)

    if not base or not table:
        c.die(
            "Could not find a base id (app...) and table id (tbl...) in AIRTABLE_515_URL:\n  %s\n"
            "Expected something like https://airtable.com/appXXXX/tblYYYY/viwZZZZ" % url
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
                c.note("  NOTE: stopped after %d records (scan cap) -- newest-first ordering is not "
                       "guaranteed for the remainder." % len(out))
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
    if field.get("type") == "date" or field.get("type") == "dateTime":
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
    dates = [f for f in fields if f.get("type") in ("date", "dateTime")]
    if not dates:
        return None
    for pattern in (r"week.*end", r"end.*date", r"week"):
        for f in dates:
            if re.search(pattern, f.get("name") or "", re.I):
                return f["name"]
    return dates[0]["name"]


def shape_record(record, fields_order):
    """Flatten a record to {field: value}, in the table's own field order, clipping long text."""
    raw = record.get("fields") or {}
    values = {}
    for name in fields_order:
        if name not in raw:
            continue                       # Airtable omits empty cells entirely
        v = raw[name]
        if isinstance(v, str):
            v = c.clip(v, MAX_CELL_CHARS)
        elif isinstance(v, list):
            v = [c.clip(x, MAX_CELL_CHARS) if isinstance(x, str) else x for x in v]
        values[name] = v
    # Anything the schema didn't describe (or a schema-less run) still gets through.
    for name, v in raw.items():
        if name not in values:
            values[name] = c.clip(v, MAX_CELL_CHARS) if isinstance(v, str) else v
    return {"id": record.get("id"), "created_time": record.get("createdTime"), "fields": values}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Read your recent 515 records and table schema from Airtable (read-only).")
    ap.add_argument("--config", help="path to .weekly-515-reporting/config.md (auto-discovered if omitted)")
    ap.add_argument("--records", type=int, default=DEFAULT_RECORDS,
                    help="how many recent records to fetch (default %d)" % DEFAULT_RECORDS)
    ap.add_argument("--end", help="week folder to write into, YYYY-MM-DD (default: this week's Friday)")
    ap.add_argument("--out", help="exact output JSON path (default <OUTPUT_ROOT>/<FRIDAY>/airtable-515-records.json)")
    ap.add_argument("--check", action="store_true", help="verify auth and reachability; write nothing")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (TLS-inspecting networks)")
    ap.add_argument("--verbose", action="store_true", help="log each HTTP request to stderr")
    args = ap.parse_args(argv)

    c.force_utf8_output()
    config_path = c.find_config(args.config)
    config = c.parse_kv(config_path)
    c.note("config: %s" % config_path)

    base_id, table_id, view_id = parse_airtable_url(config.get("AIRTABLE_515_URL"))
    c.note("base:   %s / %s%s" % (base_id, table_id, (" / %s" % view_id) if view_id else ""))

    token, token_src = c.resolve_secret("AIRTABLE_API_KEY", config_path, config, TOKEN_HELP)
    c.note("token:  %s" % token_src)
    c.warn_if_expiring("AIRTABLE_API_KEY", config_path, config, TOKEN_HELP)

    at = Airtable(token, insecure=args.insecure, verbose=args.verbose)

    # Schema first: it names the fields, supplies the select choices, and gives us a field to sort
    # on. It needs schema.bases:read, which a data-only token lacks -- so treat it as optional and
    # degrade to inferring the shape from the records themselves.
    table, schema_error = None, None
    try:
        table = find_table(at.base_schema(base_id), table_id)
        if table is None:
            schema_error = ("table %s is not in base %s -- check AIRTABLE_515_URL"
                            % (table_id, base_id))
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
               "         Field types and select choices (e.g. your Goals options) will be missing;\n"
               "         add the schema.bases:read scope to the token to get them."
               % schema_error.replace("\n", "\n         "))

    fields = [shape_field(f) for f in (table.get("fields") if table else []) or []]
    fields_order = [f["name"] for f in fields]
    sort_field = date_sort_field(fields)

    view_name = None
    for v in (table.get("views") if table else []) or []:
        if v.get("id") == view_id:
            view_name = v.get("name")

    if args.check:
        try:
            probe = at.records(base_id, table_id, view=view_id, sort_field=sort_field, max_records=1)
        except c.ApiError as e:
            c.die(str(e))
        print("OK: authenticated to Airtable and read base %s." % base_id)
        print("Table: %s" % (table.get("name") if table else "%s (schema unavailable)" % table_id))
        if view_id:
            print("View:  %s" % (view_name or "%s (name unavailable)" % view_id))
        print("Fields: %s" % (", ".join(fields_order) if fields_order else "(schema unavailable)"))
        print("Records visible in that view: %s" % ("at least 1" if probe else "0 -- check the "
              "view's filters and that the token has access to this base"))
        return 0

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
        c.die("Airtable read failed.\n%s" % e)

    records = [shape_record(r, fields_order) for r in raw]

    if not fields_order and records:
        seen = []
        for r in records:
            for name in r["fields"]:
                if name not in seen:
                    seen.append(name)
        fields_order = seen

    # A team-wide table reached through an unfiltered view returns everyone's rows. The draft would
    # then be modeled on colleagues' entries, which reads as a formatting choice rather than a bug,
    # so surface it instead of silently proceeding.
    people_field = next((n for n in fields_order if re.search(r"^(user|person|name|owner|employee)",
                                                              n, re.I)), None)
    people = []
    if people_field:
        for r in records:
            v = r["fields"].get(people_field)
            for name in (v if isinstance(v, list) else [v]):
                if isinstance(name, str) and name not in people:
                    people.append(name)
    notes = []
    if len(people) > 1:
        notes.append(
            "The sampled records span %d people (%s field: %s). This view is probably not filtered "
            "to you -- narrow the view, or point AIRTABLE_515_URL at your personal view, so the "
            "draft is modeled on your own entries."
            % (len(people), people_field, ", ".join(people)))
    if schema_error:
        notes.append("Table schema unavailable (%s). Field types and select choices are missing; "
                     "add schema.bases:read to the token." % schema_error.splitlines()[0])

    if args.end:
        try:
            end = datetime.date.fromisoformat(args.end)
        except ValueError as e:
            c.die("Bad --end (expected YYYY-MM-DD): %s" % e)
    else:
        end = c.anchor_friday(datetime.date.today())

    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": {"base": base_id, "table": table_id, "table_name": table.get("name") if table else None,
                   "view": view_id, "view_name": view_name,
                   "url": config.get("AIRTABLE_515_URL")},
        "access": "read-only",
        "sorted_by": sort_field or "createdTime (local sort)",
        "fields": fields,
        "field_order": fields_order,
        "records": records,
        "notes": notes,
    }

    out_path = c.output_path(args.out, config_path, config, end.isoformat(),
                             "airtable-515-records.json")
    c.write_json(out_path, payload)

    print("Wrote %s" % out_path)
    print("Table: %s%s" % (table.get("name") if table else table_id,
                           ("  /  view: %s" % view_name) if view_name else ""))
    print("Records: %d (newest first by %s)" % (len(records), payload["sorted_by"]))
    if fields:
        print("\nFields:")
        for f in fields:
            extra = ""
            if f.get("choices"):
                shown = ", ".join(f["choices"][:8])
                extra = "  [%s%s]" % (shown, ", ..." if len(f["choices"]) > 8 else "")
            print("  %-28s %-18s%s" % (f["name"], f["type"], extra))
    elif fields_order:
        print("\nFields (from records): %s" % ", ".join(fields_order))
    if records:
        print("\nSampled records:")
        for r in records:
            first = next((("%s=%s" % (k, v)) for k, v in r["fields"].items()
                          if isinstance(v, (str, int, float)) and str(v).strip()), r["id"])
            print("  %s  %s" % (r["created_time"][:10] if r.get("created_time") else "?",
                               c.clip(first, 90)))
    else:
        print("\nNo records returned. Check the view's filters and that the token has access to "
              "this base -- see the scope notes in credentials.md.")
    for n in notes:
        print("\nNOTE: %s" % n)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
