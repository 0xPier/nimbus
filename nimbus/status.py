"""CLI status: `python -m nimbus.status` (P1 done-when check).

Order: API (primary, per Pier's decision #1) -> JSONL fallback -> disconnected.
G6: prints exactly what each source knows; unknowns say so.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timezone

from . import api, config, oauth
from .api import ApiUnavailable
from .jsonl import estimate_usage
from .models import Snapshot, Window


def get_snapshot() -> Snapshot:
    """Source order per FACTS.md: OAuth -> sessionKey API -> JSONL -> disconnected."""
    errors = []
    for source in (oauth.fetch_usage, api.fetch_usage):
        try:
            return source()
        except ApiUnavailable as exc:
            errors.append(str(exc))
    reason = "; ".join(errors)
    fallback = estimate_usage()
    if fallback.five_hour is not None:
        fallback.detail = f"API unavailable ({reason}); {fallback.detail}"
        return fallback
    return Snapshot(source="disconnected", detail=reason)


def _fmt_window(name: str, win: Window | None) -> str:
    if win is None:
        return f"{name}: unknown"
    parts = []
    if win.utilization is not None:
        parts.append(f"{win.utilization:.1f}% used")
    else:
        parts.append("utilization unknown")
    if win.resets_at is not None:
        local = win.resets_at.astimezone()
        remaining = win.resets_at - datetime.now(timezone.utc)
        minutes = max(0, int(remaining.total_seconds() // 60))
        parts.append(f"resets {local:%a %H:%M} (in {minutes // 60}h{minutes % 60:02d}m)")
    else:
        parts.append("reset time unknown")
    if win.estimated:
        parts.append("[estimated from local JSONL]")
    return f"{name}: " + ", ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nimbus.status")
    parser.add_argument("--set-key", action="store_true",
                        help="store the claude.ai sessionKey in the macOS Keychain")
    parser.add_argument("--delete-key", action="store_true",
                        help="remove the sessionKey from the Keychain")
    args = parser.parse_args(argv)

    if args.set_key:
        key = getpass.getpass("sessionKey (sk-ant-sid...): ")
        if not key.strip():
            print("empty key, nothing stored")
            return 1
        config.set_session_key(key)
        print("stored in Keychain (service 'Nimbus')")
        return 0
    if args.delete_key:
        config.delete_session_key()
        print("removed from Keychain")
        return 0

    snap = get_snapshot()
    if snap.source == "disconnected":
        print("disconnected")
        if snap.detail:
            print(f"  reason: {snap.detail}")
        return 2

    print(f"source: {snap.source}")
    print(_fmt_window("5-hour window", snap.five_hour))
    print(_fmt_window("7-day window", snap.seven_day))
    for model, win in snap.per_model.items():
        print(_fmt_window(f"7-day ({model})", win))
    if snap.detail:
        print(f"note: {snap.detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
