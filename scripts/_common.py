"""
Shared helpers for the weekly-515-reporting fetch scripts (jira_fetch.py, github_fetch.py).

Stdlib only -- no pip installs. Lives beside its callers so a plain `import _common` works.

The week-anchoring rule here is the single Python implementation. It mirrors the shell snippet in
shared/work-week.md; if you change one, change the other, or collectors will disagree about which
folder they are writing into.
"""

import datetime
import glob
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


# --------------------------------------------------------------------------- output


def force_utf8_output():
    """Make stdout/stderr tolerate any character the APIs hand back.

    On Windows these default to a legacy codepage (cp1252 here), so a single emoji or CJK character
    in a commit message or Jira comment raises UnicodeEncodeError -- and it would do so *after* the
    JSON artifact was already written, turning a successful fetch into an apparent crash. The JSON
    itself is always written as UTF-8 and is unaffected; this only concerns the console digest.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass                                    # older Python or an already-wrapped stream


def die(message, code=2):
    sys.stderr.write("ERROR: %s\n" % message)
    sys.exit(code)


def note(message):
    """Progress/diagnostics go to stderr so stdout stays a clean digest."""
    sys.stderr.write("%s\n" % message)


def clip(text, limit):
    if text is None:
        return None
    text = str(text).replace("\r\n", "\n").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " ...[truncated]"


# --------------------------------------------------------------------------- config


def config_candidates():
    """Search order matching shared/work-week.md: Cowork mounts, then up from CWD, then home.

    The walk up from CWD matters: without it, running from a subdirectory (the plugin folder, a
    dated report folder) misses the workspace config and silently falls through to the legacy
    home-directory location, which may hold different values.
    """
    home = os.path.expanduser("~")
    candidates = sorted(glob.glob(os.path.join(home, "mnt", "*", ".weekly-515-reporting", "config.md")))

    d = os.path.abspath(os.getcwd())
    while True:
        candidates.append(os.path.join(d, ".weekly-515-reporting", "config.md"))
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent

    candidates.append(os.path.join(home, ".weekly-515-reporting", "config.md"))

    seen, ordered = set(), []
    for c in candidates:
        n = os.path.normcase(os.path.normpath(c))
        if n not in seen:
            seen.add(n)
            ordered.append(c)
    return ordered


def find_config(explicit=None):
    """Locate config.md, warning if more than one exists so a stale copy can't shadow silently."""
    if explicit:
        if not os.path.isfile(explicit):
            die("--config path not found: %s" % explicit)
        return explicit

    candidates = config_candidates()
    found = [c for c in candidates if os.path.isfile(c)]

    if not found:
        die(
            "No config found. Looked in:\n  " + "\n  ".join(candidates) +
            "\nCreate <your folder>/.weekly-515-reporting/config.md from the plugin's "
            "shared/config.example.md, or pass --config."
        )

    if len(found) > 1:
        note(
            "WARNING: %d config files found; using the first." % len(found) +
            "\n" + "".join("  %s %s\n" % ("USING ->" if c == found[0] else "        ", c) for c in found) +
            "  Delete the ones you don't want, or pass --config, to remove the ambiguity."
        )
    return found[0]


def parse_kv(path):
    """Parse `KEY = value` lines from a markdown config file, ignoring comments and fences."""
    values = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("```"):
                continue
            m = re.match(r"^([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", line)
            if m:
                val = m.group(2).strip()
                # An unfilled template placeholder is not a value.
                if val.startswith("<") and val.endswith(">"):
                    continue
                values[m.group(1)] = val
    return values


def credentials_path(config_path):
    return os.path.join(os.path.dirname(config_path), "credentials.md")


def resolve_secret(key, config_path, config, help_text=""):
    """Resolve a secret: environment variable, then credentials.md, then config.md.

    Returns (value, source_description). Exits with guidance if nothing is found.
    """
    env = os.environ.get(key, "").strip()
    if env:
        return env, "%s environment variable" % key

    cred_path = credentials_path(config_path)
    if os.path.isfile(cred_path):
        cred = parse_kv(cred_path)
        if cred.get(key):
            return cred[key], cred_path

    if config.get(key):
        return config[key], config_path

    die(
        "No %s found.\n%s\nPut it in %s as:\n  %s = <your value>\n"
        "(or set the %s environment variable)." % (key, help_text, cred_path, key, key)
    )


# --------------------------------------------------------------------------- weeks


