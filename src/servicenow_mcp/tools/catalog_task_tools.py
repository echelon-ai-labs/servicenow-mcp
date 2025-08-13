"""
Service Catalog Task tools for the ServiceNow MCP server.

This module provides tools for managing service catalog tasks (sc_task) in ServiceNow.
"""

import logging
from typing import Optional, List

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ListCatalogTasksParams(BaseModel):
    """Parameters for listing service catalog tasks."""
    
    limit: int = Field(10, description="Maximum number of catalog tasks to return")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by task state")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")
    assignment_group: Optional[str] = Field(None, description="Filter by assignment group")
    request: Optional[str] = Field(None, description="Filter by parent request sys_id")
    query: Optional[str] = Field(None, description="Search query for catalog tasks")


class GetCatalogTaskParams(BaseModel):
    """Parameters for getting a specific catalog task."""
    
    task_id: str = Field(..., description="Catalog task ID or sys_id")


class UpdateCatalogTaskParams(BaseModel):
    """Parameters for updating a catalog task."""
    
    task_id: str = Field(..., description="Catalog task ID or sys_id")
    state: Optional[str] = Field(None, description="State of the task")
    assigned_to: Optional[str] = Field(None, description="User assigned to the task")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the task")
    work_notes: Optional[str] = Field(None, description="Work notes to add to the task")
    close_notes: Optional[str] = Field(None, description="Close notes for the task")


