"""
Time Card management tools for the ServiceNow MCP server.

This module provides tools for managing Time Cards (time_card table) in ServiceNow.
"""

import logging
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig
from servicenow_mcp.utils.helpers import (
    get_headers as _get_headers,
    get_instance_url as _get_instance_url,
    unwrap_and_validate_params as _unwrap_and_validate_params,
)

logger = logging.getLogger(__name__)


# Day name to field name mapping
DAY_FIELDS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class ListTimeCardsParams(BaseModel):
    """Parameters for listing time cards."""

    task_number: Optional[str] = Field(None, description="Filter by SCTASK number (e.g. SCTASK0525799)")
    task_sys_id: Optional[str] = Field(None, description="Filter by task sys_id")
    user: Optional[str] = Field(None, description="Filter by username or sys_id")
    week_start: Optional[str] = Field(None, description="Filter by week start date (YYYY-MM-DD)")
    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")


class CreateTimeCardParams(BaseModel):
    """Parameters for creating a time card entry."""

    task_number: str = Field(..., description="SCTASK number (e.g. SCTASK0525799)")
    week_start: str = Field(..., description="Week start date (YYYY-MM-DD)")
    monday: Optional[float] = Field(0, description="Hours for Monday")
    tuesday: Optional[float] = Field(0, description="Hours for Tuesday")
    wednesday: Optional[float] = Field(0, description="Hours for Wednesday")
    thursday: Optional[float] = Field(0, description="Hours for Thursday")
    friday: Optional[float] = Field(0, description="Hours for Friday")
    saturday: Optional[float] = Field(0, description="Hours for Saturday")
    sunday: Optional[float] = Field(0, description="Hours for Sunday")
    short_description: Optional[str] = Field(None, description="Description of work done")


class UpdateTimeCardParams(BaseModel):
    """Parameters for updating an existing time card entry."""

    time_card_sys_id: str = Field(..., description="sys_id of the time card record to update")
    monday: Optional[float] = Field(None, description="Hours for Monday")
    tuesday: Optional[float] = Field(None, description="Hours for Tuesday")
    wednesday: Optional[float] = Field(None, description="Hours for Wednesday")
    thursday: Optional[float] = Field(None, description="Hours for Thursday")
    friday: Optional[float] = Field(None, description="Hours for Friday")
    saturday: Optional[float] = Field(None, description="Hours for Saturday")
    sunday: Optional[float] = Field(None, description="Hours for Sunday")
    short_description: Optional[str] = Field(None, description="Description of work done")
    state: Optional[str] = Field(None, description="State of the time card")


def _resolve_task_sys_id(instance_url: str, headers: Dict, task_number: str) -> Optional[str]:
    """Resolve a SCTASK number to its sys_id."""
    url = f"{instance_url}/api/now/table/sc_task"
    resp = requests.get(url, headers=headers, params={
        "sysparm_query": f"number={task_number}",
        "sysparm_limit": 1,
        "sysparm_fields": "sys_id",
    })
    resp.raise_for_status()
    records = resp.json().get("result", [])
    return records[0]["sys_id"] if records else None


def _format_time_card(tc: Dict) -> Dict:
    """Extract relevant fields from a raw time card record."""
    return {
        "sys_id": tc.get("sys_id"),
        "task": tc.get("task"),
        "user": tc.get("user"),
        "week_start": tc.get("week_start"),
        "short_description": tc.get("short_description"),
        "state": tc.get("state"),
        "monday": tc.get("monday", 0),
        "tuesday": tc.get("tuesday", 0),
        "wednesday": tc.get("wednesday", 0),
        "thursday": tc.get("thursday", 0),
        "friday": tc.get("friday", 0),
        "saturday": tc.get("saturday", 0),
        "sunday": tc.get("sunday", 0),
        "total": tc.get("total"),
    }


