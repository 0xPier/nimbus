"""Snapshot -> cloud state mapping and reset detection.

Thresholds come from FACTS.md (remaining %: full >=80, partly 79-40,
thin 39-15, discharged <15). Pure functions — no I/O — so the P2/P3
done-when checks can drive them with fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import Snapshot

# state name -> menu bar glyph
ICONS = {
    "full": "☁️",
    "partly": "🌥",
    "thin": "🌫",
    "discharged": "⚡",
    "recharging": "🔌",
    "disconnected": "⛔",
}


def cloud_state(snap: Snapshot, now: datetime | None = None) -> str:
    if snap.source == "disconnected":
        return "disconnected"
    win = snap.five_hour
    if win is None or win.utilization is None:
        # JSONL fallback knows the window, not the % (G6): show it as
        # recharging when a reset is pending, else disconnected-honest.
        return "recharging" if win and win.resets_at else "disconnected"
    remaining = 100.0 - win.utilization
    if remaining < 15:
        now = now or datetime.now(timezone.utc)
        if win.resets_at and win.resets_at > now:
            return "discharged" if remaining > 0 else "recharging"
        return "discharged"
    if remaining < 40:
        return "thin"
    if remaining < 80:
        return "partly"
    return "full"


@dataclass
class ResetDetector:
    """Fires exactly once per reset event (P3 done-when).

    A reset happened when the previously-known resets_at moment has passed.
    Comparing against the last *fired* reset keeps it to one notification
    even though polls repeat.
    """

    _pending_reset: datetime | None = None
    _fired_for: datetime | None = None

    def check(self, snap: Snapshot, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        fired = False
        if (
            self._pending_reset is not None
            and now >= self._pending_reset
            and self._fired_for != self._pending_reset
        ):
            self._fired_for = self._pending_reset
            fired = True
        win = snap.five_hour
        if win is not None and win.resets_at is not None:
            self._pending_reset = win.resets_at
        return fired
