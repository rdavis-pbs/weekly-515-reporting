#!/usr/bin/env python
"""
Fetch the user's OWN Jira activity for a reporting window via the Jira Cloud REST API.

Replaces the old browser-based (Claude in Chrome) Jira collection for the weekly-515-reporting
plugin. Stdlib only -- no pip installs. Works with `python` or `python3`.

What it does:
  1. Resolves config (.weekly-515-reporting/config.md) and the API token.
  2. Computes the Fri->Fri reporting window (or takes --start/--end).
  3. Runs the configured JQL to get candidate issues.
  4. For each issue, pulls the changelog and comments, and keeps ONLY entries whose author is
     the authenticated user AND whose date falls inside the window.
  5. Writes a lean JSON artifact the jira-summary skill reads to write jira-summary.md.

Read-only: performs no writes, transitions, or comments in Jira.

Usage:
  python jira_fetch.py                       # current reporting window, auto-resolve everything
  python jira_fetch.py --check               # verify auth + JQL only, write nothing
  python jira_fetch.py --start 2026-07-10 --end 2026-07-17   # backfill an older week
  python jira_fetch.py --out path/to/jira-activity.json
"""

import argparse
import base64
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c                                                          # noqa: E402

DEFAULT_JQL = 'issuekey in updatedBy("{email}", "{start}", "{end}") order by updatedDate desc'

SEARCH_FIELDS = [
    "summary", "status", "issuetype", "parent", "priority", "labels",
    "created", "resolutiondate", "assignee", "reporter", "project",
]

# Backlog-ordering churn; carries no reporting signal.
NOISE_FIELDS = {"Rank"}

MAX_VALUE_CHARS = 200
MAX_COMMENT_CHARS = 1500

TOKEN_HELP = ("Create one at https://id.atlassian.com/manage-profile/security/api-tokens\n"
              "(\"Create API token\" is enough; it inherits your own Jira permissions.)")


def normalize_site(raw):
    """Accept 'org.atlassian.net', a full URL, or a filter URL; return the bare host."""
    site = re.sub(r"^https?://", "", raw.strip())
    return site.split("/")[0].rstrip("/")


class Jira(c.HttpClient):
    def __init__(self, site, email, token, **kw):
        cred = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
        c.HttpClient.__init__(self, "https://%s" % site, {
            "Authorization": "Basic %s" % cred,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "weekly-515-reporting/jira_fetch",
        }, **kw)

    def auth_error(self, code, detail):
        return c.ApiError(
            "Jira rejected the credentials (HTTP %d). Check JIRA_EMAIL matches the account that "
            "created the token, and that the token is not revoked/expired.\n%s" % (code, detail)
        )

    def myself(self):
        return self.request("/rest/api/3/myself")

    def search(self, jql):
        """Enhanced search (/search/jql), falling back to the legacy v2 endpoint."""
        try:
            return self._search_jql(jql)
        except c.ApiError as e:
            if "HTTP 404" in str(e) or "HTTP 410" in str(e):
                c.note("  /search/jql unavailable; falling back to /rest/api/2/search")
                return self._search_legacy(jql)
            raise

    def _search_jql(self, jql):
        issues, token = [], None
        while True:
            body = {"jql": jql, "fields": SEARCH_FIELDS, "maxResults": 100}
            if token:
                body["nextPageToken"] = token
            page = self.request("/rest/api/3/search/jql", method="POST", body=body)
            issues.extend(page.get("issues") or [])
            token = page.get("nextPageToken")
            if page.get("isLast") or not token:
                return issues

    def _search_legacy(self, jql):
        issues, start = [], 0
        while True:
            page = self.request("/rest/api/2/search", params={
                "jql": jql, "fields": ",".join(SEARCH_FIELDS),
                "startAt": start, "maxResults": 100,
            })
            batch = page.get("issues") or []
            issues.extend(batch)
            start += len(batch)
            if not batch or start >= int(page.get("total") or 0):
                return issues

    def changelog(self, key):
        entries, start = [], 0
        while True:
            page = self.request("/rest/api/2/issue/%s/changelog" % key,
                                params={"startAt": start, "maxResults": 100})
            batch = page.get("values") or []
            entries.extend(batch)
            start += len(batch)
            if page.get("isLast") or not batch or start >= int(page.get("total") or 0):
                return entries

    def comments(self, key):
        found, start = [], 0
        while True:
            page = self.request("/rest/api/2/issue/%s/comment" % key,
                                params={"startAt": start, "maxResults": 100, "orderBy": "created"})
            batch = page.get("comments") or []
            found.extend(batch)
            start += len(batch)
            if not batch or start >= int(page.get("total") or 0):
                return found


