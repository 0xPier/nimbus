"""OAuth usage source — endpoint verified per G7, see FACTS.md.

Reads Claude Code's existing OAuth token from the macOS Keychain item
"Claude Code-credentials". Strictly read-only (G2): Nimbus never refreshes,
rotates, or writes that item. Expired token -> ApiUnavailable, callers fall
back; Claude Code refreshes its own token next time it runs.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime

import requests

from .api import ApiUnavailable, USER_AGENT
from .models import Snapshot, Window

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
BETA_HEADER = "oauth-2025-04-20"
CREDENTIALS_SERVICE = "Claude Code-credentials"
TIMEOUT = 15


def _read_access_token() -> str:
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", CREDENTIALS_SERVICE, "-w"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ApiUnavailable(f"keychain read failed: {exc.__class__.__name__}") from exc
    if out.returncode != 0:
        raise ApiUnavailable("no Claude Code login found in Keychain")
    try:
        creds = json.loads(out.stdout).get("claudeAiOauth") or {}
    except ValueError as exc:
        raise ApiUnavailable("unreadable Claude Code credentials") from exc
    token = creds.get("accessToken")
    expires_at = creds.get("expiresAt")  # ms epoch
    if not token:
        raise ApiUnavailable("Claude Code credentials have no access token")
    if expires_at and expires_at / 1000 < time.time():
        raise ApiUnavailable("Claude Code OAuth token expired (run any claude command to refresh)")
    return token


def _parse_window(raw: dict | None) -> Window | None:
    if not isinstance(raw, dict):
        return None
    utilization = raw.get("utilization")
    resets_at = None
    if raw.get("resets_at"):
        try:
            resets_at = datetime.fromisoformat(raw["resets_at"].replace("Z", "+00:00"))
        except ValueError:
            resets_at = None
    if utilization is None and resets_at is None:
        return None
    return Window(utilization=utilization, resets_at=resets_at, estimated=False)


def fetch_usage_own() -> Snapshot:
    """Fetch usage via Nimbus's own OAuth login (auto-refreshed)."""
    from . import login
    token = login.get_access_token()
    if not token:
        raise ApiUnavailable("Nimbus not connected (run: python -m nimbus.login)")
    snap = _fetch_with_token(token)
    snap.source = "nimbus"
    return snap


def fetch_usage() -> Snapshot:
    """Fetch usage via the Claude Code OAuth token. Raises ApiUnavailable."""
    return _fetch_with_token(_read_access_token())


def _fetch_with_token(token: str) -> Snapshot:
    try:
        resp = requests.get(
            USAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": BETA_HEADER,
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ApiUnavailable(f"network error: {exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        raise ApiUnavailable(f"HTTP {resp.status_code} from oauth usage endpoint")
    try:
        data = resp.json()
    except ValueError as exc:
        raise ApiUnavailable("non-JSON response from oauth usage endpoint") from exc

    five_hour = _parse_window(data.get("five_hour"))
    if five_hour is None:
        raise ApiUnavailable("oauth usage payload missing five_hour window")

    per_model = {}
    for key in ("seven_day_opus", "seven_day_sonnet"):
        win = _parse_window(data.get(key))
        if win:
            per_model[key.removeprefix("seven_day_")] = win

    return Snapshot(
        source="oauth",
        five_hour=five_hour,
        seven_day=_parse_window(data.get("seven_day")),
        per_model=per_model,
    )
