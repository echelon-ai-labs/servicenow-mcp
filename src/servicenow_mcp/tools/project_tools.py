"""
Project management tools for the ServiceNow MCP server.

This module provides tools for managing projects in ServiceNow.
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

class CreateProjectParams(BaseModel):
    """Parameters for creating a project."""

    short_description: str = Field(..., description="Project name of the project")
    description: Optional[str] = Field(None, description="Detailed description of the project")
    status: Optional[str] = Field(None, description="Status of the project (green, yellow, red)")
    state: Optional[str] = Field(None, description="State of project (-5 is Pending,1 is Open, 2 is Work in progress, 3 is Closed Complete, 4 is Closed Incomplete, 5 is Closed Skipped)")
    project_manager: Optional[str] = Field(None, description="Project manager for the project")
    percentage_complete: Optional[int] = Field(None, description="Percentage complete for the project")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the project")
    assigned_to: Optional[str] = Field(None, description="User assigned to the project")
    start_date: Optional[str] = Field(None, description="Start date for the project")
    end_date: Optional[str] = Field(None, description="End date for the project")
    
class UpdateProjectParams(BaseModel):
    """Parameters for updating a project."""

    project_id: str = Field(..., description="Project ID or sys_id")
    short_description: Optional[str] = Field(None, description="Project name of the project")
    description: Optional[str] = Field(None, description="Detailed description of the project")
    status: Optional[str] = Field(None, description="Status of the project (green, yellow, red)")
    state: Optional[str] = Field(None, description="State of project (-5 is Pending,1 is Open, 2 is Work in progress, 3 is Closed Complete, 4 is Closed Incomplete, 5 is Closed Skipped)")
    project_manager: Optional[str] = Field(None, description="Project manager for the project")
    percentage_complete: Optional[int] = Field(None, description="Percentage complete for the project")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the project")
    assigned_to: Optional[str] = Field(None, description="User assigned to the project")
    start_date: Optional[str] = Field(None, description="Start date for the project")
    end_date: Optional[str] = Field(None, description="End date for the project")

class ListProjectsParams(BaseModel):
    """Parameters for listing projects."""

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

def create_project(
    config: ServerConfig,  # Changed from auth_manager
    auth_manager: AuthManager,  # Changed from server_config
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new project in ServiceNow.

    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for creating the project.

    Returns:
        The created project.
    """

    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        CreateProjectParams, 
        required_fields=["short_description"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "short_description": validated_params.short_description,
    }

    # Add optional fields if provided
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.status:
        data["status"] = validated_params.status
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.percentage_complete:
        data["percentage_complete"] = validated_params.percentage_complete
    if validated_params.assigned_to:
        data["assigned_to"] = validated_params.assigned_to
    if validated_params.project_manager:
        data["project_manager"] = validated_params.project_manager
    if validated_params.start_date:
        data["start_date"] = validated_params.start_date
    if validated_params.end_date:
        data["end_date"] = validated_params.end_date
    
    # Get the instance URL
    instance_url = _get_instance_url(auth_manager, config)
    if not instance_url:
        return {
            "success": False,
            "message": "Cannot find instance_url in either server_config or auth_manager",
        }
    
    # Get the headers
    headers = _get_headers(auth_manager, config)
    if not headers:
        return {
            "success": False,
            "message": "Cannot find get_headers method in either auth_manager or server_config",
        }
    
    # Add Content-Type header
    headers["Content-Type"] = "application/json"
    
    # Make the API request
    url = f"{instance_url}/api/now/table/pm_project"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Project created successfully",
            "project": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating project: {e}")
        return {
            "success": False,
            "message": f"Error creating project: {str(e)}",
        }

def update_project(
    config: ServerConfig,  # Changed from auth_manager
    auth_manager: AuthManager,  # Changed from server_config
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing project in ServiceNow.

    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for updating the project.

    Returns:
        The updated project.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        UpdateProjectParams,
        required_fields=["project_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {}

    # Add optional fields if provided
    if validated_params.short_description:
        data["short_description"] = validated_params.short_description
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.status:
        data["status"] = validated_params.status
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.percentage_complete:
        data["percentage_complete"] = validated_params.percentage_complete
    if validated_params.assigned_to:
        data["assigned_to"] = validated_params.assigned_to
    if validated_params.project_manager:
        data["project_manager"] = validated_params.project_manager
    if validated_params.start_date:
        data["start_date"] = validated_params.start_date
    if validated_params.end_date:
        data["end_date"] = validated_params.end_date

    # Get the instance URL
    instance_url = _get_instance_url(auth_manager, config)
    if not instance_url:
        return {
            "success": False,
            "message": "Cannot find instance_url in either server_config or auth_manager",
        }
    
    # Get the headers
    headers = _get_headers(auth_manager, config)
    if not headers:
        return {
            "success": False,
            "message": "Cannot find get_headers method in either auth_manager or server_config",
        }
    
    # Add Content-Type header
    headers["Content-Type"] = "application/json"
    
    # Make the API request
    url = f"{instance_url}/api/now/table/pm_project/{validated_params.project_id}"
    
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Project updated successfully",
            "project": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating project: {e}")
        return {
            "success": False,
            "message": f"Error updating project: {str(e)}",
        }

def list_projects(
    config: ServerConfig,  # Changed from auth_manager
    auth_manager: AuthManager,  # Changed from server_config
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    List projects from ServiceNow.

    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for listing projects.

    Returns:
        A list of projects.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        ListProjectsParams
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
    instance_url = _get_instance_url(auth_manager, config)
    if not instance_url:
        return {
            "success": False,
            "message": "Cannot find instance_url in either server_config or auth_manager",
        }
    
    # Get the headers
    headers = _get_headers(auth_manager, config)
    if not headers:
        return {
            "success": False,
            "message": "Cannot find get_headers method in either auth_manager or server_config",
        }
    
    # Make the API request
    url = f"{instance_url}/api/now/table/pm_project"
    
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
        projects = result.get("result", [])
        count = len(projects)
        
        return {
            "success": True,
            "projects": projects,
            "count": count,
            "total": count,  # Use count as total if total is not provided
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing projects: {e}")
        return {
            "success": False,
            "message": f"Error listing projects: {str(e)}",
        }
