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

# GitHub personal access token — create one at https://github.com/settings/tokens
#   Classic token:      tick `repo` and `read:org`.
#   Fine-grained token: read-only Contents, Pull requests, Issues, and Metadata on the
#                       repos/orgs you work in.
# The `repo` / Contents permission is what makes PRIVATE repo activity visible. Without it the
# weekly summary silently shows only your public work, which usually looks like "no activity."
GITHUB_TOKEN = <paste your token here>
```

## Alternatives to this file

Both fetch scripts resolve their token in this order, first hit wins (`JIRA_API_TOKEN` for
`jira_fetch.py`, `GITHUB_TOKEN` for `github_fetch.py`):

1. The environment variable of that name.
2. The key in this file.
3. The key in `config.md` (works, but mixes the secret in with shareable settings).

The environment variable is the most secure option on a machine you control, but it does **not**
survive a Cowork session — the sandbox home directory is wiped each time — so this file is the
portable choice.

## Rotating or revoking

Tokens expire — Atlassian defaults to about a year, and GitHub tokens carry whatever expiry you
chose. When one does, the fetch script fails with a clear `HTTP 401`. Create a replacement at the URL
above, paste it here, and revoke the old one. Nothing else needs to change.