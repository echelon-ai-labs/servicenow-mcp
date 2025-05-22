"""
Scrum Task management tools for the ServiceNow MCP server.

This module provides tools for managing stories in ServiceNow.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)

class CreateScrumTaskParams(BaseModel):
    """Parameters for creating a scrum task."""

    story: str = Field(..., description="Short description of the story. It requires the System ID of the story.")
    short_description: str = Field(..., description="Short description of the scrum task")
    priority: Optional[str] = Field(None, description="Priority of scrum task (1 is Critical, 2 is High, 3 is Moderate, 4 is Low)")
    planned_hours: Optional[int] = Field(None, description="Planned hours for the scrum task")
    remaining_hours: Optional[int] = Field(None, description="Remaining hours for the scrum task")
    hours: Optional[int] = Field(None, description="Actual Hours for the scrum task")
    description: Optional[str] = Field(None, description="Detailed description of the scrum task")
    type: Optional[str] = Field(None, description="Type of scrum task (1 is Analysis, 2 is Coding, 3 is Documentation, 4 is Testing)")
    state: Optional[str] = Field(None, description="State of scrum task (-6 is Draft,1 is Ready, 2 is Work in progress, 3 is Complete, 4 is Cancelled)")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the scrum task")
    assigned_to: Optional[str] = Field(None, description="User assigned to the scrum task")
    work_notes: Optional[str] = Field(None, description="Work notes to add to the scrum task")
    
class UpdateScrumTaskParams(BaseModel):
    """Parameters for updating a scrum task."""

    scrum_task_id: str = Field(..., description="Scrum Task ID or sys_id")
    short_description: Optional[str] = Field(None, description="Short description of the scrum task")
    priority: Optional[str] = Field(None, description="Priority of scrum task (1 is Critical, 2 is High, 3 is Moderate, 4 is Low)")
    planned_hours: Optional[int] = Field(None, description="Planned hours for the scrum task")
    remaining_hours: Optional[int] = Field(None, description="Remaining hours for the scrum task")
    hours: Optional[int] = Field(None, description="Actual Hours for the scrum task")
    description: Optional[str] = Field(None, description="Detailed description of the scrum task")
    type: Optional[str] = Field(None, description="Type of scrum task (1 is Analysis, 2 is Coding, 3 is Documentation, 4 is Testing)")
    state: Optional[str] = Field(None, description="State of scrum task (-6 is Draft,1 is Ready, 2 is Work in progress, 3 is Complete, 4 is Cancelled)")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the scrum task")
    assigned_to: Optional[str] = Field(None, description="User assigned to the scrum task")
    work_notes: Optional[str] = Field(None, description="Work notes to add to the scrum task")

class ListScrumTasksParams(BaseModel):
    """Parameters for listing scrum tasks."""

    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    state: Optional[str] = Field(None, description="Filter by state")
    assignment_group: Optional[str] = Field(None, description="Filter by assignment group")
    timeframe: Optional[str] = Field(None, description="Filter by timeframe (upcoming, in-progress, completed)")
    query: Optional[str] = Field(None, description="Additional query string")


def _unwrap_and_validate_params(params: Any, model_class: Type[T], required_fields: List[str] = None) -> Dict[str, Any]:
    """
    Helper function to unwrap and validate parameters.
    
    Args:
        params: The parameters to unwrap and validate.
        model_class: The Pydantic model class to validate against.
        required_fields: List of required field names.
        
    Returns:
        A tuple of (success, result) where result is either the validated parameters or an error message.
    """
    # Handle case where params might be wrapped in another dictionary
    if isinstance(params, dict) and len(params) == 1 and "params" in params and isinstance(params["params"], dict):
        logger.warning("Detected params wrapped in a 'params' key. Unwrapping...")
        params = params["params"]
    
    # Handle case where params might be a Pydantic model object
    if not isinstance(params, dict):
        try:
            # Try to convert to dict if it's a Pydantic model
            logger.warning("Params is not a dictionary. Attempting to convert...")
            params = params.dict() if hasattr(params, "dict") else dict(params)
        except Exception as e:
            logger.error(f"Failed to convert params to dictionary: {e}")
            return {
                "success": False,
                "message": f"Invalid parameters format. Expected a dictionary, got {type(params).__name__}",
            }
    
    # Validate required parameters are present
    if required_fields:
        for field in required_fields:
            if field not in params:
                return {
                    "success": False,
                    "message": f"Missing required parameter '{field}'",
                }
    
    try:
        # Validate parameters against the model
        validated_params = model_class(**params)
        return {
            "success": True,
            "params": validated_params,
        }
    except Exception as e:
        logger.error(f"Error validating parameters: {e}")
        return {
            "success": False,
            "message": f"Error validating parameters: {str(e)}",
        }


def _get_instance_url(auth_manager: AuthManager, server_config: ServerConfig) -> Optional[str]:
    """
    Helper function to get the instance URL from either server_config or auth_manager.
    
    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        
    Returns:
        The instance URL if found, None otherwise.
    """
    if hasattr(server_config, 'instance_url'):
        return server_config.instance_url
    elif hasattr(auth_manager, 'instance_url'):
        return auth_manager.instance_url
    else:
        logger.error("Cannot find instance_url in either server_config or auth_manager")
        return None


def _get_headers(auth_manager: Any, server_config: Any) -> Optional[Dict[str, str]]:
    """
    Helper function to get headers from either auth_manager or server_config.
    
    Args:
        auth_manager: The authentication manager or object passed as auth_manager.
        server_config: The server configuration or object passed as server_config.
        
    Returns:
        The headers if found, None otherwise.
    """
    # Try to get headers from auth_manager
    if hasattr(auth_manager, 'get_headers'):
        return auth_manager.get_headers()
    
    # If auth_manager doesn't have get_headers, try server_config
    if hasattr(server_config, 'get_headers'):
        return server_config.get_headers()
    
    # If neither has get_headers, check if auth_manager is actually a ServerConfig
    # and server_config is actually an AuthManager (parameters swapped)
    if hasattr(server_config, 'get_headers') and not hasattr(auth_manager, 'get_headers'):
        return server_config.get_headers()
    
    logger.error("Cannot find get_headers method in either auth_manager or server_config")
    return None

def create_scrum_task(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new scrum task in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for creating the scrum task.

    Returns:
        The created scrum task.
    """

    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        CreateScrumTaskParams, 
        required_fields=["short_description", "story"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "story": validated_params.story,
        "short_description": validated_params.short_description,
    }

    # Add optional fields if provided
    if validated_params.priority:
        data["priority"] = validated_params.priority
    if validated_params.planned_hours:
        data["planned_hours"] = validated_params.planned_hours
    if validated_params.remaining_hours:
        data["remaining_hours"] = validated_params.remaining_hours
    if validated_params.hours:
        data["hours"] = validated_params.hours
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.type:
        data["type"] = validated_params.type
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.assigned_to:
        data["assigned_to"] = validated_params.assigned_to
    if validated_params.work_notes:
        data["work_notes"] = validated_params.work_notes
    
    # Get the instance URL
    instance_url = _get_instance_url(auth_manager, server_config)
    if not instance_url:
        return {
            "success": False,
            "message": "Cannot find instance_url in either server_config or auth_manager",
        }
    
    # Get the headers
    headers = _get_headers(auth_manager, server_config)
    if not headers:
        return {
            "success": False,
            "message": "Cannot find get_headers method in either auth_manager or server_config",
        }
    
    # Add Content-Type header
    headers["Content-Type"] = "application/json"
    
    # Make the API request
    url = f"{instance_url}/api/now/table/rm_scrum_task"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Scrum Task created successfully",
            "scrum_task": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating scrum task: {e}")
        return {
            "success": False,
            "message": f"Error creating scrum task: {str(e)}",
        }

