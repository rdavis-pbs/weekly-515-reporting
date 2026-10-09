#!/usr/bin/env python
"""
Fetch the user's OWN Azure DevOps Git activity for a work week via the Azure DevOps REST API.

Companion to github_fetch.py for teams that keep some repos in Azure Repos instead of (or
alongside) GitHub. Stdlib only -- no pip installs. Works with `python` or `python3`.

What it does:
  1. Resolves config (.weekly-515-reporting/config.md) and the PAT.
  2. Identifies the authenticated user (connectionData) and, on Azure DevOps Services, their
     email (profiles/me) -- email is what Git commit authorship is keyed on.
  3. Computes the Mon-Fri work week (or takes --start/--end), same as github_fetch.py.
  4. Enumerates projects (or just AZURE_DEVOPS_PROJECT, if set) and every Git repo in each,
     then collects: commits authored, PRs created, PRs completed, and PRs reviewed.
  5. For reviewed PRs, the vote is already in the list response (no extra call); the *time* of
     the vote is approximated from the user's own thread comments when any exist in the window,
     since Azure DevOps' REST API does not expose a per-vote timestamp.
  6. Writes a lean JSON artifact the azure-git-summary skill reads to write azure-git-summary.md.

Read-only: performs no commits, pushes, votes, or comments in Azure DevOps.

Usage:
  python azure_devops_fetch.py                   # current work week, auto-resolve everything
  python azure_devops_fetch.py --check            # verify auth + identity only, write nothing
  python azure_devops_fetch.py --start 2026-07-13 --end 2026-07-17   # backfill an older week
"""

import argparse
import base64
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c                                                          # noqa: E402

API_VERSION = "7.1"
MAX_BODY_CHARS = 1200
MAX_MESSAGE_CHARS = 400

# Repos scanned across all projects, and PRs whose threads get fetched for review-comment detail.
# Both cost one extra API call each; beyond the cap, stop and say so rather than running forever
# against a large org.
REPO_CAP = 150
REVIEW_DETAIL_CAP = 60

VOTE_LABELS = {
    10: "Approved",
    5: "Approved with suggestions",
    0: "No vote",
    -5: "Waiting for author",
    -10: "Rejected",
}

TOKEN_HELP = (
    "Create a PAT at https://dev.azure.com/{org}/_usersSettings/tokens\n"
    "  - Scope: Code (Read) is enough for commits, PRs, and reviews across the projects you work in.\n"
    "Without Code (Read) on a project, that project's repos simply don't appear -- there's no error."
)


def parse_org(raw):
    """Accept dev.azure.com/{org}, {org}.visualstudio.com, or an on-prem Server/collection URL.

    Returns (base_url_for_core_apis, org_name, is_cloud). `is_cloud` controls whether we also try
    the vssps.dev.azure.com profile endpoint for the user's email.
    """
    url = re.sub(r"^https?://", "", raw.strip()).rstrip("/")
    parts = url.split("/")
    host = parts[0]
    if host.lower() in ("dev.azure.com", "www.dev.azure.com") and len(parts) >= 2:
        org = parts[1]
        return "https://dev.azure.com/%s" % org, org, True
    if host.lower().endswith(".visualstudio.com"):
        org = host.split(".")[0]
        return "https://%s" % host, org, True
    # On-prem Azure DevOps Server (or a collection URL): take the whole thing as the base.
    return "https://" + url, (parts[-1] or host), False


