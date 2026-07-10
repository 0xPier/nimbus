"""Local fallback: derive the 5-hour window from Claude Code JSONL logs.

Zero network calls (G1). The JSONL tells us *when* messages were sent, so we
can compute the rolling window's start and reset time. It does NOT tell us the
account's capacity, so utilization stays None here (G6: never fabricate a
percentage) and every window is flagged estimated=True.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Snapshot, Window

PROJECTS_DIR = Path.home() / ".claude" / "projects"
WINDOW = timedelta(hours=5)
LOOKBACK = timedelta(hours=24)  # enough to find the current window


def _recent_timestamps(now: datetime) -> list[datetime]:
    cutoff = now - LOOKBACK
    stamps = []
    if not PROJECTS_DIR.is_dir():
        return stamps
    for path in PROJECTS_DIR.glob("*/*.jsonl"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) < cutoff:
                continue
            with path.open() as fh:
                for line in fh:
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    ts = entry.get("timestamp")
                    if not ts or entry.get("type") not in ("user", "assistant"):
                        continue
                    try:
                        stamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if stamp >= cutoff:
                        stamps.append(stamp)
        except OSError:
            continue
    return sorted(stamps)


def _current_window_start(stamps: list[datetime], now: datetime) -> datetime | None:
    """Replay the rolling-window rule: a window opens at the first message
    after the previous window's reset (FACTS.md)."""
    start = None
    for stamp in stamps:
        if start is None or stamp >= start + WINDOW:
            start = stamp
    if start is not None and now < start + WINDOW:
        return start
    return None


def estimate_usage() -> Snapshot:
    now = datetime.now(timezone.utc)
    stamps = _recent_timestamps(now)
    if not stamps:
        return Snapshot(source="jsonl", detail="no recent Claude Code activity found")
    start = _current_window_start(stamps, now)
    if start is None:
        return Snapshot(
            source="jsonl",
            five_hour=Window(utilization=None, resets_at=None, estimated=True),
            detail="no active 5h window — next window starts on your next message",
        )
    return Snapshot(
        source="jsonl",
        five_hour=Window(utilization=None, resets_at=start + WINDOW, estimated=True),
        detail=f"window opened {start.astimezone():%H:%M} (from local JSONL; utilization unknown)",
    )