def update_scrum_task(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing scrum task in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for updating the scrum task.

    Returns:
        The updated scrum task.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        UpdateScrumTaskParams,
        required_fields=["scrum_task_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {}

    # Add optional fields if provided
    if validated_params.short_description:
        data["short_description"] = validated_params.short_description
    if validated_params.priority:
        data["priority"] = validated_params.priority
    if validated_params.planned_hours:
        data["planned_hours"] = validated_params.planned_hours
    if validated_params.remaining_hours:
        data["remaining_hours"] = validated_params.remaining_hours
    if validated_params.hours:
        data["hours"] = validated_params.hours
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.type:
        data["type"] = validated_params.type
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.assigned_to:
        data["assigned_to"] = validated_params.assigned_to
    if validated_params.work_notes:
        data["work_notes"] = validated_params.work_notes
    
    # Get the instance URL
    instance_url = _get_instance_url(auth_manager, server_config)
    if not instance_url:
        return {
            "success": False,
            "message": "Cannot find instance_url in either server_config or auth_manager",
        }
    
    # Get the headers
    headers = _get_headers(auth_manager, server_config)
    if not headers:
        return {
            "success": False,
            "message": "Cannot find get_headers method in either auth_manager or server_config",
        }
    
    # Add Content-Type header
    headers["Content-Type"] = "application/json"
    
    # Make the API request
    url = f"{instance_url}/api/now/table/rm_scrum_task/{validated_params.scrum_task_id}"
    
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Scrum Task updated successfully",
            "scrum_task": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating scrum task: {e}")
        return {
            "success": False,
            "message": f"Error updating scrum task: {str(e)}",
        }

def list_scrum_tasks(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    List scrum tasks from ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for listing scrum tasks.

    Returns:
        A list of scrum tasks.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        ListScrumTasksParams
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Build the query
    query_parts = []
    
    if validated_params.state:
        query_parts.append(f"state={validated_params.state}")
    if validated_params.assignment_group:
        query_parts.append(f"assignment_group={validated_params.assignment_group}")
    
    # Handle timeframe filtering
    if validated_params.timeframe:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if validated_params.timeframe == "upcoming":
            query_parts.append(f"start_date>{now}")
        elif validated_params.timeframe == "in-progress":
            query_parts.append(f"start_date<{now}^end_date>{now}")
        elif validated_params.timeframe == "completed":
            query_parts.append(f"end_date<{now}")
    
    # Add any additional query string
    if validated_params.query:
        query_parts.append(validated_params.query)
    
    # Combine query parts
    query = "^".join(query_parts) if query_parts else ""
    
    # Get the instance URL
    instance_url = _get_instance_url(auth_manager, server_config)
    if not instance_url:
        return {
            "success": False,
            "message": "Cannot find instance_url in either server_config or auth_manager",
        }
    
    # Get the headers
    headers = _get_headers(auth_manager, server_config)
    if not headers:
        return {
            "success": False,
            "message": "Cannot find get_headers method in either auth_manager or server_config",
        }
    
    # Make the API request
    url = f"{instance_url}/api/now/table/rm_scrum_task"
    
    params = {
        "sysparm_limit": validated_params.limit,
        "sysparm_offset": validated_params.offset,
        "sysparm_query": query,
        "sysparm_display_value": "true",
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        result = response.json()
        
        # Handle the case where result["result"] is a list
        scrum_tasks = result.get("result", [])
        count = len(scrum_tasks)
        
        return {
            "success": True,
            "scrum_tasks": scrum_tasks,
            "count": count,
            "total": count,  # Use count as total if total is not provided
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing stories: {e}")
        return {
            "success": False,
            "message": f"Error listing stories: {str(e)}",
        }
