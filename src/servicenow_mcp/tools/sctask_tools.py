"""
Service Catalog Task (SCTASK) management tools for the ServiceNow MCP server.

This module provides tools for managing Service Catalog Tasks (sc_task table).
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


class GetSCTaskParams(BaseModel):
    """Parameters for getting a specific SCTASK by number."""

    task_number: str = Field(..., description="SCTASK number (e.g. SCTASK0525799)")


class UpdateSCTaskParams(BaseModel):
    """Parameters for updating a Service Catalog Task."""

    task_number: str = Field(..., description="SCTASK number or sys_id")
    state: Optional[str] = Field(
        None,
        description="State (1=Open, 2=Work in Progress, 3=Closed Complete, 4=Closed Incomplete, 7=Closed Skipped)",
    )
    assigned_to: Optional[str] = Field(None, description="User assigned to the task")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the task")
    short_description: Optional[str] = Field(None, description="Short description of the task")
    work_notes: Optional[str] = Field(None, description="Work notes to add")
    close_notes: Optional[str] = Field(None, description="Closure notes")
    time_worked: Optional[str] = Field(
        None,
        description="Time worked on the task in HH:MM:SS format (e.g. '02:30:00' for 2.5 hours)",
    )


class ListSCTasksParams(BaseModel):
    """Parameters for listing Service Catalog Tasks."""

    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    state: Optional[str] = Field(None, description="Filter by state")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user (username or sys_id)")
    assignment_group: Optional[str] = Field(None, description="Filter by assignment group")
    query: Optional[str] = Field(None, description="Additional ServiceNow query string")


def get_sctask(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Get a Service Catalog Task by number."""
    result = _unwrap_and_validate_params(params, GetSCTaskParams, required_fields=["task_number"])
    if not result["success"]:
        return result

    validated = result["params"]

    instance_url = _get_instance_url(auth_manager, server_config)
    if not instance_url:
        return {"success": False, "message": "Cannot find instance_url"}

    headers = _get_headers(auth_manager, server_config)
    if not headers:
        return {"success": False, "message": "Cannot find get_headers method"}

    url = f"{instance_url}/api/now/table/sc_task"
    query_params = {
        "sysparm_query": f"number={validated.task_number}",
        "sysparm_limit": 1,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }

    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        records = response.json().get("result", [])

        if not records:
            return {"success": False, "message": f"SCTASK not found: {validated.task_number}"}

        task = records[0]
        return {
            "success": True,
            "message": f"Found SCTASK {validated.task_number}",
            "sctask": {
                "sys_id": task.get("sys_id"),
                "number": task.get("number"),
                "short_description": task.get("short_description"),
                "description": task.get("description"),
                "state": task.get("state"),
                "priority": task.get("priority"),
                "assigned_to": task.get("assigned_to"),
                "assignment_group": task.get("assignment_group"),
                "request_item": task.get("request_item"),
                "request": task.get("request"),
                "opened_at": task.get("opened_at"),
                "closed_at": task.get("closed_at"),
                "time_worked": task.get("time_worked"),
                "work_notes": task.get("work_notes"),
                "close_notes": task.get("close_notes"),
            },
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SCTASK: {e}")
        return {"success": False, "message": f"Error fetching SCTASK: {str(e)}"}


def list_sctasks(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """List Service Catalog Tasks with optional filters."""
    result = _unwrap_and_validate_params(params, ListSCTasksParams)
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
    if validated.state:
        query_parts.append(f"state={validated.state}")
    if validated.assigned_to:
        query_parts.append(f"assigned_to.user_name={validated.assigned_to}^ORASSIGNEDTOassigned_to={validated.assigned_to}")
    if validated.assignment_group:
        query_parts.append(f"assignment_group={validated.assignment_group}")
    if validated.query:
        query_parts.append(validated.query)

    url = f"{instance_url}/api/now/table/sc_task"
    query_params = {
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
        tasks = response.json().get("result", [])

        return {
            "success": True,
            "sctasks": tasks,
            "count": len(tasks),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing SCTASKs: {e}")
        return {"success": False, "message": f"Error listing SCTASKs: {str(e)}"}


def update_sctask(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Update a Service Catalog Task."""
    result = _unwrap_and_validate_params(params, UpdateSCTaskParams, required_fields=["task_number"])
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

    # Resolve number to sys_id if needed
    task_id = validated.task_number
    if task_id.startswith("SCTASK"):
        lookup_url = f"{instance_url}/api/now/table/sc_task"
        lookup_params = {
            "sysparm_query": f"number={task_id}",
            "sysparm_limit": 1,
            "sysparm_fields": "sys_id",
        }
        try:
            lookup_resp = requests.get(lookup_url, headers=headers, params=lookup_params)
            lookup_resp.raise_for_status()
            records = lookup_resp.json().get("result", [])
            if not records:
                return {"success": False, "message": f"SCTASK not found: {task_id}"}
            task_id = records[0]["sys_id"]
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error resolving SCTASK number: {str(e)}"}

    data: Dict[str, Any] = {}
    if validated.state is not None:
        data["state"] = validated.state
    if validated.assigned_to is not None:
        data["assigned_to"] = validated.assigned_to
    if validated.assignment_group is not None:
        data["assignment_group"] = validated.assignment_group
    if validated.short_description is not None:
        data["short_description"] = validated.short_description
    if validated.work_notes is not None:
        data["work_notes"] = validated.work_notes
    if validated.close_notes is not None:
        data["close_notes"] = validated.close_notes
    if validated.time_worked is not None:
        # Read current time_worked and add to it instead of replacing
        try:
            lookup_url = f"{instance_url}/api/now/table/sc_task/{task_id}"
            lookup_resp = requests.get(lookup_url, headers=headers, params={"sysparm_fields": "time_worked"})
            lookup_resp.raise_for_status()
            current_raw = lookup_resp.json().get("result", {}).get("time_worked", "")
            # Parse current value (format: "1970-01-01 HH:MM:SS")
            current_seconds = 0
            if current_raw:
                try:
                    time_part = current_raw.split(" ")[-1]  # get "HH:MM:SS"
                    h, m, s = (int(x) for x in time_part.split(":"))
                    current_seconds = h * 3600 + m * 60 + s
                except Exception:
                    current_seconds = 0
            # Parse the time to add (format: "HH:MM:SS")
            add_h, add_m, add_s = (int(x) for x in validated.time_worked.split(":"))
            add_seconds = add_h * 3600 + add_m * 60 + add_s
            total_seconds = current_seconds + add_seconds
            total_h = total_seconds // 3600
            total_m = (total_seconds % 3600) // 60
            total_s = total_seconds % 60
            data["time_worked"] = f"{total_h:02}:{total_m:02}:{total_s:02}"
        except Exception:
            data["time_worked"] = validated.time_worked

    url = f"{instance_url}/api/now/table/sc_task/{task_id}"

    try:
        response = requests.patch(url, json=data, headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "message": f"SCTASK {validated.task_number} updated successfully",
            "sctask": response.json().get("result", {}),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating SCTASK: {e}")
        return {"success": False, "message": f"Error updating SCTASK: {str(e)}"}
