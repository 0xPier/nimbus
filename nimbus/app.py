"""Nimbus menu bar app (rumps, G5).

Run: python -m nimbus.app          — live monitoring
     python -m nimbus.app --debug  — cycle fixture states (G6: debug only)

Menu bar: drawn cloud icon (orange charge drains to grey as usage is used)
plus the remaining %. Optional desktop pet: a movable floating cloud widget.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import rumps
from AppKit import NSApplication

from . import config, keeper, notify, status
from .draw import cloud_image
from .models import Snapshot, Window
from .state import ResetDetector, cloud_state
from .widget import CloudWidget

POLL_ACTIVE = 300  # override via settings.json "poll_interval"
POLL_IDLE = 600  # when discharged/recharging — nothing to watch closely
POLL_BACKOFF = 900  # after a rate-limit (HTTP 429) — be a polite client
STALE_GRACE = 900  # keep showing last good live data for up to 15 min, labeled stale
ICON_SIZE = 18.0


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


def _countdown(win: Window | None) -> str:
    if win is None or win.resets_at is None:
        return ""
    mins = max(0, int((win.resets_at - datetime.now(timezone.utc)).total_seconds() // 60))
    return f"resets in {mins // 60}h{mins % 60:02d}m"


def _fmt_line(name: str, win: Window | None) -> str:
    if win is None:
        return f"{name}: unknown"
    pct = f"{win.utilization:.0f}% used" if win.utilization is not None else "?% (estimated)"
    tail = _countdown(win)
    return f"{name}: {pct}" + (f" · {tail}" if tail else "")


class NimbusApp(rumps.App):
    def __init__(self, debug: bool = False):
        super().__init__("Nimbus", quit_button="Quit Nimbus")
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
        self.subtitle = ""
        self.widget: CloudWidget | None = None
        self.last_good: tuple[Snapshot, datetime] | None = None
        self.auth_alerted = False  # one notification per live-data loss

        settings = config.load_settings()
        self.item_5h = rumps.MenuItem("5-hour: …")
        self.item_7d = rumps.MenuItem("7-day: …")
        self.item_src = rumps.MenuItem("source: …")
        self.item_keeper = rumps.MenuItem("Window keeper (1 ping per reset)",
                                          callback=self.toggle_keeper)
        self.item_keeper.state = bool(settings.get("keeper_enabled"))
        self.item_widget = rumps.MenuItem("Show desktop cloud (pet)",
                                          callback=self.toggle_widget)
        self.item_widget.state = bool(settings.get("widget_shown"))
        self.item_pct = rumps.MenuItem("Show percentage in menu bar",
                                       callback=self.toggle_percentage)
        self.item_pct.state = bool(settings.get("show_percentage", True))
        self.item_notify = rumps.MenuItem("Notify when usage resets",
                                          callback=self._make_toggle("notify_on_reset"))
        self.item_notify.state = bool(settings.get("notify_on_reset", True))
        self.item_anim = rumps.MenuItem("Reset animation (recharge sweep)",
                                        callback=self._make_toggle("reset_animation"))
        self.item_anim.state = bool(settings.get("reset_animation", True))
        self.menu = [self.item_5h, self.item_7d, self.item_src, None,
                     rumps.MenuItem("Refresh now", callback=lambda _: self.refresh()),
                     rumps.MenuItem("Connect live data (browser login)…",
                                    callback=self.connect_live),
                     self.item_keeper, self.item_widget, self.item_pct,
                     self.item_notify, self.item_anim, None]

        interval = 3 if debug else POLL_ACTIVE
        self.timer = rumps.Timer(lambda _: self.refresh(), interval)
        self.timer.start()
        self.anim_timer = rumps.Timer(self._animate, 2)
        self.anim_timer.start()
        self.refresh()
        if settings.get("widget_shown"):
            self._show_widget()
        if not debug:
            self.wizard_timer = rumps.Timer(self._run_wizard_once, 1.5)
            self.wizard_timer.start()

    def _run_wizard_once(self, timer):
        timer.stop()
        from .wizard import run_if_first_launch
        run_if_first_launch(self)

    # -- rendering ---------------------------------------------------------
    def _render(self):
        img = cloud_image(ICON_SIZE, self.remaining, self.state)
        img.setTemplate_(False)
        self._icon_nsimage = img
        try:
            self._nsapp.setStatusBarIcon()
        except AttributeError:
            pass  # before run() — initializeStatusBar picks it up
        show_pct = config.load_settings().get("show_percentage", True)
        self.title = (f" {self.remaining:.0f}%"
                      if show_pct and self.remaining is not None else "")
        if self.widget is not None:
            self.widget.update(self.remaining, self.state, self.subtitle)

    def _animate(self, _):
        # gentle bobbing for the desktop pet only; menu bar icon stays still
        if self.widget is not None:
            self.widget.update(self.remaining, self.state, self.subtitle, animate=True)

    # -- polling ---------------------------------------------------------
    def refresh(self):
        if self.fixtures is not None:
            snap = self.fixtures[self.fixture_i % len(self.fixtures)]
            self.fixture_i += 1
        else:
            snap = status.get_snapshot()
        now = datetime.now(timezone.utc)
        rate_limited = "429" in snap.detail
        if snap.source in ("nimbus", "oauth", "api"):
            self.last_good = (snap, now)
            self.auth_alerted = False
        elif "expired" in snap.detail and not self.auth_alerted and not self.debug:
            self.auth_alerted = True
            notify.send("Live usage data lost — Claude login expired. "
                        "Run `claude` in a terminal to reconnect.")
        if snap.source not in ("nimbus", "oauth", "api") and self.last_good is not None:
            # transient API failure: keep last live numbers, honestly labeled
            good, ts = self.last_good
            age = (now - ts).total_seconds()
            if age < STALE_GRACE and good.five_hour and good.five_hour.resets_at and \
                    good.five_hour.resets_at > now:
                good.detail = f"live data {int(age // 60)}m old" + \
                    (" (rate-limited, backing off)" if rate_limited else " (API unavailable)")
                snap = good
        self.state = cloud_state(snap)
        win = snap.five_hour
        self.remaining = (100.0 - win.utilization) if win and win.utilization is not None else None
        self.subtitle = _countdown(win) or snap.source
        self._render()
        if self.widget is not None:
            self.widget.save_geometry()  # keep drag/resize across restarts
        self.item_5h.title = _fmt_line("5-hour", snap.five_hour)
        self.item_7d.title = _fmt_line("7-day", snap.seven_day)
        src = f"source: {snap.source}"
        if snap.detail:
            src += f" — {snap.detail}"
        self.item_src.title = src + (" [debug]" if self.debug else "")

        # adaptive poll interval (FACTS.md); polite backoff on rate-limit
        if not self.debug:
            active = int(config.load_settings().get("poll_interval") or POLL_ACTIVE)
            if rate_limited:
                want = max(POLL_BACKOFF, active)
            elif self.state in ("discharged", "recharging"):
                want = max(POLL_IDLE, active)
            else:
                want = active
            if self.timer.interval != want:
                self.timer.stop()
                self.timer = rumps.Timer(lambda _: self.refresh(), want)
                self.timer.start()

        if self.detector.check(snap):
            self.on_reset()

    def _make_toggle(self, key: str):
        def handler(item):
            settings = config.load_settings()
            settings[key] = not settings.get(key, True)
            config.save_settings(settings)
            item.state = settings[key]
        return handler

    # -- reset event (P3 + P4) -------------------------------------------
    def on_reset(self):
        settings = config.load_settings()
        if settings.get("notify_on_reset", True):
            notify.send(notify.RESET_MESSAGE)
        if settings.get("reset_animation", True):
            self._start_reset_animation()
        self.keeper_pings_this_reset = 0
        if settings.get("keeper_enabled") and not self.debug:
            self.keeper_ping()

    # -- recharge sweep: the cloud visibly refills from empty to current --
    def _start_reset_animation(self):
        self._sweep_step = 0
        self._sweep_timer = rumps.Timer(self._sweep_frame, 0.12)
        self._sweep_timer.start()

    def _sweep_frame(self, timer):
        steps = 24
        self._sweep_step += 1
        if self._sweep_step > steps:
            timer.stop()
            self._render()  # settle on the real value
            return
        target = self.remaining if self.remaining is not None else 100.0
        value = target * (self._sweep_step / steps)
        img = cloud_image(ICON_SIZE, value, "full")
        img.setTemplate_(False)
        self._icon_nsimage = img
        try:
            self._nsapp.setStatusBarIcon()
        except AttributeError:
            pass
        if self.widget is not None:
            self.widget.update(value, "full", "recharged ⚡", animate=False)

    def keeper_ping(self):
        if self.keeper_pings_this_reset >= 2:  # initial + one retry, never more (G3)
            return
        self.keeper_pings_this_reset += 1
        if keeper.ping():
            self.refresh()  # confirm the new window started
        elif self.keeper_pings_this_reset == 1:
            # rumps timers fire immediately on start, so gate on wall clock
            self._retry_at = datetime.now(timezone.utc) + timedelta(seconds=keeper.RETRY_DELAY)
            self.retry_timer = rumps.Timer(self._retry_once, 30)
            self.retry_timer.start()
        else:
            notify.send("Keeper ping failed twice — giving up until next reset")

    def _retry_once(self, timer):
        if datetime.now(timezone.utc) < self._retry_at:
            return  # not due yet — keep ticking
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

    def connect_live(self, _):
        import webbrowser

        from . import login

        url, verifier, state = login.build_authorize()
        webbrowser.open(url)
        window = rumps.Window(
            title="Connect Nimbus",
            message="Approve in the browser (read-only usage scope), then paste "
                    "the code the page shows you:",
            default_text="", ok="Connect", cancel="Cancel", dimensions=(320, 24))
        resp = window.run()
        if resp.clicked != 1 or not resp.text.strip():
            return
        try:
            ok = login.exchange(resp.text, verifier, state)
        except ValueError:
            ok = False
        notify.send("Nimbus connected — live data flowing" if ok
                    else "Login didn't complete — try again from the menu")
        if ok:
            self.refresh()

    def _show_widget(self):
        if self.widget is None:
            self.widget = CloudWidget()
        self.widget.update(self.remaining, self.state, self.subtitle, animate=False)
        self.widget.show()

    def toggle_percentage(self, item):
        settings = config.load_settings()
        settings["show_percentage"] = not settings.get("show_percentage", True)
        config.save_settings(settings)
        item.state = settings["show_percentage"]
        self._render()

    def toggle_widget(self, item):
        settings = config.load_settings()
        shown = not settings.get("widget_shown")
        settings["widget_shown"] = shown
        config.save_settings(settings)
        item.state = shown
        if shown:
            self._show_widget()
        elif self.widget is not None:
            self.widget.hide()


def main():
    NimbusApp(debug="--debug" in sys.argv).run()


if __name__ == "__main__":
    main()
