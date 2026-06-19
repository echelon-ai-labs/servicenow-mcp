"""ServiceNow MCP SSE server with bearer-token auth and Host/Origin allowlist.

Defaults to loopback bind. Remote bind requires --allow-remote and an explicit
MCP_AUTH_TOKEN. See README "SSE deployment" for the full security contract.
"""

import argparse
import hmac
import os
import secrets
import sys
from typing import Dict, Iterable, List, Optional, Set, Union

import uvicorn
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.routing import Mount, Route

from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]", "0:0:0:0:0:0:0:1"}
_TRUTHY = {"1", "true", "yes", "on"}


def _is_loopback_host(host: str) -> bool:
    return host.lower().strip() in _LOOPBACK_HOSTS


def _resolve_auth_token(*, allow_remote: bool) -> str:
    tok = os.getenv("MCP_AUTH_TOKEN", "").strip()
    if tok:
        return tok
    if allow_remote:
        raise SystemExit("MCP_AUTH_TOKEN must be set when --allow-remote is used")
    tok = secrets.token_urlsafe(32)
    print(f"[servicenow-mcp-sse] generated auth token: {tok}", file=sys.stderr, flush=True)
    return tok


def _build_allowed_hosts(host: str, port: int, extra: Optional[Iterable[str]] = None) -> Set[str]:
    base = {
        "127.0.0.1",
        f"127.0.0.1:{port}",
        "localhost",
        f"localhost:{port}",
        "[::1]",
        f"[::1]:{port}",
    }
    if not _is_loopback_host(host):
        base.add(host)
        base.add(f"{host}:{port}")
    if extra:
        for entry in extra:
            entry = entry.strip()
            if entry:
                base.add(entry)
    return {h.lower() for h in base}


def _build_allowed_origins(allowed_hosts: Set[str]) -> Set[str]:
    origins: Set[str] = set()
    for host in allowed_hosts:
        origins.add(f"http://{host}")
        origins.add(f"https://{host}")
    return origins


class SecurityMiddleware:
    """ASGI middleware: bearer-token auth + Host/Origin allowlist.

    Pure ASGI (not BaseHTTPMiddleware) to keep streaming SSE responses unbuffered.
    """

    def __init__(
        self,
        app,
        *,
        token: str,
        allowed_hosts: Set[str],
        allowed_origins: Set[str],
    ):
        self.app = app
        self._token = token.encode("utf-8")
        self._allowed_hosts = {h.lower() for h in allowed_hosts}
        self._allowed_origins = {o.lower() for o in allowed_origins}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)

        host = headers.get("host", "").lower().strip()
        if host not in self._allowed_hosts:
            await _send_text(send, 421, b"Misdirected Request: Host not in allowlist")
            return

        origin = headers.get("origin")
        if origin is not None:
            if origin.lower().strip() not in self._allowed_origins:
                await _send_text(send, 403, b"Forbidden: Origin not in allowlist")
                return

        auth = headers.get("authorization", "")
        scheme, _, value = auth.partition(" ")
        if (
            scheme.lower() != "bearer"
            or not value
            or not hmac.compare_digest(value.encode("utf-8"), self._token)
        ):
            await _send_text(
                send,
                401,
                b"Unauthorized",
                extra_headers=[(b"www-authenticate", b"Bearer")],
            )
            return

        await self.app(scope, receive, send)


