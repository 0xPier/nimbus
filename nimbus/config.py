"""Settings + Keychain access.

G1: the session key lives ONLY in the macOS Keychain (via keyring).
The settings file persists app settings and cached org id — nothing else.
"""

from __future__ import annotations

import json
from pathlib import Path

import keyring

KEYCHAIN_SERVICE = "Nimbus"
KEYCHAIN_ACCOUNT = "sessionKey"

SETTINGS_DIR = Path.home() / "Library" / "Application Support" / "Nimbus"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"

DEFAULTS = {
    "org_id": None,  # cached from GET /api/organizations
    "poll_interval": 300,  # seconds; 600 when idle, 900 after a 429 (FACTS.md)
    "keeper_enabled": False,  # G3: OFF by default
    "keeper_model": "haiku",  # Pier's decision #2
    "keeper_anchor_override": None,  # "HH:MM" manual anchor, else observed reset
    "pet_mode": True,  # animate the desktop cloud widget
    "widget_shown": False,  # desktop pet visible
    "widget_pos": None,  # [x, y] remembered drag position
    "widget_size": None,  # [w, h] remembered resize
    "show_percentage": True,  # % text next to the menu bar cloud
    "first_run_done": False,  # wizard shown once
}


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_PATH.read_text())
    except (OSError, ValueError):
        data = {}
    return {**DEFAULTS, **data}


def save_settings(settings: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")


def get_session_key() -> str | None:
    return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)


def set_session_key(value: str) -> None:
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, value.strip())


def delete_session_key() -> None:
    try:
        keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        pass
