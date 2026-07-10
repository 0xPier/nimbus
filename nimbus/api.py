"""Remote usage fetcher — endpoint verified per G7, see FACTS.md.

G2: GET requests only. G6: any failure raises ApiUnavailable; callers must
degrade honestly, never guess.
"""

from __future__ import annotations

from datetime import datetime

import requests

from . import config
from .models import Snapshot, Window

BASE = "https://claude.ai/api"
TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
)


class ApiUnavailable(Exception):
    """Raised for any reason the endpoint can't give trustworthy data."""


def _headers(session_key: str) -> dict:
    return {
        "Cookie": f"sessionKey={session_key}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }


def _get(path: str, session_key: str) -> dict | list:
    try:
        resp = requests.get(BASE + path, headers=_headers(session_key), timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ApiUnavailable(f"network error: {exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        raise ApiUnavailable(f"HTTP {resp.status_code} from {path}")
    try:
        return resp.json()
    except ValueError as exc:
        raise ApiUnavailable(f"non-JSON response from {path}") from exc


def _resolve_org_id(session_key: str) -> str:
    settings = config.load_settings()
    if settings.get("org_id"):
        return settings["org_id"]
    orgs = _get("/organizations", session_key)
    if not isinstance(orgs, list) or not orgs or "uuid" not in orgs[0]:
        raise ApiUnavailable("could not resolve organization id")
    settings["org_id"] = orgs[0]["uuid"]
    config.save_settings(settings)
    return settings["org_id"]


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


def fetch_usage() -> Snapshot:
    """Fetch the current usage snapshot. Raises ApiUnavailable on any failure."""
    session_key = config.get_session_key()
    if not session_key:
        raise ApiUnavailable("no session key in Keychain")
    org_id = _resolve_org_id(session_key)
    data = _get(f"/organizations/{org_id}/usage", session_key)
    if not isinstance(data, dict):
        raise ApiUnavailable("unexpected usage payload shape")

    five_hour = _parse_window(data.get("five_hour"))
    if five_hour is None:
        raise ApiUnavailable("usage payload missing five_hour window")

    per_model = {}
    for key in ("seven_day_opus", "seven_day_sonnet"):
        win = _parse_window(data.get(key))
        if win:
            per_model[key.removeprefix("seven_day_")] = win

    return Snapshot(
        source="api",
        five_hour=five_hour,
        seven_day=_parse_window(data.get("seven_day")),
        per_model=per_model,
    )
