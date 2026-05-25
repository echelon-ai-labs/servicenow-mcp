"""
Browser-session (SSO) authentication for ServiceNow.

- Launches Chromium (Playwright) for one-time SSO/MFA login
- Captures session cookies + X-UserToken (g_ck)
- Caches session in ~/.servicenow-mcp/session_cache.json
- Auto-refreshes by re-opening browser when cache expires
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SESSION_CACHE_DIR = Path.home() / ".servicenow-mcp"
SESSION_CACHE_FILE = SESSION_CACHE_DIR / "session_cache.json"
DEFAULT_LOGIN_TIMEOUT_S = 180
SESSION_TTL_S = 60 * 60 * 8  # 8h declared lifetime (actual validation via ping)


# ── Cache ─────────────────────────────────────────────────────────────────────

def load_cached_session() -> Optional[dict]:
    """Load cached session from disk, if available."""
    if not SESSION_CACHE_FILE.exists():
        return None
    try:
        with open(SESSION_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupted session cache: %s", exc)
        return None


def save_cached_session(data: dict) -> None:
    """Persist session to disk with restricted permissions (0o600 when possible)."""
    SESSION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(SESSION_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(SESSION_CACHE_FILE, 0o600)
    except OSError:
        # Windows may not support traditional chmod semantics
        pass


def clear_session_cache() -> None:
    """Remove cache, forcing a new capture on next use."""
    if SESSION_CACHE_FILE.exists():
        SESSION_CACHE_FILE.unlink()
        logger.info("Session cache removed.")


# ── Validation ────────────────────────────────────────────────────────────────

def _build_cookie_header(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def is_session_valid(data: dict, instance_url: str, timeout: int = 10) -> bool:
    """Perform a lightweight ping to confirm session is still authenticated."""
    if not data or "cookies" not in data:
        return False
    try:
        url = f"{instance_url.rstrip('/')}/api/now/table/sys_user"
        headers = {
            "Accept": "application/json",
            "X-UserToken": data.get("x_user_token", ""),
            "Cookie": _build_cookie_header(data["cookies"]),
        }
        r = requests.get(
            url,
            headers=headers,
            params={"sysparm_limit": 1, "sysparm_fields": "sys_id"},
            timeout=timeout,
        )
        return r.status_code == 200
    except requests.RequestException as exc:
        logger.warning("Error validating session: %s", exc)
        return False


# ── Capture via Playwright ────────────────────────────────────────────────────

def capture_session(
    instance_url: str,
    headless: bool = False,
    timeout_s: int = DEFAULT_LOGIN_TIMEOUT_S,
) -> dict:
    """
    Open Chromium, wait for user login (SSO+MFA), and capture session.

    Returns dict with keys: cookies (dict), x_user_token (str),
    user_id (str|None), captured_at (epoch), instance_url (str).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        ) from exc

    instance_url = instance_url.rstrip("/")
    logger.info("Opening browser for SSO login at %s ...", instance_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        # /navpage.do loads classic UI16 (frameset with gsft_main).
        # If not authenticated, it redirects to SSO. After login, it returns
        # to the frameset where g_user/g_ck are exposed in gsft_main.
        page.goto(f"{instance_url}/navpage.do", timeout=30_000)

        # Polling: look for non-guest g_user.userID in any frame.
        deadline = time.time() + timeout_s
        g_ck = None
        user_id = None
        logger.info(
            "Waiting for user login (timeout=%ds). "
            "Complete SSO/MFA in the Chromium window...",
            timeout_s,
        )

        last_log = 0.0
        while time.time() < deadline:
            now = time.time()
            if now - last_log > 15:
                frames_info = [(f.name or "<top>", (f.url or "")[:80]) for f in page.frames]
                logger.info("Waiting... frames: %s", frames_info)
                last_log = now

            for frame in page.frames:
                try:
                    uid = frame.evaluate(
                        "() => (typeof window.g_user !== 'undefined' && window.g_user) "
                        "? window.g_user.userID : null"
                    )
                except Exception:
                    uid = None
                if not uid or str(uid).lower() == "guest":
                    continue
                try:
                    ck = frame.evaluate(
                        "() => (typeof window.g_ck !== 'undefined') ? window.g_ck : null"
                    )
                except Exception:
                    ck = None
                if uid and ck:
                    user_id, g_ck = uid, ck
                    break
            if user_id and g_ck:
                logger.info("Login detected in frame (user=%s).", user_id)
                break
            page.wait_for_timeout(2000)

        if not g_ck or not user_id:
            browser.close()
            raise TimeoutError(
                f"Login not completed in {timeout_s}s "
                f"(user_id={user_id!r}). Check SSO/MFA and try again."
            )

        cookies_list = context.cookies()
        cookies = {c["name"]: c["value"] for c in cookies_list if c.get("domain")}
        browser.close()

    data = {
        "cookies": cookies,
        "x_user_token": g_ck,
        "user_id": user_id,
        "captured_at": int(time.time()),
        "instance_url": instance_url,
    }
    logger.info("Session captured (user_id=%s, %d cookies).", user_id, len(cookies))
    return data


# ── Orchestrator ──────────────────────────────────────────────────────────────

def get_valid_session(
    instance_url: str,
    headless: bool = False,
    force_reauth: bool = False,
    auto_refresh: bool = True,
) -> dict:
    """
    Return a valid session.

    Order: cache -> ping validation -> (if invalid and auto_refresh) recapture.
    """
    if not force_reauth:
        cached = load_cached_session()
        if cached and cached.get("instance_url") == instance_url.rstrip("/"):
            if is_session_valid(cached, instance_url):
                logger.debug("Reusing cached session.")
                return cached
            logger.info("Cached session is invalid; recapturing...")

    if not auto_refresh and not force_reauth:
        raise RuntimeError(
            "Session is invalid and auto_refresh=False. "
            "Run `servicenow-mcp session login` manually."
        )

    data = capture_session(instance_url, headless=headless)
    save_cached_session(data)
    return data
