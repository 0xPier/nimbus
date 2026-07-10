"""First-run wizard — shown once after install.

Walks a new user through: what the cloud shows, which data source is live,
the desktop pet, and the (opt-in, G3) window keeper. Every step defaults to
the safe choice; the keeper step shows the usage-cost disclosure and is OFF
unless explicitly enabled.
"""

from __future__ import annotations

import rumps

from . import config, keeper

WELCOME = (
    "Nimbus lives in your menu bar and shows Claude usage as a cloud:\n\n"
    "☁ orange & full — plenty of usage left\n"
    "☁ draining to grey — the 5-hour window is filling up\n"
    "⚡ bolt — discharged (<15% left)\n"
    "⚡ green bolt — locked, recharging until the reset\n"
    "／ red slash — disconnected (Nimbus never guesses numbers)\n\n"
    "It notifies you the moment usage is available again."
)


def _source_step() -> str:
    from .status import get_snapshot
    snap = get_snapshot()
    if snap.source == "oauth":
        return ("Connected via your Claude Code login (read-only) — live "
                "percentages are flowing. Nothing to set up.")
    if snap.source == "api":
        return "Connected via your claude.ai session key — live percentages are flowing."
    if snap.source == "jsonl":
        return ("No live connection yet — showing window timing estimated from "
                "local Claude Code logs.\n\nFor live percentages, either log in "
                "to the Claude CLI (`claude` → /login) or store a claude.ai "
                "session key:\n  python -m nimbus.status --set-key")
    return ("Currently disconnected. Log in to the Claude CLI (`claude` → /login) "
            "or store a session key with:  python -m nimbus.status --set-key")


def run_if_first_launch(app) -> None:
    """`app` is the NimbusApp; used to flip toggles the user opts into."""
    settings = config.load_settings()
    if settings.get("first_run_done"):
        return

    rumps.alert(title="Welcome to Nimbus ☁️", message=WELCOME, ok="Next")
    rumps.alert(title="Data source", message=_source_step(), ok="Next")

    if rumps.alert(title="Desktop cloud pet",
                   message="Want a floating cloud on your desktop? Drag it anywhere, "
                           "resize it from any edge. You can toggle it any time from "
                           "the menu bar.",
                   ok="Show the pet", cancel="Not now") == 1:
        settings = config.load_settings()
        settings["widget_shown"] = True
        config.save_settings(settings)
        app.item_widget.state = True
        app._show_widget()

    # G3: keeper stays OFF unless explicitly enabled here, disclosure shown
    if rumps.alert(title="Window keeper (optional)", message=keeper.DISCLOSURE,
                   ok="Keep it off", cancel="Enable keeper") == 0:
        settings = config.load_settings()
        settings["keeper_enabled"] = True
        config.save_settings(settings)
        app.item_keeper.state = True

    settings = config.load_settings()
    settings["first_run_done"] = True
    config.save_settings(settings)
