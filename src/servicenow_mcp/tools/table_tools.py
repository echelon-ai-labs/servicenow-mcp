"""
Generic table tools for the ServiceNow MCP server.

This module provides tools for querying arbitrary ServiceNow tables.
"""

import logging
import re
from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

_TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class QueryTableParams(BaseModel):
    """Parameters for querying a generic ServiceNow table."""

    table: str = Field(..., description="ServiceNow table name, for example 'incident'.")
    query: Optional[str] = Field(
        None,
        description="Encoded ServiceNow query for sysparm_query (for example 'active=true^priority=1').",
    )
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return.")
    offset: int = Field(0, ge=0, description="Pagination offset.")
    fields: Optional[List[str]] = Field(
        None,
        description="Optional list of fields to return via sysparm_fields.",
    )
    display_value: Literal["false", "true", "all"] = Field(
        "false",
        description="ServiceNow sysparm_display_value option.",
    )


def query_table(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: QueryTableParams,
) -> Dict[str, Any]:
    """
    Query an arbitrary ServiceNow table through the Table API.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Query parameters including table, filter, and pagination.

    Returns:
        Dictionary containing success flag, metadata, and records.
    """
    if not _TABLE_NAME_PATTERN.match(params.table):
        return {
            "success": False,
            "message": (
                "Invalid table name. Use only letters, numbers, and underscores, "
                "and start with a letter."
            ),
            "table": params.table,
        }

    api_url = f"{config.api_url}/table/{params.table}"
    request_params: Dict[str, str] = {
        "sysparm_limit": str(params.limit),
        "sysparm_offset": str(params.offset),
        "sysparm_display_value": params.display_value,
    }

    if params.query:
        request_params["sysparm_query"] = params.query
    if params.fields:
        request_params["sysparm_fields"] = ",".join(params.fields)

    try:
        response = requests.get(
            api_url,
            params=request_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        records = payload.get("result", [])
        count = len(records) if isinstance(records, list) else 1 if records else 0

        return {
            "success": True,
            "table": params.table,
            "count": count,
            "result": records,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to query table '{params.table}': {e}")
        return {
            "success": False,
            "message": f"Failed to query table '{params.table}': {str(e)}",
            "table": params.table,
        }