class AzureDevOps(c.HttpClient):
    def __init__(self, base, pat, **kw):
        cred = base64.b64encode((":" + pat).encode("utf-8")).decode("ascii")
        c.HttpClient.__init__(self, base, {
            "Authorization": "Basic %s" % cred,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "weekly-515-reporting/azure_devops_fetch",
        }, **kw)

    def auth_error(self, code, detail):
        return c.ApiError(
            "Azure DevOps rejected the PAT (HTTP %d). Check the organization URL is exactly right, "
            "the PAT hasn't expired, and it has at least Code (Read) scope.\n%s" % (code, detail)
        )

    def connection_data(self):
        # Unlike the Git/project endpoints below, connectionData has never graduated out of
        # preview -- plain "7.1" is rejected with HTTP 400 ("under preview").
        return self.request("/_apis/connectionData", params={"api-version": "7.1-preview.1"})

    def list_projects(self):
        items, token = [], None
        while True:
            params = {"api-version": API_VERSION, "$top": 100}
            if token:
                params["continuationToken"] = token
            data, headers = self.request("/_apis/projects", params=params, with_headers=True)
            items.extend(data.get("value") or [])
            headers = {k.lower(): v for k, v in headers.items()}
            token = headers.get("x-ms-continuationtoken")
            if not token:
                return items

    def list_repos(self, project):
        data = self.request("/%s/_apis/git/repositories" % c.urllib.parse.quote(project),
                            params={"api-version": API_VERSION})
        return [r for r in (data.get("value") or []) if not r.get("isDisabled")]

    def list_commits(self, project, repo_id, email, from_date, to_date):
        items, skip = [], 0
        proj = c.urllib.parse.quote(project)
        while True:
            params = {
                "api-version": API_VERSION,
                "searchCriteria.author": email,
                "searchCriteria.fromDate": from_date,
                "searchCriteria.toDate": to_date,
                "$top": 100,
                "$skip": skip,
            }
            data = self.request("/%s/_apis/git/repositories/%s/commits" % (proj, repo_id), params=params)
            batch = data.get("value") or []
            items.extend(batch)
            if len(batch) < 100:
                return items
            skip += 100

    def list_pull_requests(self, project, criteria_key, identity_id):
        items, skip = [], 0
        proj = c.urllib.parse.quote(project)
        while True:
            params = {
                "api-version": API_VERSION,
                "searchCriteria.status": "all",
                "searchCriteria.%s" % criteria_key: identity_id,
                "$top": 100,
                "$skip": skip,
            }
            data = self.request("/%s/_apis/git/pullrequests" % proj, params=params)
            batch = data.get("value") or []
            items.extend(batch)
            if len(batch) < 100:
                return items
            skip += 100

    def pr_threads(self, project, repo_id, pr_id):
        proj = c.urllib.parse.quote(project)
        data = self.request("/%s/_apis/git/repositories/%s/pullrequests/%d/threads"
                            % (proj, repo_id, pr_id), params={"api-version": API_VERSION})
        return data.get("value") or []


def resolve_identity(ado, org, is_cloud, pat, insecure, verbose):
    """Returns (identity_id, display_name, email-or-None)."""
    conn = ado.connection_data()
    user = conn.get("authenticatedUser") or {}
    identity_id = user.get("id")
    display_name = user.get("providerDisplayName") or user.get("customDisplayName")
    if not identity_id:
        c.die("Azure DevOps did not return an authenticated identity. Check the PAT and org URL.")

    email = None
    if is_cloud:
        try:
            profile = AzureDevOps("https://vssps.dev.azure.com/%s" % org, pat,
                                  insecure=insecure, verbose=verbose)
            me = profile.request("/_apis/profile/profiles/me",
                                 params={"api-version": "7.1-preview.3"})
            email = me.get("emailAddress")
            display_name = me.get("displayName") or display_name
        except c.ApiError as e:
            c.note("  NOTE: could not read profile email (%s); set AZURE_DEVOPS_EMAIL in config.md "
                   "if commits come back empty." % e)
    return identity_id, display_name, email


def shape_commit(item, project_name, repo_name):
    author = item.get("author") or {}
    msg = (item.get("comment") or "").strip()
    return {
        "project": project_name,
        "repo": repo_name,
        "commit_id": (item.get("commitId") or "")[:10],
        "url": item.get("remoteUrl") or item.get("url"),
        "subject": c.clip(msg.split("\n")[0], MAX_MESSAGE_CHARS),
        "message": c.clip(msg, MAX_BODY_CHARS) if "\n" in msg else None,
        "authored_at": author.get("date"),
        "author_name": author.get("name"),
        "author_email": author.get("email"),
    }


def pr_web_url(pr):
    repo = pr.get("repository") or {}
    web_url = repo.get("webUrl") or repo.get("url")
    pr_id = pr.get("pullRequestId")
    if web_url and pr_id:
        return "%s/pullrequest/%d" % (web_url.rstrip("/"), pr_id)
    return web_url


def shape_pr(pr, project_name):
    repo = pr.get("repository") or {}
    return {
        "project": project_name,
        "repo": repo.get("name"),
        "repo_id": repo.get("id"),
        "id": pr.get("pullRequestId"),
        "title": pr.get("title"),
        "url": pr_web_url(pr),
        "status": pr.get("status"),
        "is_draft": pr.get("isDraft"),
        "created_at": pr.get("creationDate"),
        "closed_at": pr.get("closedDate"),
        "description": c.clip(pr.get("description"), MAX_BODY_CHARS),
        "source_branch": pr.get("sourceRefName"),
        "target_branch": pr.get("targetRefName"),
    }


