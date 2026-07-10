"""macOS notifications via osascript (stdlib-only, G5).

Content is fixed copy + percentages only — never conversation data (G1).
"""

from __future__ import annotations

import subprocess

RESET_TITLE = "Nimbus"
RESET_MESSAGE = "☁️ Cloud recharged — usage available"


def send(message: str, title: str = RESET_TITLE) -> None:
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass  # a failed notification must never crash the monitor
