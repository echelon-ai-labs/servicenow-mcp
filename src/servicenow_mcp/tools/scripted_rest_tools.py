"""
Scripted REST API tools for the ServiceNow MCP server.

This module provides tools for creating Scripted REST APIs (services and resources)
in ServiceNow.
"""

import logging
from typing import Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class CreateScriptedRestApiParams(BaseModel):
    """Parameters for creating a Scripted REST API service."""

    name: str = Field(..., description="Name of the Scripted REST API service")
    api_id: Optional[str] = Field(
        None,
        description="API ID (namespace) for the service, e.g. 'nowllm_chat'. "
        "If not provided, ServiceNow will auto-generate one.",
    )
    short_description: Optional[str] = Field(
        None, description="Short description of the service"
    )
    is_active: bool = Field(True, description="Whether the service is active")


class CreateScriptedRestResourceParams(BaseModel):
    """Parameters for creating a Scripted REST API resource (operation)."""

    web_service_definition: str = Field(
        ...,
        description="sys_id of the parent Scripted REST API service (sys_ws_definition)",
    )
    name: str = Field(..., description="Name of the resource")
    http_method: str = Field(
        ...,
        description="HTTP method: GET, POST, PUT, PATCH, or DELETE",
    )
    relative_path: str = Field(
        ...,
        description="Relative path for the resource, e.g. '/generate'",
    )
    operation_script: str = Field(
        ...,
        description="Server-side JavaScript that handles the request",
    )
    short_description: Optional[str] = Field(
        None, description="Short description of the resource"
    )
    active: bool = Field(True, description="Whether the resource is active")


class ScriptedRestResponse(BaseModel):
    """Response from scripted REST API operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    sys_id: Optional[str] = Field(None, description="sys_id of the created record")
    name: Optional[str] = Field(None, description="Name of the created record")


def create_scripted_rest_api(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateScriptedRestApiParams,
) -> ScriptedRestResponse:
    """Create a new Scripted REST API service in ServiceNow.

    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for the request.

    Returns:
        A response indicating the result of the operation.
    """
    url = f"{config.instance_url}/api/now/table/sys_ws_definition"

    body = {
        "name": params.name,
        "is_active": str(params.is_active).lower(),
    }

    if params.api_id:
        body["service_id"] = params.api_id

    if params.short_description:
        body["short_description"] = params.short_description

    headers = auth_manager.get_headers()

    try:
        response = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        if "result" not in data:
            return ScriptedRestResponse(
                success=False,
                message="Failed to create Scripted REST API service",
            )

        result = data["result"]

        return ScriptedRestResponse(
            success=True,
            message=f"Created Scripted REST API service: {result.get('name')}",
            sys_id=result.get("sys_id"),
            name=result.get("name"),
        )

    except Exception as e:
        logger.error(f"Error creating Scripted REST API service: {e}")
        return ScriptedRestResponse(
            success=False,
            message=f"Error creating Scripted REST API service: {str(e)}",
        )


def create_scripted_rest_resource(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateScriptedRestResourceParams,
) -> ScriptedRestResponse:
    """Create a new Scripted REST API resource (operation) in ServiceNow.

    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for the request.

    Returns:
        A response indicating the result of the operation.
    """
    url = f"{config.instance_url}/api/now/table/sys_ws_operation"

    body = {
        "web_service_definition": params.web_service_definition,
        "name": params.name,
        "http_method": params.http_method.upper(),
        "relative_path": params.relative_path,
        "operation_script": params.operation_script,
        "active": str(params.active).lower(),
    }

    if params.short_description:
        body["short_description"] = params.short_description

    headers = auth_manager.get_headers()

    try:
        response = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        if "result" not in data:
            return ScriptedRestResponse(
                success=False,
                message="Failed to create Scripted REST API resource",
            )

        result = data["result"]

        return ScriptedRestResponse(
            success=True,
            message=f"Created Scripted REST API resource: {result.get('name')}",
            sys_id=result.get("sys_id"),
            name=result.get("name"),
        )

    except Exception as e:
        logger.error(f"Error creating Scripted REST API resource: {e}")
        return ScriptedRestResponse(
            success=False,
            message=f"Error creating Scripted REST API resource: {str(e)}",
        )