def dedupe(records):
    seen, out = set(), []
    for r in records:
        key = (r.get("project"), r.get("repo"), r.get("id"), r.get("commit_id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch your own Azure DevOps Git activity for a work week.")
    ap.add_argument("--config", help="path to .weekly-515-reporting/config.md (auto-discovered if omitted)")
    ap.add_argument("--start", help="window start date YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", help="window end date YYYY-MM-DD (inclusive); also names the output folder")
    ap.add_argument("--out", help="exact output JSON path (default <OUTPUT_ROOT>/<FRIDAY>/azure-git-activity.json)")
    ap.add_argument("--check", action="store_true", help="verify auth and identity; write nothing")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (TLS-inspecting networks)")
    ap.add_argument("--verbose", action="store_true", help="log each HTTP request to stderr")
    args = ap.parse_args(argv)

    c.force_utf8_output()
    config_path = c.find_config(args.config)
    config = c.parse_kv(config_path)
    c.note("config: %s" % config_path)

    org_url = config.get("AZURE_DEVOPS_ORG_URL")
    if not org_url:
        c.die("Set AZURE_DEVOPS_ORG_URL (e.g. https://dev.azure.com/yourorg) in %s" % config_path)
    base, org, is_cloud = parse_org(org_url)
    c.note("org:    %s (%s)" % (org, base))

    pat, token_src = c.resolve_secret("AZURE_DEVOPS_PAT", config_path, config, TOKEN_HELP)
    c.note("token:  %s" % token_src)
    c.warn_if_expiring("AZURE_DEVOPS_PAT", config_path, config, TOKEN_HELP)

    ado = AzureDevOps(base, pat, insecure=args.insecure, verbose=args.verbose)

    try:
        identity_id, display_name, email = resolve_identity(ado, org, is_cloud, pat, args.insecure, args.verbose)
    except c.ApiError as e:
        c.die(str(e))
    email = config.get("AZURE_DEVOPS_EMAIL") or email
    c.note("auth:   OK as %s (%s)" % (display_name, identity_id))

    project_filter = [p.strip() for p in (config.get("AZURE_DEVOPS_PROJECT") or "").split(",") if p.strip()]
    try:
        if project_filter:
            projects = project_filter
        else:
            projects = [p.get("name") for p in ado.list_projects() if p.get("name")]
    except c.ApiError as e:
        c.die("Could not list projects.\n%s" % e)
    c.note("projects: %s" % ", ".join(projects))

    start, end = c.resolve_window(args, c.workweek_window)
    start_iso, end_iso = start.isoformat(), end.isoformat()
    folder = end_iso
    label = c.label_for(start, end)
    from_date = start_iso
    to_date = (end + datetime.timedelta(days=1)).isoformat()  # widen net; filtered precisely below
    c.note("window: %s .. %s  (%s)" % (start_iso, end_iso, label))

    if args.check:
        print("OK: authenticated to %s as %s." % (org, display_name))
        print("Email for commit matching: %s" % (email or "NOT RESOLVED -- set AZURE_DEVOPS_EMAIL"))
        print("Projects visible: %d (%s)" % (len(projects), ", ".join(projects) or "none"))
        return 0

    if not email:
        c.die("Could not resolve your email address for commit matching. Set AZURE_DEVOPS_EMAIL in "
              "%s to your Azure DevOps account email." % config_path)

    notes = []
    commits, prs_created, reviewed_raw = [], [], []
    repos_scanned, repo_total = 0, 0

    for project in projects:
        try:
            repos = ado.list_repos(project)
        except c.ApiError as e:
            notes.append("Could not list repos in project %r: %s" % (project, e))
            continue
        repo_total += len(repos)

        try:
            created = ado.list_pull_requests(project, "creatorId", identity_id)
            reviewed = ado.list_pull_requests(project, "reviewerId", identity_id)
        except c.ApiError as e:
            notes.append("PR search failed for project %r: %s" % (project, e))
            created, reviewed = [], []
        prs_created.extend(shape_pr(pr, project) for pr in created)
        for pr in reviewed:
            reviewed_raw.append((project, pr))

        for repo in repos:
            if repos_scanned >= REPO_CAP:
                notes.append("Repo scan capped at %d repos; some repos were skipped." % REPO_CAP)
                break
            repos_scanned += 1
            try:
                repo_commits = ado.list_commits(project, repo.get("id"), email, from_date, to_date)
            except c.ApiError as e:
                notes.append("Commit search failed for %s/%s: %s" % (project, repo.get("name"), e))
                continue
            commits.extend(shape_commit(cm, project, repo.get("name")) for cm in repo_commits)

    commits = dedupe([cm for cm in commits if c.in_window(cm["authored_at"], start_iso, end_iso)])

    prs_opened = [pr for pr in prs_created if c.in_window(pr["created_at"], start_iso, end_iso)]
    prs_completed = [pr for pr in prs_created
                      if pr["status"] == "completed" and c.in_window(pr["closed_at"], start_iso, end_iso)]

    reviewed, capped = [], 0
    for i, (project, pr) in enumerate(reviewed_raw):
        shaped = shape_pr(pr, project)
        reviewers = pr.get("reviewers") or []
        mine = next((r for r in reviewers if r.get("id") == identity_id), None)
        vote = (mine or {}).get("vote") or 0

        comments, approximate = [], False
        if i < REVIEW_DETAIL_CAP and shaped.get("repo_id"):
            try:
                threads = ado.pr_threads(project, shaped["repo_id"], shaped["id"])
            except c.ApiError:
                threads = []
            for thread in threads:
                for cm in thread.get("comments") or []:
                    if (cm.get("author") or {}).get("id") != identity_id:
                        continue
                    at = cm.get("publishedDate")
                    if c.in_window(at, start_iso, end_iso):
                        comments.append({"at": at, "body": c.clip(cm.get("content"), MAX_BODY_CHARS)})
        elif i >= REVIEW_DETAIL_CAP:
            capped += 1

        in_window = bool(comments)
        if not in_window and vote != 0:
            # No comment to pin the vote to a date -- fall back to the PR's own dates and say so.
            if c.in_window(shaped.get("created_at"), start_iso, end_iso) or \
               c.in_window(shaped.get("closed_at"), start_iso, end_iso):
                in_window, approximate = True, True

        if not in_window:
            continue
        shaped["my_vote"] = vote
        shaped["my_vote_label"] = VOTE_LABELS.get(vote, str(vote))
        shaped["my_comments"] = comments
        shaped["vote_date_is_approximate"] = approximate
        reviewed.append(shaped)
    if capped:
        notes.append("Review comment detail skipped for %d PRs beyond the %d-PR cap."
                     % (capped, REVIEW_DETAIL_CAP))
    if repos_scanned >= REPO_CAP and repo_total > repos_scanned:
        notes.append("%d of %d repos scanned (REPO_CAP=%d)." % (repos_scanned, repo_total, REPO_CAP))

    for pr in prs_opened + prs_completed + reviewed:
        pr.pop("repo_id", None)

    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "org": org,
        "me": {"id": identity_id, "display_name": display_name, "email": email},
        "window": {"start": start_iso, "end": end_iso, "label": label, "basis": "Monday to Friday, inclusive"},
        "projects_scanned": projects,
        "counts": {
            "commits": len(commits),
            "prs_opened": len(prs_opened),
            "prs_completed": len(prs_completed),
            "prs_reviewed": len(reviewed),
        },
        "commits": commits,
        "prs_opened": prs_opened,
        "prs_completed": prs_completed,
        "prs_reviewed": reviewed,
        "notes": notes,
    }

    out_path = c.output_path(args.out, config_path, config, folder, "azure-git-activity.json")
    c.write_json(out_path, payload)

    print("Wrote %s" % out_path)
    print("Week %s (%s .. %s) as %s" % (label, start_iso, end_iso, display_name))
    for k, v in payload["counts"].items():
        print("  %-14s %d" % (k, v))
    if not any(payload["counts"].values()):
        print("\nNo activity found. If you expected some, check the PAT has Code (Read) on the "
              "right projects, and that AZURE_DEVOPS_PROJECT (if set) names them correctly.")
    for bucket, title in (("prs_completed", "Completed"), ("prs_opened", "Opened"),
                          ("prs_reviewed", "Reviewed")):
        if payload[bucket]:
            print("\n%s:" % title)
            for r in payload[bucket]:
                print("  %s/%s!%s  %s" % (r["project"], r["repo"], r["id"], r["title"]))
    if commits:
        print("\nCommits:")
        for cm in commits:
            print("  %s/%s %s  %s" % (cm["project"], cm["repo"], cm["commit_id"], cm["subject"]))
    for n in notes:
        print("\nNOTE: %s" % n)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