async def _send_text(
    send,
    status: int,
    body: bytes,
    *,
    extra_headers: Optional[List] = None,
):
    headers = [(b"content-type", b"text/plain; charset=utf-8")]
    if extra_headers:
        headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def create_starlette_app(
    mcp_server: Server,
    *,
    auth_token: str,
    allowed_hosts: Set[str],
    allowed_origins: Set[str],
    debug: bool = False,
) -> Starlette:
    """Build a Starlette app exposing the MCP server via SSE, gated by SecurityMiddleware."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
        middleware=[
            Middleware(
                SecurityMiddleware,
                token=auth_token,
                allowed_hosts=allowed_hosts,
                allowed_origins=allowed_origins,
            ),
        ],
    )


class ServiceNowSSEMCP(ServiceNowMCP):
    """ServiceNow MCP server bound to an SSE transport."""

    def __init__(self, config: Union[Dict, ServerConfig]):
        super().__init__(config)

    def start(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        *,
        allow_remote: bool = False,
        auth_token: Optional[str] = None,
        allowed_hosts: Optional[Set[str]] = None,
        allowed_origins: Optional[Set[str]] = None,
        debug: bool = False,
    ):
        """Start the SSE server.

        host/port: bind address. Defaults to loopback; non-loopback requires allow_remote.
        auth_token: bearer token; auto-generated on loopback if None, required for remote.
        allowed_hosts/origins: allowlists; auto-built from host/port if None.
        """
        if not _is_loopback_host(host) and not allow_remote:
            raise SystemExit(
                f"refusing to bind non-loopback host {host!r} without allow_remote=True"
            )
        if auth_token is None:
            auth_token = _resolve_auth_token(allow_remote=allow_remote)
        if allowed_hosts is None:
            allowed_hosts = _build_allowed_hosts(host, port, [])
        if allowed_origins is None:
            allowed_origins = _build_allowed_origins(allowed_hosts)

        app = create_starlette_app(
            self.mcp_server,
            auth_token=auth_token,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
            debug=debug,
        )
        uvicorn.run(app, host=host, port=port)


def create_servicenow_mcp(instance_url: str, username: str, password: str):
    """Create a ServiceNow MCP server with basic-auth ServiceNow credentials.

    Example:
        ```python
        mcp = create_servicenow_mcp(
            instance_url="https://instance.service-now.com",
            username="admin",
            password="password",
        )
        mcp.start()  # binds 127.0.0.1:8080 with auto-generated bearer token
        ```
    """
    auth_config = AuthConfig(
        type=AuthType.BASIC, basic=BasicAuthConfig(username=username, password=password)
    )
    config = ServerConfig(instance_url=instance_url, auth=auth_config)
    return ServiceNowSSEMCP(config)


def main(argv: Optional[List[str]] = None):
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run ServiceNow MCP SSE-based server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1; non-loopback requires --allow-remote)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        default=os.getenv("MCP_ALLOW_REMOTE", "").strip().lower() in _TRUTHY,
        help="Permit non-loopback bind (requires MCP_AUTH_TOKEN). Env: MCP_ALLOW_REMOTE",
    )
    parser.add_argument(
        "--allowed-host",
        action="append",
        default=None,
        help="Extra Host header value to allow (repeatable). Env: MCP_ALLOWED_HOSTS=h1,h2",
    )
    args = parser.parse_args(argv)

    if not _is_loopback_host(args.host) and not args.allow_remote:
        parser.error(
            f"refusing to bind non-loopback host {args.host!r} without --allow-remote"
        )

    auth_token = _resolve_auth_token(allow_remote=args.allow_remote)

    extra_hosts: List[str] = list(args.allowed_host or [])
    env_hosts = os.getenv("MCP_ALLOWED_HOSTS", "")
    if env_hosts:
        extra_hosts.extend(h.strip() for h in env_hosts.split(",") if h.strip())

    allowed_hosts = _build_allowed_hosts(args.host, args.port, extra_hosts)
    allowed_origins = _build_allowed_origins(allowed_hosts)

    debug = os.getenv("SERVICENOW_DEBUG", "").strip().lower() in _TRUTHY

    server = create_servicenow_mcp(
        instance_url=os.getenv("SERVICENOW_INSTANCE_URL"),
        username=os.getenv("SERVICENOW_USERNAME"),
        password=os.getenv("SERVICENOW_PASSWORD"),
    )
    server.start(
        host=args.host,
        port=args.port,
        allow_remote=args.allow_remote,
        auth_token=auth_token,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
        debug=debug,
    )


if __name__ == "__main__":
    main()
