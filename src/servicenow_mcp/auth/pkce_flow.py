"""
OAuth 2.0 PKCE flow for ServiceNow SSO authentication.

- Opens browser once for SSO login
- Saves tokens to ~/.servicenow-mcp/token_cache.json
- Transparently auto-refreshes using refresh_token
"""
import base64
import hashlib
import json
import logging
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

logger = logging.getLogger(__name__)

TOKEN_CACHE_DIR = Path.home() / ".servicenow-mcp"
TOKEN_CACHE_FILE = TOKEN_CACHE_DIR / "token_cache.json"
REDIRECT_PORT_DEFAULT = 9876
REDIRECT_URI_TEMPLATE = "http://localhost:{port}/callback"


# ── PKCE helpers ──────────────────────────────────────────────────────────────

def _generate_pkce_pair() -> tuple:
    """Generate a code_verifier and its corresponding SHA-256 code_challenge."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ── Token cache ───────────────────────────────────────────────────────────────

def load_cached_token() -> Optional[dict]:
    """Load cached tokens from disk, if available."""
    if TOKEN_CACHE_FILE.exists():
        try:
            with open(TOKEN_CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_token(token_data: dict) -> None:
    """Save tokens to disk with restricted permissions."""
    TOKEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    token_data = dict(token_data)
    token_data["issued_at"] = int(time.time())
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    try:
        TOKEN_CACHE_FILE.chmod(0o600)
    except OSError:
        pass  # Windows may not support chmod; safe to ignore


def clear_token_cache() -> None:
    """Remove token cache, forcing a new login on next call."""
    if TOKEN_CACHE_FILE.exists():
        TOKEN_CACHE_FILE.unlink()
        logger.info("Token cache removed.")


def is_token_valid(token_data: dict, buffer_seconds: int = 60) -> bool:
    """Check whether access_token is still valid (with safety buffer)."""
    issued_at = token_data.get("issued_at", 0)
    expires_in = token_data.get("expires_in", 0)
    return (issued_at + expires_in - buffer_seconds) > int(time.time())


def refresh_access_token(instance_url: str, client_id: str, token_data: dict) -> Optional[dict]:
    """Try refreshing access_token using cached refresh_token."""
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        return None
    token_url = f"{instance_url}/oauth_token.do"
    try:
        resp = requests.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code == 200:
            new_data = resp.json()
            # Preserve refresh_token if the new payload does not include one
            if "refresh_token" not in new_data:
                new_data["refresh_token"] = refresh_token
            save_token(new_data)
            logger.info("Access token refreshed via refresh_token.")
            return new_data
        logger.warning(f"Refresh token failed: HTTP {resp.status_code} — {resp.text}")
        return None
    except requests.RequestException as e:
        logger.error(f"Error refreshing token: {e}")
        return None


# ── Local OAuth callback server ──────────────────────────────────────────────

class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code: Optional[str] = None
    error: Optional[str] = None
    _event: Optional[threading.Event] = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            body = (
                b"<html><body style='font-family:sans-serif;text-align:center;padding:40px'>"
                b"<h2 style='color:#2e7d32'>&#10003; SSO authentication completed!</h2>"
                b"<p>You can close this window and return to the terminal.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            _CallbackHandler.error = (
                params.get("error_description", params.get("error", ["Unknown error"]))[0]
            )
            body = (
                b"<html><body style='font-family:sans-serif;text-align:center;padding:40px'>"
                b"<h2 style='color:#c62828'>&#10007; SSO authentication error</h2>"
                b"<p>Check terminal output for details.</p>"
                b"</body></html>"
            )
        else:
            body = b"<html><body><p>Aguardando callback...</p></body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        if (_CallbackHandler.auth_code or _CallbackHandler.error) and _CallbackHandler._event:
            _CallbackHandler._event.set()

    def log_message(self, fmt, *args):
        pass  # suppress callback server HTTP logs


def _start_callback_server(port: int, event: threading.Event) -> HTTPServer:
    _CallbackHandler.auth_code = None
    _CallbackHandler.error = None
    _CallbackHandler._event = event
    server = HTTPServer(("localhost", port), _CallbackHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ── Main PKCE flow ────────────────────────────────────────────────────────────

def run_pkce_flow(
    instance_url: str,
    client_id: str,
    scopes: str = "useraccount",
    port: int = REDIRECT_PORT_DEFAULT,
    timeout: int = 180,
) -> dict:
    """
        Execute full OAuth 2.0 PKCE flow:
            1. Start local callback server on selected port
            2. Open browser for ServiceNow SSO login
            3. Wait for callback with authorization code
            4. Exchange code for access_token + refresh_token
            5. Save tokens in local cache
    """
    redirect_uri = REDIRECT_URI_TEMPLATE.format(port=port)
    verifier, challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    auth_url = (
        f"{instance_url}/oauth_auth.do?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
                "scope": scopes,
            }
        )
    )

    event = threading.Event()
    server = _start_callback_server(port, event)

    print("\n" + "=" * 62)
    print("  SSO AUTHENTICATION - ServiceNow")
    print("=" * 62)
    print(f"\n  Opening browser for SSO login...")
    print(f"\n  If browser does not open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)
    print(f"  Waiting for authorization (timeout: {timeout}s)...")

    completed = event.wait(timeout=timeout)
    server.shutdown()

    if not completed:
        raise RuntimeError(f"Timeout: SSO login not completed within {timeout} seconds.")
    if _CallbackHandler.error:
        raise RuntimeError(f"SSO authorization error: {_CallbackHandler.error}")
    if not _CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received in callback.")

    # Exchange authorization code for tokens
    token_url = f"{instance_url}/oauth_token.do"
    resp = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": _CallbackHandler.auth_code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to exchange authorization code for token: HTTP {resp.status_code} — {resp.text}"
        )

    token_data = resp.json()
    save_token(token_data)

    print("\n  + SSO login completed. Token saved in cache.")
    print("=" * 62 + "\n")
    return token_data


def get_valid_token(
    instance_url: str,
    client_id: str,
    scopes: str = "useraccount",
    port: int = REDIRECT_PORT_DEFAULT,
    force_reauth: bool = False,
) -> str:
    """
        Return a valid access_token, using this order:
            1. Local cache (if still valid)
            2. Refresh token (silent refresh)
            3. Browser SSO login (one-time when required)
    """
    if not force_reauth:
        cached = load_cached_token()
        if cached:
            if is_token_valid(cached):
                logger.debug("Usando access_token do cache local.")
                return cached["access_token"]
            logger.info("Token expired - trying refresh via refresh_token...")
            refreshed = refresh_access_token(instance_url, client_id, cached)
            if refreshed and is_token_valid(refreshed):
                return refreshed["access_token"]
            logger.info("Refresh token invalid or expired - starting SSO login.")

    token_data = run_pkce_flow(
        instance_url=instance_url,
        client_id=client_id,
        scopes=scopes,
        port=port,
    )
    return token_data["access_token"]
