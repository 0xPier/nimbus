"""Nimbus menu bar app (rumps, G5).

Run: python -m nimbus.app          — live monitoring
     python -m nimbus.app --debug  — cycle fixture states (G6: debug only)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import rumps
from AppKit import NSApplication

from . import config, keeper, notify, status
from .models import Snapshot, Window
from .state import ICONS, ResetDetector, cloud_state

POLL_ACTIVE = 120
POLL_IDLE = 300  # when discharged/recharging — nothing to watch closely

# pet-mode animation frames per state (menu bar cycles these every 2s)
FRAMES = {
    "full": ["☁️", "🌤"],
    "partly": ["🌥", "☁️"],
    "thin": ["🌫", "🌥"],
    "discharged": ["⚡", "🌩"],
    "recharging": ["🔌", "⚡"],
    "disconnected": ["⛔"],
}


def _debug_fixtures() -> list[Snapshot]:
    """One snapshot per cloud state — allowed only behind --debug (G6)."""
    now = datetime.now(timezone.utc)
    reset = now + timedelta(hours=2)

    def snap(util, source="api"):
        return Snapshot(source=source,
                        five_hour=Window(utilization=util, resets_at=reset))

    return [
        snap(5.0),                       # full
        snap(50.0),                      # partly
        snap(75.0),                      # thin
        snap(95.0),                      # discharged
        Snapshot(source="jsonl", five_hour=Window(None, reset, estimated=True)),  # recharging
        Snapshot(source="disconnected", detail="debug fixture"),  # disconnected
    ]


def _fmt_line(name: str, win: Window | None) -> str:
    if win is None:
        return f"{name}: unknown"
    pct = f"{win.utilization:.0f}% used" if win.utilization is not None else "?% (estimated)"
    if win.resets_at:
        mins = max(0, int((win.resets_at - datetime.now(timezone.utc)).total_seconds() // 60))
        return f"{name}: {pct} · resets in {mins // 60}h{mins % 60:02d}m"
    return f"{name}: {pct}"


class NimbusApp(rumps.App):
    def __init__(self, debug: bool = False):
        super().__init__("Nimbus", title=ICONS["disconnected"], quit_button="Quit Nimbus")
        # menu-bar only: no dock icon (NSApplicationActivationPolicyAccessory)
        NSApplication.sharedApplication().setActivationPolicy_(1)
        self.debug = debug
        self.detector = ResetDetector()
        self.keeper_pings_this_reset = 0
        self.retry_timer: rumps.Timer | None = None
        self.fixtures = _debug_fixtures() if debug else None
        self.fixture_i = 0
        self.state = "disconnected"
        self.remaining: float | None = None
        self.frame_i = 0

        settings = config.load_settings()
        self.item_5h = rumps.MenuItem("5-hour: …")
        self.item_7d = rumps.MenuItem("7-day: …")
        self.item_src = rumps.MenuItem("source: …")
        self.item_keeper = rumps.MenuItem("Window keeper (1 ping per reset)",
                                          callback=self.toggle_keeper)
        self.item_keeper.state = bool(settings.get("keeper_enabled"))
        self.item_pet = rumps.MenuItem("Animate cloud (pet mode)", callback=self.toggle_pet)
        self.item_pet.state = bool(settings.get("pet_mode", True))
        self.menu = [self.item_5h, self.item_7d, self.item_src, None,
                     rumps.MenuItem("Refresh now", callback=lambda _: self.refresh()),
                     self.item_keeper, self.item_pet, None]

        interval = 3 if debug else POLL_ACTIVE
        self.timer = rumps.Timer(lambda _: self.refresh(), interval)
        self.timer.start()
        self.anim_timer = rumps.Timer(self._animate, 2)
        self.anim_timer.start()
        self.refresh()

    # -- menu bar title ----------------------------------------------------
    def _set_title(self):
        pet = bool(config.load_settings().get("pet_mode", True))
        frames = FRAMES[self.state] if pet else [ICONS[self.state]]
        glyph = frames[self.frame_i % len(frames)]
        pct = f" {self.remaining:.0f}%" if self.remaining is not None else ""
        self.title = f"{glyph}{pct}"

    def _animate(self, _):
        self.frame_i += 1
        self._set_title()

    # -- polling ---------------------------------------------------------
    def refresh(self):
        if self.fixtures is not None:
            snap = self.fixtures[self.fixture_i % len(self.fixtures)]
            self.fixture_i += 1
        else:
            snap = status.get_snapshot()
        state = cloud_state(snap)
        self.state = state
        win = snap.five_hour
        self.remaining = (100.0 - win.utilization) if win and win.utilization is not None else None
        self._set_title()
        self.item_5h.title = _fmt_line("5-hour", snap.five_hour)
        self.item_7d.title = _fmt_line("7-day", snap.seven_day)
        self.item_src.title = f"source: {snap.source}" + (" [debug]" if self.debug else "")

        # adaptive poll interval (FACTS.md)
        if not self.debug:
            want = POLL_IDLE if state in ("discharged", "recharging") else POLL_ACTIVE
            if self.timer.interval != want:
                self.timer.stop()
                self.timer = rumps.Timer(lambda _: self.refresh(), want)
                self.timer.start()

        if self.detector.check(snap):
            self.on_reset()

    # -- reset event (P3 + P4) -------------------------------------------
    def on_reset(self):
        notify.send(notify.RESET_MESSAGE)
        self.keeper_pings_this_reset = 0
        if config.load_settings().get("keeper_enabled") and not self.debug:
            self.keeper_ping()

    def keeper_ping(self):
        if self.keeper_pings_this_reset >= 2:  # initial + one retry, never more (G3)
            return
        self.keeper_pings_this_reset += 1
        if keeper.ping():
            self.refresh()  # confirm the new window started
        elif self.keeper_pings_this_reset == 1:
            self.retry_timer = rumps.Timer(self._retry_once, keeper.RETRY_DELAY)
            self.retry_timer.start()
        else:
            notify.send("Keeper ping failed twice — giving up until next reset")

    def _retry_once(self, timer):
        timer.stop()
        self.keeper_ping()

    # -- settings ----------------------------------------------------------
    def toggle_keeper(self, item):
        settings = config.load_settings()
        if not settings.get("keeper_enabled"):
            # G3: explicit opt-in with cost disclosure
            resp = rumps.alert(title="Enable window keeper?", message=keeper.DISCLOSURE,
                               ok="Enable", cancel="Cancel")
            if resp != 1:
                return
            settings["keeper_enabled"] = True
        else:
            settings["keeper_enabled"] = False
        config.save_settings(settings)
        item.state = settings["keeper_enabled"]

    def toggle_pet(self, item):
        settings = config.load_settings()
        settings["pet_mode"] = not settings.get("pet_mode", True)
        config.save_settings(settings)
        item.state = settings["pet_mode"]
        self._set_title()


def main():
    NimbusApp(debug="--debug" in sys.argv).run()


if __name__ == "__main__":
    main()
