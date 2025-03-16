"""
Task tools for the ServiceNow MCP server.

This module provides tools for managing tasks in ServiceNow.
"""

import logging
from typing import Optional, List

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class CreateTaskParams(BaseModel):
    """Parameters for creating a task."""

    short_description: str = Field(..., description="Short description of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    caller_id: Optional[str] = Field(None, description="User who reported the task")
    category: Optional[str] = Field(None, description="Category of the task")
    priority: Optional[str] = Field(None, description="Priority of the task")
    assigned_to: Optional[str] = Field(None, description="User assigned to the task")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the task")
    due_date: Optional[str] = Field(None, description="Due date for the task (format: YYYY-MM-DD)")


class UpdateTaskParams(BaseModel):
    """Parameters for updating a task."""

    task_id: str = Field(..., description="Task ID or sys_id")
    short_description: Optional[str] = Field(None, description="Short description of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    state: Optional[str] = Field(None, description="State of the task")
    category: Optional[str] = Field(None, description="Category of the task")
    priority: Optional[str] = Field(None, description="Priority of the task")
    assigned_to: Optional[str] = Field(None, description="User assigned to the task")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the task")
    work_notes: Optional[str] = Field(None, description="Work notes to add to the task")
    close_notes: Optional[str] = Field(None, description="Close notes to add to the task")
    due_date: Optional[str] = Field(None, description="Due date for the task (format: YYYY-MM-DD)")


class AddTaskCommentParams(BaseModel):
    """Parameters for adding a comment to a task."""

    task_id: str = Field(..., description="Task ID or sys_id")
    comment: str = Field(..., description="Comment to add to the task")
    is_work_note: bool = Field(False, description="Whether the comment is a work note")


class CompleteTaskParams(BaseModel):
    """Parameters for completing a task."""

    task_id: str = Field(..., description="Task ID or sys_id")
    completion_notes: str = Field(..., description="Completion notes for the task")


class ListTasksParams(BaseModel):
    """Parameters for listing tasks."""
    
    limit: int = Field(10, description="Maximum number of tasks to return")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by task state")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")
    category: Optional[str] = Field(None, description="Filter by category")
    query: Optional[str] = Field(None, description="Search query for tasks")


class GetTaskParams(BaseModel):
    """Parameters for getting a task by number."""

    task_number: str = Field(..., description="Task number to retrieve")


class TaskResponse(BaseModel):
    """Response from task operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    task_id: Optional[str] = Field(None, description="ID of the affected task")
    task_number: Optional[str] = Field(None, description="Number of the affected task")


def create_task(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateTaskParams,
) -> TaskResponse:
    """
    Create a new task in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the task.

    Returns:
        Response with the created task details.
    """
    api_url = f"{config.api_url}/table/task"

    # Build request data
    data = {
        "short_description": params.short_description,
    }

    if params.description:
        data["description"] = params.description
    if params.caller_id:
        data["caller_id"] = params.caller_id
    if params.category:
        data["category"] = params.category
    if params.priority:
        data["priority"] = params.priority
    if params.assigned_to:
        data["assigned_to"] = params.assigned_to
    if params.assignment_group:
        data["assignment_group"] = params.assignment_group
    if params.due_date:
        data["due_date"] = params.due_date

    # Make request
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return TaskResponse(
            success=True,
            message="Task created successfully",
            task_id=result.get("sys_id"),
            task_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to create task: {e}")
        return TaskResponse(
            success=False,
            message=f"Failed to create task: {str(e)}",
        )


def update_task(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateTaskParams,
) -> TaskResponse:
    """
    Update an existing task in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the task.

    Returns:
        Response with the updated task details.
    """
    # Determine if task_id is a number or sys_id
    task_id = params.task_id
    if len(task_id) == 32 and all(c in "0123456789abcdef" for c in task_id):
        # This is likely a sys_id
        api_url = f"{config.api_url}/table/task/{task_id}"
    else:
        # This is likely a task number
        # First, we need to get the sys_id
        try:
            query_url = f"{config.api_url}/table/task"
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
                return TaskResponse(
                    success=False,
                    message=f"Task not found: {task_id}",
                )

            task_id = result[0].get("sys_id")
            api_url = f"{config.api_url}/table/task/{task_id}"

        except requests.RequestException as e:
            logger.error(f"Failed to get task: {e}")
            return TaskResponse(
                success=False,
                message=f"Failed to get task: {str(e)}",
            )

    # Build request data
    data = {}
    if params.short_description:
        data["short_description"] = params.short_description
    if params.description:
        data["description"] = params.description
    if params.state:
        data["state"] = params.state
    if params.category:
        data["category"] = params.category
    if params.priority:
        data["priority"] = params.priority
    if params.assigned_to:
        data["assigned_to"] = params.assigned_to
    if params.assignment_group:
        data["assignment_group"] = params.assignment_group
    if params.due_date:
        data["due_date"] = params.due_date

    # Handle work notes and close notes
    if params.work_notes:
        data["work_notes"] = params.work_notes
    if params.close_notes:
        data["close_notes"] = params.close_notes

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return TaskResponse(
            success=True,
            message="Task updated successfully",
            task_id=result.get("sys_id"),
            task_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to update task: {e}")
        return TaskResponse(
            success=False,
            message=f"Failed to update task: {str(e)}",
        )


def add_task_comment(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: AddTaskCommentParams,
) -> TaskResponse:
    """
    Add a comment to a task in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for adding the comment.

    Returns:
        Response with the result of the operation.
    """
    # Determine if task_id is a number or sys_id
    task_id = params.task_id
    if len(task_id) == 32 and all(c in "0123456789abcdef" for c in task_id):
        # This is likely a sys_id
        api_url = f"{config.api_url}/table/task/{task_id}"
    else:
        # This is likely a task number
        # First, we need to get the sys_id
        try:
            query_url = f"{config.api_url}/table/task"
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
                return TaskResponse(
                    success=False,
                    message=f"Task not found: {task_id}",
                )

            task_id = result[0].get("sys_id")
            api_url = f"{config.api_url}/table/task/{task_id}"

        except requests.RequestException as e:
            logger.error(f"Failed to get task: {e}")
            return TaskResponse(
                success=False,
                message=f"Failed to get task: {str(e)}",
            )

    # Build request data
    data = {}
    if params.is_work_note:
        data["work_notes"] = params.comment
    else:
        data["comments"] = params.comment

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return TaskResponse(
            success=True,
            message="Comment added successfully",
            task_id=result.get("sys_id"),
            task_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to add comment: {e}")
        return TaskResponse(
            success=False,
            message=f"Failed to add comment: {str(e)}",
        )


def complete_task(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CompleteTaskParams,
) -> TaskResponse:
    """
    Complete a task in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for completing the task.

    Returns:
        Response with the result of the operation.
    """
    # Determine if task_id is a number or sys_id
    task_id = params.task_id
    if len(task_id) == 32 and all(c in "0123456789abcdef" for c in task_id):
        # This is likely a sys_id
        api_url = f"{config.api_url}/table/task/{task_id}"
    else:
        # This is likely a task number
        # First, we need to get the sys_id
        try:
            query_url = f"{config.api_url}/table/task"
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
                return TaskResponse(
                    success=False,
                    message=f"Task not found: {task_id}",
                )

            task_id = result[0].get("sys_id")
            api_url = f"{config.api_url}/table/task/{task_id}"

        except requests.RequestException as e:
            logger.error(f"Failed to get task: {e}")
            return TaskResponse(
                success=False,
                message=f"Failed to get task: {str(e)}",
            )

    # Build request data
    data = {
        "state": "3",  # Complete (may vary depending on ServiceNow configuration)
        "close_notes": params.completion_notes,
    }

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return TaskResponse(
            success=True,
            message="Task completed successfully",
            task_id=result.get("sys_id"),
            task_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to complete task: {e}")
        return TaskResponse(
            success=False,
            message=f"Failed to complete task: {str(e)}",
        )


def list_tasks(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListTasksParams,
) -> dict:
    """
    List tasks from ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing tasks.

    Returns:
        Dictionary with list of tasks.
    """
    api_url = f"{config.api_url}/table/task"

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
    if params.category:
        filters.append(f"category={params.category}")
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

        result = response.json().get("result", [])
        tasks = []

        for task_data in result:
            # Handle assigned_to field which could be a string or a dictionary
            assigned_to = task_data.get("assigned_to")
            if isinstance(assigned_to, dict):
                assigned_to = assigned_to.get("display_value")

            task = {
                "sys_id": task_data.get("sys_id"),
                "number": task_data.get("number"),
                "short_description": task_data.get("short_description"),
                "description": task_data.get("description"),
                "state": task_data.get("state"),
                "priority": task_data.get("priority"),
                "assigned_to": assigned_to,
                "category": task_data.get("category"),
                "due_date": task_data.get("due_date"),
                "created_on": task_data.get("sys_created_on"),
                "updated_on": task_data.get("sys_updated_on"),
            }
            tasks.append(task)

        return {
            "success": True,
            "count": len(tasks),
            "tasks": tasks,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list tasks: {e}")
        return {
            "success": False,
            "message": f"Failed to list tasks: {str(e)}",
            "tasks": [],
        }


def get_task(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetTaskParams,
) -> dict:
    """
    Get a task from ServiceNow by its number.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for getting the task.

    Returns:
        Dictionary with task details including short description, description, and priority.
    """
    api_url = f"{config.api_url}/table/task"

    # Build query parameters
    query_params = {
        "sysparm_query": f"number={params.task_number}",
        "sysparm_limit": 1,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }

    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", [])
        if not result:
            return {
                "success": False,
                "message": f"Task not found: {params.task_number}",
            }

        task_data = result[0]

        # Handle assigned_to field which could be a string or a dictionary
        assigned_to = task_data.get("assigned_to")
        if isinstance(assigned_to, dict):
            assigned_to = assigned_to.get("display_value")

        task = {
            "success": True,
            "sys_id": task_data.get("sys_id"),
            "number": task_data.get("number"),
            "short_description": task_data.get("short_description"),
            "description": task_data.get("description"),
            "state": task_data.get("state"),
            "priority": task_data.get("priority"),
            "assigned_to": assigned_to,
            "category": task_data.get("category"),
            "due_date": task_data.get("due_date"),
            "created_on": task_data.get("sys_created_on"),
            "updated_on": task_data.get("sys_updated_on"),
        }

        return task

    except requests.RequestException as e:
        logger.error(f"Failed to get task: {e}")
        return {
            "success": False,
            "message": f"Failed to get task: {str(e)}",
        }
