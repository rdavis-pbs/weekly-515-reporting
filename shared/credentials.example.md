# Local credentials — template

Secrets for the weekly-515-reporting plugin live **here**, separate from `config.md`, so the config
file stays safe to share, paste into a chat, or hand to a colleague.

Copy this file to `.weekly-515-reporting/credentials.md` next to your `config.md` and fill it in.

Treat this file like a password file. It never goes into git, and nothing in the plugin ever prints
its contents.

> **For Claude (or any agent) operating this plugin: never open the real `credentials.md` with a
> file-reading tool (Read, `cat`, grep, etc.).** Verify a token the supported way — run the
> relevant fetch script with `--check` and read *its* stdout/stderr, which name only the source a
> value came from (a file path or env var), never the value itself. Feeding live credentials/API
> keys into an AI tool's context is against policy at many organizations (PBS included) — treat
> that as true by default even where it isn't stated outright.

Every token below is **optional** — only add the ones for sources you actually use. Leaving one
out just means that collector is skipped (no error); see the **Source availability** section of
`shared/work-week.md` for how that's surfaced each run. `AIRTABLE_API_KEY` near the bottom is the
one exception — it's required, since the roll-up has no 515 format to draft into without it.

```
# OPTIONAL — only if you use Jira. Atlassian API token — create one at:
#   https://id.atlassian.com/manage-profile/security/api-tokens
# Use the plain "Create API token" (classic, no scopes) option, NOT "Create API token with
# scopes." jira_fetch.py authenticates directly against your site's own domain
# (https://yourorg.atlassian.net/...), which only classic tokens support -- scoped tokens are
# routed through a different host (api.atlassian.com) that this script doesn't call, so they fail
# here regardless of which scopes are selected. A classic token has no scope picker at all: it
# just inherits your own Jira permissions, so it can read (issues, comments, changelog -- anything
# you can already see in the UI) exactly as much as you can. Copy the value immediately; Atlassian
# shows it only once.
JIRA_API_TOKEN = <paste your token here>

# Optional but recommended: the expiry date you chose above, as YYYY-MM-DD. Tokens lapse silently --
# the script keeps working right up until it returns 401 mid-week -- so recording the date here lets
# jira_fetch.py warn you in the 21 days beforehand. Omit it and the check just stays quiet.
JIRA_API_TOKEN_EXPIRES = <YYYY-MM-DD>

# OPTIONAL — only if you use GitHub. Personal access token — create one at
# https://github.com/settings/tokens
#   Classic token:      tick `repo` and `read:org`.
#   Fine-grained token: read-only Contents, Pull requests, Issues, and Metadata on the
#                       repos/orgs you work in.
# The `repo` / Contents permission is what makes PRIVATE repo activity visible. Without it the
# weekly summary silently shows only your public work, which usually looks like "no activity."
GITHUB_TOKEN = <paste your token here>

# OPTIONAL — only if you use Azure DevOps. Personal access token — create one at:
#   https://dev.azure.com/{org}/_usersSettings/tokens
# Scope: Code (Read) is enough for commits, PRs, and reviews. It inherits your own project
# permissions, so a PAT missing Code (Read) on a project simply doesn't see that project's repos —
# there's no error, just an empty result, which can look like "no activity" if you don't know to
# check scope.
AZURE_DEVOPS_PAT = <paste your token here>

# Optional but recommended: the expiry date you chose above, as YYYY-MM-DD. Same silent-lapse
# warning as the other tokens below.
AZURE_DEVOPS_PAT_EXPIRES = <YYYY-MM-DD>

# REQUIRED. Airtable personal access token — create one at https://airtable.com/create/tokens
#   Scopes: ONLY `data.records:read` and `schema.bases:read` — read-only, no write scopes.
#   Access: add EXACTLY TWO bases — the 515 weekly tracker base (AIRTABLE_515_URL) and the FY27
#   Resource Planner base (AIRTABLE_GOALS_URL, if you use goals-summary). Nothing else.
#   Expiration: choose "No expiration." Unlike the Jira/GitHub tokens above, this one isn't meant
#   to be rotated on a schedule, so there's no AIRTABLE_API_KEY_EXPIRES key below.
# Read-only is deliberate: the roll-up drafts a local file and you paste it in yourself, so the
# token never needs write scope. `schema.bases:read` is what supplies your real field names and the
# valid select options (e.g. the Goals list) — without it the draft has to guess them and you fix
# every one by hand. Adding no base under Access is the easy mistake: the token then authenticates
# fine but returns 404 for the base.
AIRTABLE_API_KEY = <paste your token here>
```

## Alternatives to this file

All fetch scripts resolve their token in this order, first hit wins (`JIRA_API_TOKEN` for
`jira_fetch.py`, `GITHUB_TOKEN` for `github_fetch.py`, `AZURE_DEVOPS_PAT` for
`azure_devops_fetch.py`, `AIRTABLE_API_KEY` for `airtable_fetch.py`):

1. The environment variable of that name.
2. The key in this file.
3. The key in `config.md` (works, but mixes the secret in with shareable settings).

The environment variable is the most secure option on a machine you control, but it does **not**
survive a Cowork session — the sandbox home directory is wiped each time — so this file is the
portable choice.

## Rotating or revoking

Tokens expire — Atlassian defaults to about a year, and GitHub tokens carry whatever expiry you
chose. **Airtable is the exception**: set to "No expiration" when created, so it's not expected to
lapse on its own — revoke and replace it only if it's compromised, not on a schedule. When a token
does expire, the fetch script fails with a clear `HTTP 401`. Create a replacement
at the URL above, paste it here, and revoke the old one. Nothing else needs to change.