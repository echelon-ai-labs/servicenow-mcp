"""Unit tests for SSE transport helpers and CLI guards (security hardening)."""

import pytest

from servicenow_mcp.server_sse import (
    _build_allowed_hosts,
    _build_allowed_origins,
    _is_loopback_host,
    _resolve_auth_token,
    create_starlette_app,
    main,
)


# --- _is_loopback_host -----------------------------------------------------


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "[::1]", "LOCALHOST"])
def test_is_loopback_host_true(host):
    assert _is_loopback_host(host) is True


@pytest.mark.parametrize(
    "host", ["0.0.0.0", "192.168.1.5", "10.0.0.1", "example.com", "mcp.internal", ""]
)
def test_is_loopback_host_false(host):
    assert _is_loopback_host(host) is False


# --- _resolve_auth_token ---------------------------------------------------


def test_resolve_auth_token_env_wins(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "supplied-token")
    assert _resolve_auth_token(allow_remote=False) == "supplied-token"
    assert _resolve_auth_token(allow_remote=True) == "supplied-token"


def test_resolve_auth_token_autogen_on_loopback(monkeypatch, capsys):
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    tok = _resolve_auth_token(allow_remote=False)
    assert isinstance(tok, str) and len(tok) >= 32
    err = capsys.readouterr().err
    assert tok in err
    assert "generated auth token" in err


def test_resolve_auth_token_fail_on_remote(monkeypatch):
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        _resolve_auth_token(allow_remote=True)


def test_resolve_auth_token_blank_env_treated_as_unset(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "   ")
    with pytest.raises(SystemExit):
        _resolve_auth_token(allow_remote=True)


# --- _build_allowed_hosts / _build_allowed_origins -------------------------


def test_build_allowed_hosts_loopback_defaults():
    hosts = _build_allowed_hosts("127.0.0.1", 8080)
    assert "127.0.0.1" in hosts
    assert "127.0.0.1:8080" in hosts
    assert "localhost" in hosts
    assert "localhost:8080" in hosts
    assert "[::1]" in hosts
    assert "[::1]:8080" in hosts


def test_build_allowed_hosts_includes_remote_host():
    hosts = _build_allowed_hosts("mcp.internal", 9000)
    assert "mcp.internal" in hosts
    assert "mcp.internal:9000" in hosts
    assert "127.0.0.1" in hosts


def test_build_allowed_hosts_extras_appended():
    hosts = _build_allowed_hosts("127.0.0.1", 8080, ["a.example", "b.example:443"])
    assert "a.example" in hosts
    assert "b.example:443" in hosts


def test_build_allowed_hosts_lowercased():
    hosts = _build_allowed_hosts("MCP.Internal", 8080)
    assert "mcp.internal" in hosts
    assert all(h == h.lower() for h in hosts)


def test_build_allowed_origins_pairs_http_and_https():
    origins = _build_allowed_origins({"127.0.0.1:8080"})
    assert "http://127.0.0.1:8080" in origins
    assert "https://127.0.0.1:8080" in origins


# --- main() guards ---------------------------------------------------------


def test_main_remote_bind_without_allow_remote_exits(monkeypatch):
    monkeypatch.delenv("MCP_ALLOW_REMOTE", raising=False)
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        main(["--host", "0.0.0.0"])


def test_main_allow_remote_without_token_exits(monkeypatch):
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        main(["--host", "0.0.0.0", "--allow-remote"])


def test_main_allow_remote_via_env(monkeypatch):
    """MCP_ALLOW_REMOTE=1 should flip --allow-remote default but token still required."""
    monkeypatch.setenv("MCP_ALLOW_REMOTE", "1")
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        main(["--host", "0.0.0.0"])


# --- create_starlette_app debug default ------------------------------------


def test_create_starlette_app_no_debug_by_default():
    """Regression: ensure debug is not silently True (CVE root cause #b)."""
    sentinel_server = object()  # not used until a request comes in
    app = create_starlette_app(
        sentinel_server,  # type: ignore[arg-type]
        auth_token="t",
        allowed_hosts={"127.0.0.1:8080"},
        allowed_origins={"http://127.0.0.1:8080"},
    )
    assert app.debug is False
