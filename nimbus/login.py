"""Nimbus's own OAuth login (Pier decision #5, endpoints verified per G7).

Manual-paste PKCE flow — the public client only accepts the hosted callback
page, not localhost (FACTS.md): the browser opens claude.ai for approval with
read-only scope `user:profile`, the callback page displays a code, the user
pastes it back. Tokens live in Nimbus's OWN Keychain item (service "Nimbus",
account "oauth") and Nimbus refreshes them itself. Claude Code's credentials
are never touched (G2).

Run: python -m nimbus.login
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import webbrowser

import keyring
import requests

AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"  # public PKCE client
SCOPE = "user:profile"  # read-only usage

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


def build_authorize() -> tuple[str, str, str]:
    """Returns (authorize_url, code_verifier, state)."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = _b64url(secrets.token_bytes(16))
    params = urllib.parse.urlencode({
        "code": "true",  # required — the callback page displays a paste-able code
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })
    return f"{AUTHORIZE_URL}?{params}", verifier, state


def parse_pasted_code(raw: str) -> tuple[str, str | None]:
    """Accepts 'code#state', a bare code, or the full callback URL.
    Returns (code, state_or_None)."""
    raw = raw.strip()
    if not raw:
        raise ValueError("empty code")
    if raw.startswith("http"):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        code = (qs.get("code") or [None])[0]
        state = (qs.get("state") or [None])[0]
        if not code:
            raise ValueError("URL has no code parameter")
        return code, state
    if "#" in raw:
        code, _, state = raw.partition("#")
        return code, state or None
    return raw, None


def exchange(pasted: str, verifier: str, state: str) -> bool:
    """Exchange the pasted code for tokens. Returns True on success."""
    code, returned_state = parse_pasted_code(pasted)
    if returned_state is not None and returned_state != state:
        print("state mismatch — aborting (possible tampering)")
        return False
    resp = requests.post(TOKEN_URL, json={
        "grant_type": "authorization_code",
        "code": code,
        "state": returned_state or state,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
    }, timeout=15)
    if resp.status_code != 200:
        print(f"token exchange failed: HTTP {resp.status_code}")
        return False
    _store_response(resp.json())
    return True


def login() -> bool:
    """CLI flow: open browser, prompt for the pasted code."""
    url, verifier, state = build_authorize()
    print("Opening browser for Claude approval (read-only usage scope)…")
    print(f"If it doesn't open, visit:\n  {url}\n")
    webbrowser.open(url)
    pasted = input("Paste the code shown after approving: ")
    try:
        ok = exchange(pasted, verifier, state)
    except ValueError as exc:
        print(f"could not parse that: {exc}")
        return False
    if ok:
        print("Connected — Nimbus now has its own read-only token (Keychain: Nimbus/oauth).")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if login() else 1)