def list_time_cards(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """List time cards, optionally filtered by task or user."""
    result = _unwrap_and_validate_params(params, ListTimeCardsParams)
    if not result["success"]:
        return result
    validated = result["params"]

    instance_url = _get_instance_url(auth_manager, server_config)
    if not instance_url:
        return {"success": False, "message": "Cannot find instance_url"}
    headers = _get_headers(auth_manager, server_config)
    if not headers:
        return {"success": False, "message": "Cannot find get_headers method"}

    query_parts = []

    # Resolve task number to sys_id if provided
    if validated.task_number:
        try:
            task_sys_id = _resolve_task_sys_id(instance_url, headers, validated.task_number)
            if not task_sys_id:
                return {"success": False, "message": f"Task not found: {validated.task_number}"}
            query_parts.append(f"task={task_sys_id}")
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error resolving task: {str(e)}"}
    elif validated.task_sys_id:
        query_parts.append(f"task={validated.task_sys_id}")

    if validated.user:
        query_parts.append(f"user.user_name={validated.user}^ORuser={validated.user}")
    if validated.week_start:
        query_parts.append(f"week_start={validated.week_start}")

    url = f"{instance_url}/api/now/table/time_card"
    query_params: Dict[str, Any] = {
        "sysparm_limit": validated.limit,
        "sysparm_offset": validated.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    if query_parts:
        query_params["sysparm_query"] = "^".join(query_parts)

    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        cards = response.json().get("result", [])
        return {
            "success": True,
            "time_cards": [_format_time_card(tc) for tc in cards],
            "count": len(cards),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing time cards: {e}")
        return {"success": False, "message": f"Error listing time cards: {str(e)}"}


def create_time_card(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new time card entry for a task."""
    result = _unwrap_and_validate_params(params, CreateTimeCardParams, required_fields=["task_number", "week_start"])
    if not result["success"]:
        return result
    validated = result["params"]

    instance_url = _get_instance_url(auth_manager, server_config)
    if not instance_url:
        return {"success": False, "message": "Cannot find instance_url"}
    headers = _get_headers(auth_manager, server_config)
    if not headers:
        return {"success": False, "message": "Cannot find get_headers method"}
    headers["Content-Type"] = "application/json"

    # Resolve task number to sys_id
    try:
        task_sys_id = _resolve_task_sys_id(instance_url, headers, validated.task_number)
        if not task_sys_id:
            return {"success": False, "message": f"Task not found: {validated.task_number}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Error resolving task: {str(e)}"}

    data: Dict[str, Any] = {
        "task": task_sys_id,
        "week_start": validated.week_start,
        "monday": validated.monday or 0,
        "tuesday": validated.tuesday or 0,
        "wednesday": validated.wednesday or 0,
        "thursday": validated.thursday or 0,
        "friday": validated.friday or 0,
        "saturday": validated.saturday or 0,
        "sunday": validated.sunday or 0,
    }
    if validated.short_description:
        data["short_description"] = validated.short_description

    url = f"{instance_url}/api/now/table/time_card"
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        tc = response.json().get("result", {})
        return {
            "success": True,
            "message": "Time card created successfully",
            "time_card": _format_time_card(tc),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating time card: {e}")
        return {"success": False, "message": f"Error creating time card: {str(e)}"}


def update_time_card(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing time card entry."""
    result = _unwrap_and_validate_params(params, UpdateTimeCardParams, required_fields=["time_card_sys_id"])
    if not result["success"]:
        return result
    validated = result["params"]

    instance_url = _get_instance_url(auth_manager, server_config)
    if not instance_url:
        return {"success": False, "message": "Cannot find instance_url"}
    headers = _get_headers(auth_manager, server_config)
    if not headers:
        return {"success": False, "message": "Cannot find get_headers method"}
    headers["Content-Type"] = "application/json"

    data: Dict[str, Any] = {}
    for day in DAY_FIELDS:
        val = getattr(validated, day, None)
        if val is not None:
            data[day] = val
    if validated.short_description is not None:
        data["short_description"] = validated.short_description
    if validated.state is not None:
        data["state"] = validated.state

    url = f"{instance_url}/api/now/table/time_card/{validated.time_card_sys_id}"
    try:
        response = requests.patch(url, json=data, headers=headers)
        response.raise_for_status()
        tc = response.json().get("result", {})
        return {
            "success": True,
            "message": "Time card updated successfully",
            "time_card": _format_time_card(tc),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating time card: {e}")
        return {"success": False, "message": f"Error updating time card: {str(e)}"}