def my_changes(entries, account_id, start_iso, end_iso):
    out = []
    for entry in entries:
        if (entry.get("author") or {}).get("accountId") != account_id:
            continue
        created = entry.get("created")
        if not c.in_window(created, start_iso, end_iso):
            continue
        for item in entry.get("items") or []:
            field = item.get("field") or item.get("fieldId") or "?"
            if field in NOISE_FIELDS:
                continue
            out.append({
                "at": created,
                "field": field,
                "from": c.clip(item.get("fromString") or item.get("from"), MAX_VALUE_CHARS),
                "to": c.clip(item.get("toString") or item.get("to"), MAX_VALUE_CHARS),
            })
    return out


def my_comments(entries, account_id, start_iso, end_iso):
    out = []
    for cm in entries:
        if (cm.get("author") or {}).get("accountId") != account_id:
            continue
        if not c.in_window(cm.get("created"), start_iso, end_iso):
            continue
        out.append({"at": cm.get("created"), "body": c.clip(cm.get("body"), MAX_COMMENT_CHARS)})
    return out


def shape_issue(issue, site):
    f = issue.get("fields") or {}

    def name_of(obj, key="name"):
        return (obj or {}).get(key)

    parent = f.get("parent") or {}
    return {
        "key": issue.get("key"),
        "url": "https://%s/browse/%s" % (site, issue.get("key")),
        "summary": f.get("summary"),
        "type": name_of(f.get("issuetype")),
        "status": name_of(f.get("status")),
        "status_category": ((f.get("status") or {}).get("statusCategory") or {}).get("name"),
        "priority": name_of(f.get("priority")),
        "labels": f.get("labels") or [],
        "project": name_of(f.get("project")),
        "parent": ({"key": parent.get("key"),
                    "summary": (parent.get("fields") or {}).get("summary")} if parent else None),
        "assignee": name_of(f.get("assignee"), "displayName"),
        "reporter": name_of(f.get("reporter"), "displayName"),
        "created": f.get("created"),
        "resolutiondate": f.get("resolutiondate"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch your own Jira activity for a reporting window.")
    ap.add_argument("--config", help="path to .weekly-515-reporting/config.md (auto-discovered if omitted)")
    ap.add_argument("--start", help="window start date YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", help="window end date YYYY-MM-DD (inclusive); also names the output folder")
    ap.add_argument("--out", help="exact output JSON path (default <OUTPUT_ROOT>/<END>/jira-activity.json)")
    ap.add_argument("--check", action="store_true", help="verify auth + JQL and print counts; write nothing")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (TLS-inspecting networks)")
    ap.add_argument("--verbose", action="store_true", help="log each HTTP request to stderr")
    args = ap.parse_args(argv)

    config_path = c.find_config(args.config)
    config = c.parse_kv(config_path)
    c.note("config: %s" % config_path)

    site_raw = config.get("JIRA_SITE") or config.get("JIRA_FILTER_URL")
    if not site_raw:
        c.die("Set JIRA_SITE (e.g. yourorg.atlassian.net) in %s" % config_path)
    site = normalize_site(site_raw)

    email = config.get("JIRA_EMAIL") or os.environ.get("JIRA_EMAIL", "").strip()
    if not email:
        c.die("Set JIRA_EMAIL (the Atlassian account email) in %s" % config_path)

    token, token_src = c.resolve_secret("JIRA_API_TOKEN", config_path, config, TOKEN_HELP)
    c.note("token:  %s" % token_src)

    start, end = c.resolve_window(args, c.friday_to_friday_window)
    start_iso, end_iso = start.isoformat(), end.isoformat()
    label = c.label_for(start, end)

    # The net is widened a day past the window end because Jira's date-only comparisons land on
    # midnight, which would drop the final day's activity. Per-item filtering below is
    # authoritative, so the wider net costs nothing but a few extra candidates.
    jql = ((config.get("JIRA_JQL") or DEFAULT_JQL)
           .replace("{email}", email)
           .replace("{start}", start.strftime("%Y/%m/%d"))
           .replace("{end}", (end + datetime.timedelta(days=1)).strftime("%Y/%m/%d"))
           .replace("{start_iso}", start_iso)
           .replace("{end_iso}", end_iso))

    c.note("window: %s .. %s  (%s)" % (start_iso, end_iso, label))
    c.note("jql:    %s" % jql)

    jira = Jira(site, email, token, insecure=args.insecure, verbose=args.verbose)

    try:
        me = jira.myself()
    except c.ApiError as e:
        c.die(str(e))
    account_id = me.get("accountId")
    c.note("auth:   OK as %s (%s)" % (me.get("displayName"), account_id))

    try:
        matched = jira.search(jql)
    except c.ApiError as e:
        c.die("JQL search failed. Check JIRA_JQL in %s.\n%s" % (config_path, e))
    c.note("issues: %d matched by JQL" % len(matched))

    if args.check:
        for issue in matched[:15]:
            print("  %-12s %s" % (issue.get("key"), (issue.get("fields") or {}).get("summary")))
        if len(matched) > 15:
            print("  ... and %d more" % (len(matched) - 15))
        print("\nOK: auth and JQL both work. %d candidate issues." % len(matched))
        return 0

    issues, skipped = [], []
    for i, issue in enumerate(matched, 1):
        key = issue.get("key")
        c.note("  [%d/%d] %s" % (i, len(matched), key))
        try:
            changes = my_changes(jira.changelog(key), account_id, start_iso, end_iso)
            comments = my_comments(jira.comments(key), account_id, start_iso, end_iso)
        except c.ApiError as e:
            c.note("    WARNING: %s -- keeping issue with no detail" % e)
            record = shape_issue(issue, site)
            record["fetch_error"] = str(e)
            record["my_changes"], record["my_comments"] = [], []
            issues.append(record)
            continue

        if not changes and not comments:
            skipped.append(key)
            continue

        record = shape_issue(issue, site)
        record["my_changes"] = changes
        record["my_comments"] = comments
        issues.append(record)

    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "site": site,
        "me": {"accountId": account_id, "displayName": me.get("displayName"), "email": email},
        "window": {"start": start_iso, "end": end_iso, "label": label,
                   "basis": "Friday to Friday, inclusive"},
        "jql": jql,
        "counts": {
            "matched_by_jql": len(matched),
            "with_my_activity": len(issues),
            "no_activity_in_window": len(skipped),
        },
        "issues": issues,
        "matched_but_no_activity_by_me_in_window": skipped,
    }

    out_path = c.output_path(args.out, config_path, config, end_iso, "jira-activity.json")
    c.write_json(out_path, payload)

    # Digest on stdout so the caller can see the shape without opening the file.
    print("Wrote %s" % out_path)
    print("Window %s (%s .. %s)" % (label, start_iso, end_iso))
    print("%d issues matched; %d with your own activity in the window; %d without."
          % (len(matched), len(issues), len(skipped)))
    for rec in issues:
        print("\n%s  [%s] %s" % (rec["key"], rec.get("status"), rec.get("summary")))
        for ch in rec["my_changes"]:
            print("    %s  %s: %s -> %s" % (ch["at"][:10], ch["field"], ch["from"], ch["to"]))
        for cm in rec["my_comments"]:
            print("    %s  comment: %s" % (cm["at"][:10], c.clip((cm["body"] or "").split("\n")[0], 120)))
    if skipped:
        print("\nMatched but nothing authored by you in the window: %s" % ", ".join(skipped))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)