class CatalogTaskResponse(BaseModel):
    """Response from catalog task operations."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    task_id: Optional[str] = Field(None, description="ID of the affected task")
    task_number: Optional[str] = Field(None, description="Number of the affected task")


def list_catalog_tasks(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCatalogTasksParams,
) -> dict:
    """
    List service catalog tasks from ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing catalog tasks.

    Returns:
        Dictionary with list of catalog tasks.
    """
    api_url = f"{config.api_url}/table/sc_task"

    # Build query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Add filters
    filters = []
    if params.state:
        filters.append(f"state={params.state}")
    if params.assigned_to:
        filters.append(f"assigned_to={params.assigned_to}")
    if params.assignment_group:
        filters.append(f"assignment_group={params.assignment_group}")
    if params.request:
        filters.append(f"request={params.request}")
    if params.query:
        filters.append(f"short_descriptionLIKE{params.query}^ORdescriptionLIKE{params.query}")
    
    if filters:
        query_params["sysparm_query"] = "^".join(filters)
    
    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        tasks = []
        
        for task_data in data.get("result", []):
            # Handle assigned_to field which could be a string or a dictionary
            assigned_to = task_data.get("assigned_to")
            if isinstance(assigned_to, dict):
                assigned_to = assigned_to.get("display_value")
            
            # Handle assignment_group field
            assignment_group = task_data.get("assignment_group")
            if isinstance(assignment_group, dict):
                assignment_group = assignment_group.get("display_value")
            
            # Handle request field
            request_ref = task_data.get("request")
            if isinstance(request_ref, dict):
                request_ref = request_ref.get("display_value")
            
            task = {
                "sys_id": task_data.get("sys_id"),
                "number": task_data.get("number"),
                "short_description": task_data.get("short_description"),
                "description": task_data.get("description"),
                "state": task_data.get("state"),
                "assigned_to": assigned_to,
                "assignment_group": assignment_group,
                "request": request_ref,
                "request_sys_id": task_data.get("request", {}).get("value") if isinstance(task_data.get("request"), dict) else task_data.get("request"),
                "created_on": task_data.get("sys_created_on"),
                "updated_on": task_data.get("sys_updated_on"),
                "due_date": task_data.get("due_date"),
                "priority": task_data.get("priority"),
            }
            tasks.append(task)
        
        return {
            "success": True,
            "message": f"Found {len(tasks)} catalog tasks",
            "tasks": tasks
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to list catalog tasks: {e}")
        return {
            "success": False,
            "message": f"Failed to list catalog tasks: {str(e)}",
            "tasks": []
        }


def get_catalog_task(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCatalogTaskParams,
) -> dict:
    """
    Get a specific service catalog task from ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for getting the catalog task.

    Returns:
        Dictionary with the catalog task details.
    """
    # Determine if task_id is a number or sys_id
    task_id = params.task_id
    if len(task_id) == 32 and all(c in "0123456789abcdef" for c in task_id):
        # This is likely a sys_id
        api_url = f"{config.api_url}/table/sc_task/{task_id}"
    else:
        # This is likely a task number, need to query first
        api_url = f"{config.api_url}/table/sc_task"
        query_params = {
            "sysparm_query": f"number={task_id}",
            "sysparm_limit": 1,
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        }
        
        try:
            response = requests.get(
                api_url,
                params=query_params,
                headers=auth_manager.get_headers(),
                timeout=config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            result = data.get("result", [])
            
            if not result:
                return {
                    "success": False,
                    "message": f"Catalog task not found: {task_id}",
                }
            
            task_data = result[0]
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch catalog task: {e}")
            return {
                "success": False,
                "message": f"Failed to fetch catalog task: {str(e)}",
            }
    
    # If we have a sys_id, fetch directly
    if len(task_id) == 32 and all(c in "0123456789abcdef" for c in task_id):
        try:
            response = requests.get(
                api_url,
                params={
                    "sysparm_display_value": "true",
                    "sysparm_exclude_reference_link": "true",
                },
                headers=auth_manager.get_headers(),
                timeout=config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            task_data = data.get("result", {})
            
            if not task_data:
                return {
                    "success": False,
                    "message": f"Catalog task not found: {task_id}",
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch catalog task: {e}")
            return {
                "success": False,
                "message": f"Failed to fetch catalog task: {str(e)}",
            }
    
    # Process the task data
    assigned_to = task_data.get("assigned_to")
    if isinstance(assigned_to, dict):
        assigned_to = assigned_to.get("display_value")
    
    assignment_group = task_data.get("assignment_group")
    if isinstance(assignment_group, dict):
        assignment_group = assignment_group.get("display_value")
    
    request_ref = task_data.get("request")
    if isinstance(request_ref, dict):
        request_ref = request_ref.get("display_value")
    
    task = {
        "sys_id": task_data.get("sys_id"),
        "number": task_data.get("number"),
        "short_description": task_data.get("short_description"),
        "description": task_data.get("description"),
        "state": task_data.get("state"),
        "assigned_to": assigned_to,
        "assignment_group": assignment_group,
        "request": request_ref,
        "request_sys_id": task_data.get("request", {}).get("value") if isinstance(task_data.get("request"), dict) else task_data.get("request"),
        "created_on": task_data.get("sys_created_on"),
        "updated_on": task_data.get("sys_updated_on"),
        "due_date": task_data.get("due_date"),
        "priority": task_data.get("priority"),
        "work_notes": task_data.get("work_notes"),
        "close_notes": task_data.get("close_notes"),
    }
    
    return {
        "success": True,
        "message": f"Catalog task {task_data.get('number', task_id)} found",
        "task": task,
    }


def update_catalog_task(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateCatalogTaskParams,
) -> CatalogTaskResponse:
    """
    Update an existing service catalog task in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the catalog task.

    Returns:
        Response with the updated catalog task details.
    """
    # Determine if task_id is a number or sys_id
    task_id = params.task_id
    if len(task_id) == 32 and all(c in "0123456789abcdef" for c in task_id):
        # This is likely a sys_id
        api_url = f"{config.api_url}/table/sc_task/{task_id}"
    else:
        # This is likely a task number
        # First, we need to get the sys_id
        try:
            query_url = f"{config.api_url}/table/sc_task"
            query_params = {
                "sysparm_query": f"number={task_id}",
                "sysparm_limit": 1,
            }

            response = requests.get(
                query_url,
                params=query_params,
                headers=auth_manager.get_headers(),
                timeout=config.timeout,
            )
            response.raise_for_status()

            result = response.json().get("result", [])
            if not result:
                return CatalogTaskResponse(
                    success=False,
                    message=f"Catalog task not found: {task_id}",
                )

            task_id = result[0].get("sys_id")
            api_url = f"{config.api_url}/table/sc_task/{task_id}"

        except requests.RequestException as e:
            logger.error(f"Failed to find catalog task: {e}")
            return CatalogTaskResponse(
                success=False,
                message=f"Failed to find catalog task: {str(e)}",
            )

    # Build request data
    data = {}

    if params.state:
        data["state"] = params.state
    if params.assigned_to:
        data["assigned_to"] = params.assigned_to
    if params.assignment_group:
        data["assignment_group"] = params.assignment_group
    if params.work_notes:
        data["work_notes"] = params.work_notes
    if params.close_notes:
        data["close_notes"] = params.close_notes

    # Make request
    try:
        response = requests.put(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return CatalogTaskResponse(
            success=True,
            message="Catalog task updated successfully",
            task_id=result.get("sys_id"),
            task_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to update catalog task: {e}")
        return CatalogTaskResponse(
            success=False,
            message=f"Failed to update catalog task: {str(e)}",
        )