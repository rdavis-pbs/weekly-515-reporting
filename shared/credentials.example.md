# Local credentials — template

Secrets for the weekly-515-reporting plugin live **here**, separate from `config.md`, so the config
file stays safe to share, paste into a chat, or hand to a colleague.

Copy this file to `.weekly-515-reporting/credentials.md` next to your `config.md` and fill it in.

Treat this file like a password file. It never goes into git, and nothing in the plugin ever prints
its contents.

```
# Atlassian API token — create one at:
#   https://id.atlassian.com/manage-profile/security/api-tokens
# "Create API token" is enough; the token inherits your own Jira permissions, so it can only see
# what you can see. A scoped token also works if you prefer — it needs `read:jira-work` and
# `read:jira-user`. Copy the value immediately; Atlassian shows it only once.
JIRA_API_TOKEN = <paste your token here>

# Optional but recommended: the expiry date you chose above, as YYYY-MM-DD. Tokens lapse silently --
# the script keeps working right up until it returns 401 mid-week -- so recording the date here lets
# jira_fetch.py warn you in the 21 days beforehand. Omit it and the check just stays quiet.
JIRA_API_TOKEN_EXPIRES = <YYYY-MM-DD>

# GitHub personal access token — create one at https://github.com/settings/tokens
#   Classic token:      tick `repo` and `read:org`.
#   Fine-grained token: read-only Contents, Pull requests, Issues, and Metadata on the
#                       repos/orgs you work in.
# The `repo` / Contents permission is what makes PRIVATE repo activity visible. Without it the
# weekly summary silently shows only your public work, which usually looks like "no activity."
GITHUB_TOKEN = <paste your token here>

# Azure DevOps personal access token — create one at:
#   https://dev.azure.com/{org}/_usersSettings/tokens
# Scope: Code (Read) is enough for commits, PRs, and reviews. It inherits your own project
# permissions, so a PAT missing Code (Read) on a project simply doesn't see that project's repos —
# there's no error, just an empty result, which can look like "no activity" if you don't know to
# check scope.
AZURE_DEVOPS_PAT = <paste your token here>

# Optional but recommended: the expiry date you chose above, as YYYY-MM-DD. Same silent-lapse
# warning as the other tokens below.
AZURE_DEVOPS_PAT_EXPIRES = <YYYY-MM-DD>

# Airtable personal access token — create one at https://airtable.com/create/tokens
#   Scopes: `data.records:read` and `schema.bases:read`.
#   Access: add the base your 515 tracker lives in (the app... id in AIRTABLE_515_URL).
# Read-only is deliberate: the roll-up drafts a local file and you paste it in yourself, so the
# token never needs write scope. `schema.bases:read` is what supplies your real field names and the
# valid select options (e.g. the Goals list) — without it the draft has to guess them and you fix
# every one by hand. Adding no base under Access is the easy mistake: the token then authenticates
# fine but returns 404 for the base.
AIRTABLE_API_KEY = <paste your token here>

# Optional, same as above: the expiry you chose, as YYYY-MM-DD, so the collector can warn you ahead
# of a silent lapse instead of failing mid-week.
AIRTABLE_API_KEY_EXPIRES = <YYYY-MM-DD>
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

Tokens expire — Atlassian defaults to about a year, and GitHub and Airtable tokens carry whatever
expiry you chose. When one does, the fetch script fails with a clear `HTTP 401`. Create a replacement
at the URL above, paste it here, and revoke the old one. Nothing else needs to change.