#!/usr/bin/env python
"""
Fetch the user's OWN GitHub activity for a work week via the GitHub REST API.

Replaces the browser-based (Claude in Chrome) GitHub collection for the weekly-515-reporting
plugin. Stdlib only -- no pip installs. Works with `python` or `python3`.

What it does:
  1. Resolves config (.weekly-515-reporting/config.md) and the GitHub token.
  2. Computes the Mon-Fri work week (or takes --start/--end).
  3. Runs GitHub search across all repos the token can see, in five buckets: commits authored,
     PRs opened, PRs merged, PRs reviewed, issues opened/closed.
  4. For reviewed PRs, pulls the actual review bodies and keeps only reviews the user submitted
     inside the window -- `reviewed-by:` alone can't tell you when or what.
  5. Writes a lean JSON artifact the git-summary skill reads to write git-summary.md.

Read-only: performs no writes, comments, or merges on GitHub.

Usage:
  python github_fetch.py                     # current work week, auto-resolve everything
  python github_fetch.py --check             # verify auth + identity only, write nothing
  python github_fetch.py --start 2026-07-13 --end 2026-07-17   # backfill an older week
"""

import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c                                                          # noqa: E402

MAX_BODY_CHARS = 1200
MAX_MESSAGE_CHARS = 400

# Reviewed-PR detail costs one extra API call per PR. Beyond this many, stop fetching detail and
# say so in the output rather than silently truncating.
REVIEW_DETAIL_CAP = 60

TOKEN_HELP = (
    "Create a token at https://github.com/settings/tokens\n"
    "  - Classic token: tick `repo` (private repo visibility) and `read:org`.\n"
    "  - Fine-grained token: grant read-only Contents, Pull requests, Issues, and Metadata\n"
    "    on the repos/orgs you work in.\n"
    "Without `repo`/Contents access the search only sees your PUBLIC activity."
)


def api_base(host):
    """github.com uses api.github.com; GitHub Enterprise Server uses HOST/api/v3."""
    host = re.sub(r"^https?://", "", (host or "github.com").strip()).strip("/")
    if host in ("github.com", "www.github.com", "api.github.com"):
        return "https://api.github.com", "github.com"
    return "https://%s/api/v3" % host, host


class GitHub(c.HttpClient):
    def __init__(self, base, token, **kw):
        c.HttpClient.__init__(self, base, {
            "Authorization": "Bearer %s" % token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "weekly-515-reporting/github_fetch",
        }, **kw)

    def auth_error(self, code, detail):
        if "rate limit" in detail.lower():
            return c.ApiError("GitHub rate limit hit (HTTP %d).\n%s" % (code, detail))
        return c.ApiError(
            "GitHub rejected the token (HTTP %d). Check it hasn't expired, and that it has the "
            "scopes listed in credentials.md.\n%s" % (code, detail)
        )

    def viewer(self):
        return self.request("/user")

    def search(self, kind, query, extra=None):
        """Paginate a search endpoint. GitHub caps search at 1000 results per query."""
        items, page = [], 1
        while True:
            params = {"q": query, "per_page": 100, "page": page}
            if extra:
                params.update(extra)
            result = self.request("/search/%s" % kind, params=params)
            batch = result.get("items") or []
            items.extend(batch)
            total = int(result.get("total_count") or 0)
            if not batch or len(items) >= total or len(items) >= 1000 or page >= 10:
                if total > len(items):
                    c.note("  NOTE: %d of %d results retrieved for `%s` (GitHub search caps at 1000)"
                           % (len(items), total, query))
                return items
            page += 1

    def pull_reviews(self, owner, repo, number):
        return self.request("/repos/%s/%s/pulls/%d/reviews" % (owner, repo, number),
                            params={"per_page": 100})


def repo_from_url(url):
    """Extract (owner, repo) from a repository_url or html_url."""
    m = re.search(r"/repos/([^/]+)/([^/]+)", url or "")
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"github[^/]*/([^/]+)/([^/]+)/(?:pull|issues)/", url or "")
    if m:
        return m.group(1), m.group(2)
    return None, None


