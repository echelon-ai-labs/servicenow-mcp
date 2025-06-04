"""
Story management tools for the ServiceNow MCP server.

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

class CreateStoryParams(BaseModel):
    """Parameters for creating a story."""

    short_description: str = Field(..., description="Short description of the story")
    acceptance_criteria: str = Field(..., description="Acceptance criteria for the story")
    description: Optional[str] = Field(None, description="Detailed description of the story")
    state: Optional[str] = Field(None, description="State of story (-6 is Draft,-7 is Ready for Testing,-8 is Testing,1 is Ready, 2 is Work in progress, 3 is Complete, 4 is Cancelled)")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the story")
    story_points: Optional[int] = Field(10, description="Points value for the story")
    assigned_to: Optional[str] = Field(None, description="User assigned to the story")
    epic: Optional[str] = Field(None, description="Epic that the story belongs to. It requires the System ID of the epic.")
    project: Optional[str] = Field(None, description="Project that the story belongs to. It requires the System ID of the project.")
    work_notes: Optional[str] = Field(None, description="Work notes to add to the story. Used for adding notes and comments to a story")
    
class UpdateStoryParams(BaseModel):
    """Parameters for updating a story."""

    story_id: str = Field(..., description="Story IDNumber or sys_id. You will need to fetch the story to get the sys_id if you only have the story number")
    short_description: Optional[str] = Field(None, description="Short description of the story")
    acceptance_criteria: Optional[str] = Field(None, description="Acceptance criteria for the story")
    description: Optional[str] = Field(None, description="Detailed description of the story")
    state: Optional[str] = Field(None, description="State of story (-6 is Draft,-7 is Ready for Testing,-8 is Testing,1 is Ready, 2 is Work in progress, 3 is Complete, 4 is Cancelled)")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the story")
    story_points: Optional[int] = Field(None, description="Points value for the story")
    assigned_to: Optional[str] = Field(None, description="User assigned to the story")
    epic: Optional[str] = Field(None, description="Epic that the story belongs to. It requires the System ID of the epic.")
    project: Optional[str] = Field(None, description="Project that the story belongs to. It requires the System ID of the project.")
    work_notes: Optional[str] = Field(None, description="Work notes to add to the story. Used for adding notes and comments to a story")

class ListStoriesParams(BaseModel):
    """Parameters for listing stories."""

    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    state: Optional[str] = Field(None, description="Filter by state")
    assignment_group: Optional[str] = Field(None, description="Filter by assignment group")
    timeframe: Optional[str] = Field(None, description="Filter by timeframe (upcoming, in-progress, completed)")
    query: Optional[str] = Field(None, description="Additional query string")

class ListStoryDependenciesParams(BaseModel):
    """Parameters for listing story dependencies."""

    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    query: Optional[str] = Field(None, description="Additional query string")
    dependent_story: Optional[str] = Field(None, description="Sys_id of the dependent story is required")
    prerequisite_story: Optional[str] = Field(None, description="Sys_id that this story depends on is required")

class CreateStoryDependencyParams(BaseModel):
    """Parameters for creating a story dependency."""

    dependent_story: str = Field(..., description="Sys_id of the dependent story is required")
    prerequisite_story: str = Field(..., description="Sys_id that this story depends on is required")

class DeleteStoryDependencyParams(BaseModel):
    """Parameters for deleting a story dependency."""

    dependency_id: str = Field(..., description="Sys_id of the dependency is required")

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

def create_story(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new story in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for creating the story.

    Returns:
        The created story.
    """

    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        CreateStoryParams, 
        required_fields=["short_description", "acceptance_criteria"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "short_description": validated_params.short_description,
        "acceptance_criteria": validated_params.acceptance_criteria,
    }
       
    # Add optional fields if provided
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.story_points:
        data["story_points"] = validated_params.story_points
    if validated_params.assigned_to:
        data["assigned_to"] = validated_params.assigned_to
    if validated_params.epic:
        data["epic"] = validated_params.epic
    if validated_params.project:
        data["project"] = validated_params.project
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
    url = f"{instance_url}/api/now/table/rm_story"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Story created successfully",
            "story": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating story: {e}")
        return {
            "success": False,
            "message": f"Error creating story: {str(e)}",
        }

def update_story(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing story in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for updating the story.

    Returns:
        The updated story.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        UpdateStoryParams,
        required_fields=["story_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {}
    
    # Add optional fields if provided
    if validated_params.short_description:
        data["short_description"] = validated_params.short_description
    if validated_params.acceptance_criteria:
        data["acceptance_criteria"] = validated_params.acceptance_criteria
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.story_points:
        data["story_points"] = validated_params.story_points
    if validated_params.epic:
        data["epic"] = validated_params.epic
    if validated_params.project:
        data["project"] = validated_params.project
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
    url = f"{instance_url}/api/now/table/rm_story/{validated_params.story_id}"
    
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Story updated successfully",
            "story": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating story: {e}")
        return {
            "success": False,
            "message": f"Error updating story: {str(e)}",
        }

def list_stories(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    List stories from ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for listing stories.

    Returns:
        A list of stories.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        ListStoriesParams
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
    url = f"{instance_url}/api/now/table/rm_story"
    
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
        stories = result.get("result", [])
        count = len(stories)
        
        return {
            "success": True,
            "stories": stories,
            "count": count,
            "total": count,  # Use count as total if total is not provided
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing stories: {e}")
        return {
            "success": False,
            "message": f"Error listing stories: {str(e)}",
        }

def list_story_dependencies(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    List story dependencies from ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for listing story dependencies.

    Returns:
        A list of story dependencies.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        ListStoryDependenciesParams
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Build the query
    query_parts = []
    
    if validated_params.dependent_story:
        query_parts.append(f"dependent_story={validated_params.dependent_story}")
    if validated_params.prerequisite_story:
        query_parts.append(f"prerequisite_story={validated_params.prerequisite_story}")
    
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
    url = f"{instance_url}/api/now/table/m2m_story_dependencies"
    
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
        story_dependencies = result.get("result", [])
        count = len(story_dependencies)
        
        return {
            "success": True,
            "story_dependencies": story_dependencies,
            "count": count,
            "total": count,  # Use count as total if total is not provided
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing story dependencies: {e}")
        return {
            "success": False,
            "message": f"Error listing story dependencies: {str(e)}",
        }

def create_story_dependency(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a dependency between two stories in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for creating a story dependency.

    Returns:
        The created story dependency.
    """
    # Unwrap and validate parameters    
    result = _unwrap_and_validate_params(
        params, 
        CreateStoryDependencyParams,
        required_fields=["dependent_story", "prerequisite_story"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "dependent_story": validated_params.dependent_story,
        "prerequisite_story": validated_params.prerequisite_story,
    }
    
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
    url = f"{instance_url}/api/now/table/m2m_story_dependencies"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()    
        return {
            "success": True,
            "message": "Story dependency created successfully",
            "story_dependency": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating story dependency: {e}")
        return {
            "success": False,
            "message": f"Error creating story dependency: {str(e)}",
        }
def delete_story_dependency(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Delete a story dependency in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for deleting a story dependency.

    Returns:
        The deleted story dependency.
    """
    # Unwrap and validate parameters    
    result = _unwrap_and_validate_params(
        params, 
        DeleteStoryDependencyParams,
        required_fields=["dependency_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
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
    url = f"{instance_url}/api/now/table/m2m_story_dependencies/{validated_params.dependency_id}"
    
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        return {
            "success": True,
            "message": "Story dependency deleted successfully",
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting story dependency: {e}")
        return {
            "success": False,
            "message": f"Error deleting story dependency: {str(e)}",
        }