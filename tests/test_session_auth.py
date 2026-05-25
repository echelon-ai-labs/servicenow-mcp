"""Tests for SESSION authentication (browser SSO via Playwright)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import AuthConfig, AuthType, SessionAuthConfig


@pytest.fixture
def session_auth_config():
    return AuthConfig(
        type=AuthType.SESSION,
        session=SessionAuthConfig(headless=True, auto_refresh=True),
    )


@pytest.fixture
def fake_session_data():
    return {
        "cookies": {"JSESSIONID": "ABC123", "glide_session_store": "DEF456"},
        "x_user_token": "tok_xyz",
        "user_id": "user_sys_id_1",
        "captured_at": 1700000000,
        "instance_url": "https://example.service-now.com",
    }


def test_get_headers_session_injects_cookie_and_token(session_auth_config, fake_session_data):
    mgr = AuthManager(session_auth_config, "https://example.service-now.com")
    with patch(
        "servicenow_mcp.auth.session_flow.get_valid_session",
        return_value=fake_session_data,
    ):
        headers = mgr.get_headers()
    assert headers["X-UserToken"] == "tok_xyz"
    assert "JSESSIONID=ABC123" in headers["Cookie"]
    assert "glide_session_store=DEF456" in headers["Cookie"]
    assert headers["Accept"] == "application/json"


def test_get_cookies_session(session_auth_config, fake_session_data):
    mgr = AuthManager(session_auth_config, "https://example.service-now.com")
    with patch(
        "servicenow_mcp.auth.session_flow.get_valid_session",
        return_value=fake_session_data,
    ):
        cookies = mgr.get_cookies()
    assert cookies == fake_session_data["cookies"]


def test_make_request_retries_on_401(session_auth_config, fake_session_data):
    mgr = AuthManager(session_auth_config, "https://example.service-now.com")

    response_401 = MagicMock(status_code=401, text="unauthorized")
    response_200 = MagicMock(status_code=200, text="ok")

    call_count = {"n": 0}

    def fake_request(method, url, **kwargs):
        call_count["n"] += 1
        return response_401 if call_count["n"] == 1 else response_200

    with patch(
        "servicenow_mcp.auth.session_flow.get_valid_session",
        return_value=fake_session_data,
    ), patch("servicenow_mcp.auth.auth_manager.requests.request", side_effect=fake_request):
        r = mgr.make_request("GET", "https://example.service-now.com/api/now/table/incident")

    assert r.status_code == 200
    assert call_count["n"] == 2


def test_make_request_no_retry_on_non_session_auth():
    cfg = AuthConfig(
        type=AuthType.BASIC,
        basic={"username": "u", "password": "p"},  # type: ignore
    )
    mgr = AuthManager(cfg, "https://example.service-now.com")
    response_401 = MagicMock(status_code=401, text="unauthorized")

    with patch(
        "servicenow_mcp.auth.auth_manager.requests.request",
        return_value=response_401,
    ) as req:
        r = mgr.make_request("GET", "https://example.service-now.com/x")
    assert r.status_code == 401
    assert req.call_count == 1


def test_session_flow_validation_ping():
    """is_session_valid performs GET with headers/cookies and returns True on HTTP 200."""
    from servicenow_mcp.auth.session_flow import is_session_valid

    data = {
        "cookies": {"JSESSIONID": "X"},
        "x_user_token": "t",
    }
    with patch("servicenow_mcp.auth.session_flow.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        assert is_session_valid(data, "https://example.service-now.com") is True

        mock_get.return_value = MagicMock(status_code=401)
        assert is_session_valid(data, "https://example.service-now.com") is False


def test_session_flow_cache_roundtrip(tmp_path, monkeypatch):
    """save -> load preserves content."""
    from servicenow_mcp.auth import session_flow

    cache_dir = tmp_path / ".servicenow-mcp"
    monkeypatch.setattr(session_flow, "SESSION_CACHE_DIR", cache_dir)
    monkeypatch.setattr(session_flow, "SESSION_CACHE_FILE", cache_dir / "session_cache.json")

    data = {"cookies": {"a": "b"}, "x_user_token": "t", "user_id": "u"}
    session_flow.save_cached_session(data)
    assert session_flow.load_cached_session() == data

    session_flow.clear_session_cache()
    assert session_flow.load_cached_session() is None


def test_get_valid_session_uses_cache_when_valid(monkeypatch):
    from servicenow_mcp.auth import session_flow

    cached = {
        "cookies": {"JSESSIONID": "X"},
        "x_user_token": "t",
        "instance_url": "https://example.service-now.com",
    }
    monkeypatch.setattr(session_flow, "load_cached_session", lambda: cached)
    monkeypatch.setattr(session_flow, "is_session_valid", lambda d, url: True)

    capture_called = {"n": 0}
    monkeypatch.setattr(
        session_flow,
        "capture_session",
        lambda *a, **k: capture_called.__setitem__("n", capture_called["n"] + 1) or {},
    )

    result = session_flow.get_valid_session("https://example.service-now.com")
    assert result == cached
    assert capture_called["n"] == 0


def test_get_valid_session_recaptures_when_invalid(monkeypatch):
    from servicenow_mcp.auth import session_flow

    cached = {
        "cookies": {},
        "instance_url": "https://example.service-now.com",
    }
    fresh = {
        "cookies": {"JSESSIONID": "NEW"},
        "x_user_token": "t",
        "instance_url": "https://example.service-now.com",
    }
    monkeypatch.setattr(session_flow, "load_cached_session", lambda: cached)
    monkeypatch.setattr(session_flow, "is_session_valid", lambda d, url: False)
    monkeypatch.setattr(session_flow, "capture_session", lambda *a, **k: fresh)
    monkeypatch.setattr(session_flow, "save_cached_session", lambda d: None)

    result = session_flow.get_valid_session("https://example.service-now.com")
    assert result == fresh


def test_ui_tool_rejects_non_session_auth():
    from servicenow_mcp.tools.ui_internal_tools import (
        UiCurrentUserParams,
        ui_current_user,
    )
    from servicenow_mcp.utils.config import BasicAuthConfig, ServerConfig

    cfg = ServerConfig(
        instance_url="https://example.service-now.com",
        auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="u", password="p")),
    )
    mgr = AuthManager(cfg.auth, cfg.instance_url)
    out = ui_current_user(cfg, mgr, UiCurrentUserParams())
    parsed = json.loads(out)
    assert "error" in parsed
    assert "session" in parsed["error"].lower()
