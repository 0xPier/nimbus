"""Nimbus's own OAuth login (Pier decision #5, endpoints verified per G7).

One-time browser approval with read-only scope `user:profile`. Tokens live in
Nimbus's OWN Keychain item (service "Nimbus", account "oauth") and Nimbus
refreshes them itself. Claude Code's credentials are never read here, let
alone written (G2).

Run: python -m nimbus.login
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import threading
import time
import urllib.parse
import webbrowser

import keyring
import requests

AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"  # public PKCE client
SCOPE = "user:profile"  # read-only usage
PORTS = (1456, 1458)
CALLBACK_PATH = "/callback"

KEYCHAIN_SERVICE = "Nimbus"
KEYCHAIN_ACCOUNT = "oauth"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def load_tokens() -> dict | None:
    raw = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def save_tokens(tokens: dict) -> None:
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, json.dumps(tokens))


def delete_tokens() -> None:
    try:
        keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        pass


def _store_response(data: dict) -> dict:
    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expires_at": time.time() + float(data.get("expires_in", 3600)),
    }
    save_tokens(tokens)
    return tokens


def refresh(tokens: dict) -> dict | None:
    """Refresh Nimbus's own token. Returns new tokens or None."""
    if not tokens.get("refresh_token"):
        return None
    try:
        resp = requests.post(TOKEN_URL, json={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": CLIENT_ID,
        }, timeout=15)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        return _store_response(resp.json())
    except (ValueError, KeyError):
        return None


def get_access_token() -> str | None:
    """Valid access token from Nimbus's own login, auto-refreshed."""
    tokens = load_tokens()
    if tokens is None:
        return None
    if time.time() < tokens.get("expires_at", 0) - 60:
        return tokens["access_token"]
    tokens = refresh(tokens)
    return tokens["access_token"] if tokens else None


class _Callback(http.server.BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        _Callback.result = dict(urllib.parse.parse_qsl(parsed.query))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Nimbus is connected &#9729;&#65039;</h2>"
                         b"You can close this tab.")
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args):
        pass  # no request logging (G1)


def login(timeout: int = 300) -> bool:
    """Full PKCE browser flow. Returns True on success."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = _b64url(secrets.token_bytes(16))

    server = None
    port = None
    for candidate in PORTS:
        try:
            server = http.server.HTTPServer(("127.0.0.1", candidate), _Callback)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        print("ports 1456/1458 busy — close whatever is using them and retry")
        return False

    redirect_uri = f"http://localhost:{port}{CALLBACK_PATH}"
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })
    url = f"{AUTHORIZE_URL}?{params}"
    print("Opening browser for Claude approval (read-only usage scope)…")
    print(f"If it doesn't open, visit:\n  {url}")
    webbrowser.open(url)

    server.timeout = timeout
    _Callback.result = {}
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    thread.join(timeout)
    server.shutdown()

    result = _Callback.result
    if not result:
        print("timed out waiting for the browser callback")
        return False
    if result.get("error"):
        print(f"authorization refused: {result['error']}")
        return False
    if result.get("state") != state:
        print("state mismatch — aborting (possible tampering)")
        return False

    resp = requests.post(TOKEN_URL, json={
        "grant_type": "authorization_code",
        "code": result.get("code"),
        "state": result.get("state"),
        "redirect_uri": redirect_uri,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
    }, timeout=15)
    if resp.status_code != 200:
        print(f"token exchange failed: HTTP {resp.status_code}")
        return False
    _store_response(resp.json())
    print("Connected — Nimbus now has its own read-only token (Keychain: Nimbus/oauth).")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if login() else 1)
