"""Window keeper — G3: opt-in, exactly one ping per reset event, one retry max.

The ping goes exclusively through the headless CLI (G4):
    claude -p "Reply with exactly: ok" --model <model>
Log contains timestamps and outcomes only — never message content beyond the
fixed prompt (G1).
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import config

PROMPT = "Reply with exactly: ok"
TIMEOUT = 60  # seconds (FACTS.md)
RETRY_DELAY = 300  # one retry after 5 min, then give up (G3)
LOG_PATH = config.SETTINGS_DIR / "keeper.log"

# Toggle copy shown in settings (G3: must disclose the cost)
DISCLOSURE = (
    "Window keeper sends ONE minimal message ('ok' ping) at each reset "
    "to pin the 5-hour window to a fixed schedule. This consumes a small "
    "amount of your usage every cycle."
)


def _log(event: str) -> None:
    config.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG_PATH.open("a") as fh:
        fh.write(f"{stamp} {event}\n")


def ping(claude_bin: str = "claude") -> bool:
    """One keeper ping. Returns True on success. Never call in a loop —
    scheduling (and the single retry) is the caller's job."""
    settings = config.load_settings()
    model = settings.get("keeper_model", "haiku")
    try:
        result = subprocess.run(
            [claude_bin, "-p", PROMPT, "--model", model],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except FileNotFoundError:
        _log("ping failed: claude CLI not on PATH")
        return False
    except subprocess.TimeoutExpired:
        _log(f"ping timeout after {TIMEOUT}s (model={model})")
        return False
    ok = result.returncode == 0
    _log(f"ping {'ok' if ok else f'failed rc={result.returncode}'} (model={model})")
    return ok