def anchor_friday(today):
    """
    The reporting week's Friday -- the name of the output folder every collector writes into.

    Mon or Tue  -> last week's Friday (you're still reporting on the week that ended).
    Wed .. Sun  -> this week's Friday.

    Weeks are Monday-start, so on Sat/Sun "this week's Friday" is the Friday just passed.
    Must stay in sync with the snippet in shared/work-week.md.
    """
    wd = today.weekday()                                    # Mon=0 .. Sun=6
    friday = today - datetime.timedelta(days=wd - 4)
    if wd <= 1:                                             # Monday, Tuesday
        friday -= datetime.timedelta(days=7)
    return friday


def workweek_window(friday):
    """Mon-Fri window for the anchor Friday. Used by most collectors."""
    return friday - datetime.timedelta(days=4), friday


def friday_to_friday_window(friday):
    """7-day Fri->Fri window ending on the anchor Friday. Used by Jira."""
    return friday - datetime.timedelta(days=7), friday


def label_for(start, end):
    return "%s - %s" % (start.strftime("%b %d"), end.strftime("%b %d, %Y"))


def resolve_window(args, friday_fn):
    """Honor --start/--end if given, else derive the window from today via friday_fn."""
    if bool(args.start) != bool(args.end):
        die("--start and --end must be given together.")
    if args.start:
        try:
            start = datetime.date.fromisoformat(args.start)
            end = datetime.date.fromisoformat(args.end)
        except ValueError as e:
            die("Bad --start/--end (expected YYYY-MM-DD): %s" % e)
        if start > end:
            die("--start is after --end.")
        return start, end
    return friday_fn(anchor_friday(datetime.date.today()))


def in_window(timestamp, start_iso, end_iso):
    """Compare an ISO timestamp on its date part only.

    Date-granular comparison sidesteps timezone-offset parsing differences across Python versions,
    and the reporting windows are themselves day-granular.
    """
    if not timestamp:
        return False
    return start_iso <= timestamp[:10] <= end_iso


# --------------------------------------------------------------------------- output paths


def output_path(explicit, config_path, config, end_iso, filename):
    """<OUTPUT_ROOT or the config's own folder>/<END>/<filename>, creating the folder."""
    if explicit:
        path = explicit
    else:
        root = config.get("OUTPUT_ROOT") or os.path.dirname(os.path.dirname(config_path))
        path = os.path.join(root, end_iso, filename)

    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    return path


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- http


class ApiError(Exception):
    pass


class HttpClient(object):
    """Minimal JSON-over-HTTPS client with retry on transient failures."""

    def __init__(self, base, headers, insecure=False, verbose=False):
        self.base = base.rstrip("/")
        self.headers = dict(headers)
        self.verbose = verbose
        self.ctx = None
        if insecure:
            self.ctx = ssl.create_default_context()
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE

    def auth_error(self, code, detail):
        """Override to give a service-specific message for 401/403."""
        return ApiError("Authentication failed (HTTP %d).\n%s" % (code, detail))

    def request(self, path, method="GET", body=None, params=None, attempts=4, with_headers=False):
        url = path if path.startswith("http") else self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None

        last = None
        for attempt in range(attempts):
            req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
            try:
                if self.verbose:
                    note("  %s %s" % (method, url))
                with urllib.request.urlopen(req, timeout=60, context=self.ctx) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
                    return (parsed, dict(resp.headers)) if with_headers else parsed
            except urllib.error.HTTPError as e:
                detail = ""
                try:
                    detail = e.read().decode("utf-8", "replace")[:400]
                except Exception:
                    pass

                retry_after = e.headers.get("Retry-After")
                if e.code in (401, 403) and not retry_after:
                    raise self.auth_error(e.code, detail)
                if (e.code in (429, 500, 502, 503, 504) or retry_after) and attempt < attempts - 1:
                    wait = int(retry_after or (2 ** attempt))
                    note("  HTTP %d -- retrying in %ds" % (e.code, wait))
                    time.sleep(min(wait, 120))
                    last = e
                    continue
                raise ApiError("HTTP %d for %s %s\n%s" % (e.code, method, url, detail))
            except urllib.error.URLError as e:
                if attempt < attempts - 1:
                    time.sleep(2 ** attempt)
                    last = e
                    continue
                raise ApiError(
                    "Could not reach %s (%s). If your network inspects TLS, retry with --insecure."
                    % (self.base, e)
                )
        raise ApiError("Request failed after %d attempts: %s" % (attempts, last))