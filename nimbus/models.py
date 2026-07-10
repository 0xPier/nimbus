"""Data model for usage snapshots.

G1: these objects hold only utilization %, reset timestamps, and a source tag.
G6: unknown values stay None — never fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Window:
    """One rate-limit window (5-hour or 7-day)."""

    utilization: float | None  # 0-100, None = unknown
    resets_at: datetime | None  # tz-aware, None = unknown
    estimated: bool = False  # True when derived from JSONL, not the API


@dataclass
class Snapshot:
    """What Nimbus knows right now. source: 'api' | 'jsonl' | 'disconnected'."""

    source: str
    five_hour: Window | None = None
    seven_day: Window | None = None
    per_model: dict[str, Window] = field(default_factory=dict)
    detail: str = ""  # human-readable note (e.g. why disconnected)