def shape_issue(item):
    """Shape a search/issues result (covers both issues and PRs)."""
    owner, repo = repo_from_url(item.get("repository_url") or item.get("html_url"))
    pr = item.get("pull_request") or {}
    return {
        "repo": ("%s/%s" % (owner, repo)) if owner else None,
        "number": item.get("number"),
        "title": item.get("title"),
        "url": item.get("html_url"),
        "state": item.get("state"),
        "is_pr": bool(item.get("pull_request")),
        "draft": item.get("draft"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "closed_at": item.get("closed_at"),
        "merged_at": pr.get("merged_at"),
        "labels": [l.get("name") for l in (item.get("labels") or []) if isinstance(l, dict)],
        "author": (item.get("user") or {}).get("login"),
        "body": c.clip(item.get("body"), MAX_BODY_CHARS),
        "comments": item.get("comments"),
    }


def shape_commit(item):
    commit = item.get("commit") or {}
    repo = item.get("repository") or {}
    message = (commit.get("message") or "").strip()
    # `item["author"]` is the linked GitHub account and can be null; `commit["author"]` is the raw
    # git identity and is always present. Track which one we used so the caller can tell a
    # "different person" from an "unlinked email."
    gh_author = (item.get("author") or {}).get("login")
    return {
        "repo": repo.get("full_name"),
        "sha": (item.get("sha") or "")[:10],
        "url": item.get("html_url"),
        # First line is the subject; the rest is usually boilerplate for reporting purposes.
        "subject": c.clip(message.split("\n")[0], MAX_MESSAGE_CHARS),
        "message": c.clip(message, MAX_BODY_CHARS) if "\n" in message else None,
        "authored_at": (commit.get("author") or {}).get("date"),
        "author": gh_author or (commit.get("author") or {}).get("name"),
        "author_is_github_account": bool(gh_author),
    }


def dedupe(records):
    """Collapse duplicates keyed by repo + number (or sha)."""
    seen, out = set(), []
    for r in records:
        key = (r.get("repo"), r.get("number"), r.get("sha"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch your own GitHub activity for a work week.")
    ap.add_argument("--config", help="path to .weekly-515-reporting/config.md (auto-discovered if omitted)")
    ap.add_argument("--start", help="window start date YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", help="window end date YYYY-MM-DD (inclusive); also names the output folder")
    ap.add_argument("--out", help="exact output JSON path (default <OUTPUT_ROOT>/<FRIDAY>/github-activity.json)")
    ap.add_argument("--check", action="store_true", help="verify auth and identity; write nothing")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (TLS-inspecting networks)")
    ap.add_argument("--verbose", action="store_true", help="log each HTTP request to stderr")
    args = ap.parse_args(argv)

    config_path = c.find_config(args.config)
    config = c.parse_kv(config_path)
    c.note("config: %s" % config_path)

    base, host = api_base(config.get("GITHUB_HOST"))
    token, token_src = c.resolve_secret("GITHUB_TOKEN", config_path, config, TOKEN_HELP)
    c.note("host:   %s (%s)" % (host, base))
    c.note("token:  %s" % token_src)

    gh = GitHub(base, token, insecure=args.insecure, verbose=args.verbose)

    try:
        me = gh.viewer()
    except c.ApiError as e:
        c.die(str(e))
    login = config.get("GITHUB_USER") or me.get("login")
    if config.get("GITHUB_USER") and config["GITHUB_USER"] != me.get("login"):
        c.note("NOTE: config GITHUB_USER (%s) differs from the token's account (%s); using the config value."
               % (config["GITHUB_USER"], me.get("login")))
    c.note("auth:   OK as %s" % me.get("login"))

    # The anchor Friday names the output folder; the searched window is that week's Mon-Fri.
    start, end = c.resolve_window(args, c.workweek_window)
    start_iso, end_iso = start.isoformat(), end.isoformat()
    folder = end_iso
    label = c.label_for(start, end)
    span = "%s..%s" % (start_iso, end_iso)
    c.note("window: %s .. %s  (%s)" % (start_iso, end_iso, label))

    if args.check:
        probe = gh.search("issues", "author:%s created:%s" % (login, span),
                          {"advanced_search": "true"})
        print("OK: authenticated to %s as %s (reporting for %s)." % (host, me.get("login"), login))
        print("Week %s: %d PRs/issues you opened." % (label, len(probe)))
        print("If that looks low and your work is in private repos, the token is likely missing "
              "`repo` (classic) or Contents/Pull-requests read access (fine-grained).")
        return 0

    # GitHub's issue search now requires advanced_search; harmless on hosts that ignore it.
    adv = {"advanced_search": "true"}

    def issue_search(q):
        try:
            return gh.search("issues", q, adv)
        except c.ApiError as e:
            if "HTTP 422" in str(e):
                c.note("  advanced_search rejected; retrying without it")
                return gh.search("issues", q)
            raise

    c.note("searching...")
    try:
        prs_opened = [shape_issue(i) for i in issue_search(
            "is:pr author:%s created:%s" % (login, span))]
        prs_merged = [shape_issue(i) for i in issue_search(
            "is:pr author:%s merged:%s" % (login, span))]
        prs_reviewed = [shape_issue(i) for i in issue_search(
            "is:pr reviewed-by:%s updated:%s" % (login, span))]
        issues_opened = [shape_issue(i) for i in issue_search(
            "is:issue author:%s created:%s" % (login, span))]
        issues_closed = dedupe(
            [shape_issue(i) for i in issue_search("is:issue author:%s closed:%s" % (login, span))] +
            [shape_issue(i) for i in issue_search("is:issue assignee:%s closed:%s" % (login, span))]
        )
        commits = [shape_commit(i) for i in gh.search(
            "commits", "author:%s author-date:%s" % (login, span))]
    except c.ApiError as e:
        c.die("GitHub search failed.\n%s" % e)

    # `reviewed-by:` matches PRs the user reviewed at ANY time, filtered only by the PR's own
    # updated date -- so confirm each review was actually submitted by the user in the window.
    reviewed = []
    capped = 0
    for i, pr in enumerate(prs_reviewed):
        if pr["repo"] is None or pr["number"] is None:
            continue
        if i >= REVIEW_DETAIL_CAP:
            capped += 1
            continue
        owner, repo = pr["repo"].split("/", 1)
        try:
            reviews = gh.pull_reviews(owner, repo, pr["number"])
        except c.ApiError as e:
            c.note("    WARNING: reviews for %s#%s: %s" % (pr["repo"], pr["number"], e))
            continue
        mine = [
            {"at": r.get("submitted_at"), "state": r.get("state"),
             "body": c.clip(r.get("body"), MAX_BODY_CHARS)}
            for r in reviews
            if (r.get("user") or {}).get("login") == login
            and c.in_window(r.get("submitted_at"), start_iso, end_iso)
        ]
        if mine:
            entry = dict(pr)
            entry["my_reviews"] = mine
            reviewed.append(entry)
    if capped:
        c.note("  NOTE: review detail skipped for %d PRs beyond the %d-PR cap" % (capped, REVIEW_DETAIL_CAP))

    # `author:LOGIN` in the query already constrains attribution, so only drop a commit when GitHub
    # positively attributes it to somebody else. Requiring an exact login match would silently drop
    # commits whose author object is null -- which happens whenever the commit's email isn't linked
    # to a GitHub account, exactly the case where `author` falls back to the raw git name.
    commits = [cm for cm in commits
               if cm["author"] in (login, None, me.get("login"), me.get("name"))
               or not cm["author_is_github_account"]]
    commits = [cm for cm in commits if c.in_window(cm["authored_at"], start_iso, end_iso)]

    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "host": host,
        "me": {"login": me.get("login"), "name": me.get("name"), "reporting_for": login},
        "window": {"start": start_iso, "end": end_iso, "label": label, "basis": "Monday to Friday, inclusive"},
        "counts": {
            "commits": len(commits),
            "prs_opened": len(prs_opened),
            "prs_merged": len(prs_merged),
            "prs_reviewed": len(reviewed),
            "issues_opened": len(issues_opened),
            "issues_closed": len(issues_closed),
        },
        "commits": commits,
        "prs_opened": prs_opened,
        "prs_merged": prs_merged,
        "prs_reviewed": reviewed,
        "issues_opened": issues_opened,
        "issues_closed": issues_closed,
        "notes": ([] if not capped else
                  ["Review detail skipped for %d PRs beyond the %d-PR cap." % (capped, REVIEW_DETAIL_CAP)]),
    }

    out_path = c.output_path(args.out, config_path, config, folder, "github-activity.json")
    c.write_json(out_path, payload)

    print("Wrote %s" % out_path)
    print("Week %s (%s .. %s) as %s" % (label, start_iso, end_iso, login))
    for k, v in payload["counts"].items():
        print("  %-14s %d" % (k, v))
    if not any(payload["counts"].values()):
        print("\nNo activity found. If you expected some, the token most likely can't see your "
              "private repos -- see the scope notes in credentials.md.")
    for bucket, title in (("prs_merged", "Merged"), ("prs_opened", "Opened"),
                          ("prs_reviewed", "Reviewed"), ("issues_closed", "Issues closed")):
        if payload[bucket]:
            print("\n%s:" % title)
            for r in payload[bucket]:
                print("  %s#%s  %s" % (r["repo"], r["number"], r["title"]))
    if commits:
        print("\nCommits:")
        for cm in commits:
            print("  %s %s  %s" % (cm["repo"], cm["sha"], cm["subject"]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)