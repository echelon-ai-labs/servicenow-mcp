"""
ServiceNow MCP Server

This module provides the main implementation of the ServiceNow MCP server.
"""

import argparse
import os
from typing import Dict, Union

import uvicorn
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class MCPFactory:
    """Factory class to create ServiceNowMCP instances on demand."""

    @staticmethod
    def create_mcp_instance(instance_url: str, username: str, password: str) -> ServiceNowMCP:
        """
        Create a new ServiceNowMCP instance with the provided credentials.

        Args:
            instance_url: ServiceNow instance URL
            username: ServiceNow username
            password: ServiceNow password

        Returns:
            A configured ServiceNowMCP instance
        """
        # Create basic auth config
        auth_config = AuthConfig(
            type=AuthType.BASIC, basic=BasicAuthConfig(username=username, password=password)
        )

        # Create server config
        config = ServerConfig(instance_url=instance_url, auth=auth_config)

        # Create and return MCP instance
        return ServiceNowMCP(config)


def create_starlette_app(debug: bool = False) -> Starlette:
    """Create a Starlette application that creates MCP instances per request."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Union[None, JSONResponse]:
        # Extract auth and instance URL from headers
        instance_url = request.headers.get("X-ServiceNow-Instance-URL")
        username = request.headers.get("X-ServiceNow-Username")
        password = request.headers.get("X-ServiceNow-Password")

        # Validate required headers
        if not all([instance_url, username, password]):
            return JSONResponse(
                {"error": "Missing required headers for ServiceNow connection"}, status_code=400
            )

        # Create a new MCP instance for this specific request
        mcp_instance = MCPFactory.create_mcp_instance(
            instance_url=instance_url, username=username, password=password
        )

        # Get the underlying MCP server
        mcp_server = mcp_instance.mcp_server._mcp_server

        # Handle the connection
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
    )


class ServiceNowMCP(ServiceNowMCP):
    """
    ServiceNow MCP Server implementation.

    This class provides a Model Context Protocol (MCP) server for ServiceNow,
    allowing LLMs to interact with ServiceNow data and functionality.
    """

    def __init__(self, config: Union[Dict, ServerConfig]):
        """
        Initialize the ServiceNow MCP server.

        Args:
            config: Server configuration, either as a dictionary or ServerConfig object.
        """
        super().__init__(config)
        self.mcp_server = FastMCP("ServiceNow", port=8080, host="localhost")
        self._register_tools()


def start_server(host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
    """
    Start the MCP server with SSE transport using Starlette and Uvicorn.

    This server creates new MCP instances per request based on headers.

    Args:
        host: Host address to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    # Create Starlette app with SSE transport
    starlette_app = create_starlette_app(debug=debug)

    # Run using uvicorn
    uvicorn.run(starlette_app, host=host, port=port)


def main():
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run ServiceNow MCP SSE-based server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Start the server
    start_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
