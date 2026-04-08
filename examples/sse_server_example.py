#!/usr/bin/env python
"""
SSE Server Example

Demonstrates how to run the ServiceNow MCP server using Server-Sent Events (SSE)
for HTTP-based communication instead of stdio.

Prerequisites:
1. pip install -e .  (from the project root)
2. A .env file with your ServiceNow credentials, or set environment variables:
   - SERVICENOW_INSTANCE_URL
   - SERVICENOW_USERNAME
   - SERVICENOW_PASSWORD
   - SERVICENOW_AUTH_TYPE (default: basic)

Usage:
    python examples/sse_server_example.py
    python examples/sse_server_example.py --host 127.0.0.1 --port 9000
"""

import argparse
import os
import sys

import uvicorn
from dotenv import load_dotenv

from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.server_sse import create_starlette_app
from servicenow_mcp.utils.config import (
    AuthConfig,
    AuthType,
    BasicAuthConfig,
    OAuthConfig,
    ServerConfig,
)

# Load environment variables from .env
load_dotenv()


def build_config() -> ServerConfig:
    instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    auth_type = os.getenv("SERVICENOW_AUTH_TYPE", "basic").lower()

    if not instance_url:
        print("Error: SERVICENOW_INSTANCE_URL is required", file=sys.stderr)
        sys.exit(1)

    if auth_type == "oauth":
        auth = AuthConfig(
            type=AuthType.OAUTH,
            config=OAuthConfig(
                client_id=os.getenv("SERVICENOW_CLIENT_ID", ""),
                client_secret=os.getenv("SERVICENOW_CLIENT_SECRET", ""),
                token_url=os.getenv("SERVICENOW_TOKEN_URL", ""),
            ),
        )
    else:
        username = os.getenv("SERVICENOW_USERNAME", "")
        password = os.getenv("SERVICENOW_PASSWORD", "")
        if not username or not password:
            print("Error: SERVICENOW_USERNAME and SERVICENOW_PASSWORD are required", file=sys.stderr)
            sys.exit(1)
        auth = AuthConfig(
            type=AuthType.BASIC,
            config=BasicAuthConfig(username=username, password=password),
        )

    return ServerConfig(instance_url=instance_url, auth=auth, debug=True)


def main():
    parser = argparse.ArgumentParser(description="ServiceNow MCP SSE Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()

    config = build_config()
    mcp_server = ServiceNowMCP(config)
    app = create_starlette_app(mcp_server, debug=True)

    print(f"Starting SSE server on {args.host}:{args.port}")
    print(f"  SSE endpoint:      http://{args.host}:{args.port}/sse")
    print(f"  Messages endpoint: http://{args.host}:{args.port}/messages/")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
