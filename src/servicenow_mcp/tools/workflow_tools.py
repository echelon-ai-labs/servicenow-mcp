"""
Workflow management tools for the ServiceNow MCP server.

This module provides tools for viewing and managing workflows in ServiceNow.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


class ListWorkflowsParams(BaseModel):
    """Parameters for listing workflows."""
    
    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    active: Optional[bool] = Field(None, description="Filter by active status")
    name: Optional[str] = Field(None, description="Filter by name (contains)")
    query: Optional[str] = Field(None, description="Additional query string")


class GetWorkflowDetailsParams(BaseModel):
    """Parameters for getting workflow details."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")
    include_versions: Optional[bool] = Field(False, description="Include workflow versions")


class ListWorkflowVersionsParams(BaseModel):
    """Parameters for listing workflow versions."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")
    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")


class GetWorkflowActivitiesParams(BaseModel):
    """Parameters for getting workflow activities."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")
    version: Optional[str] = Field(None, description="Specific version to get activities for")


class CreateWorkflowParams(BaseModel):
    """Parameters for creating a new workflow."""
    
    name: str = Field(..., description="Name of the workflow")
    description: Optional[str] = Field(None, description="Description of the workflow")
    table: Optional[str] = Field(None, description="Table the workflow applies to")
    active: Optional[bool] = Field(True, description="Whether the workflow is active")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes for the workflow")


class UpdateWorkflowParams(BaseModel):
    """Parameters for updating a workflow."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")
    name: Optional[str] = Field(None, description="Name of the workflow")
    description: Optional[str] = Field(None, description="Description of the workflow")
    table: Optional[str] = Field(None, description="Table the workflow applies to")
    active: Optional[bool] = Field(None, description="Whether the workflow is active")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes for the workflow")


class ActivateWorkflowParams(BaseModel):
    """Parameters for activating a workflow."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")


class DeactivateWorkflowParams(BaseModel):
    """Parameters for deactivating a workflow."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")


class AddWorkflowActivityParams(BaseModel):
    """Parameters for adding an activity to a workflow."""
    
    workflow_version_id: str = Field(..., description="Workflow version ID")
    name: str = Field(..., description="Name of the activity")
    description: Optional[str] = Field(None, description="Description of the activity")
    activity_type: str = Field(..., description="Type of activity (e.g., 'approval', 'task', 'notification')")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes for the activity")


class UpdateWorkflowActivityParams(BaseModel):
    """Parameters for updating a workflow activity."""
    
    activity_id: str = Field(..., description="Activity ID or sys_id")
    name: Optional[str] = Field(None, description="Name of the activity")
    description: Optional[str] = Field(None, description="Description of the activity")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes for the activity")


class DeleteWorkflowActivityParams(BaseModel):
    """Parameters for deleting a workflow activity."""
    
    activity_id: str = Field(..., description="Activity ID or sys_id")


class ReorderWorkflowActivitiesParams(BaseModel):
    """Parameters for reordering workflow activities."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")
    activity_ids: List[str] = Field(..., description="List of activity IDs in the desired order")


class DeleteWorkflowParams(BaseModel):
    """Parameters for deleting a workflow."""
    
    workflow_id: str = Field(..., description="Workflow ID or sys_id")


def _unwrap_params(params: Any, param_class: Type[T]) -> Dict[str, Any]:
    """
    Unwrap parameters if they're wrapped in a Pydantic model.
    This helps handle cases where the parameters are passed as a model instead of a dict.
    """
    if isinstance(params, dict):
        return params
    if isinstance(params, param_class):
        return params.dict(exclude_none=True)
    return params


def _get_auth_and_config(
    auth_manager_or_config: Union[AuthManager, ServerConfig],
    server_config_or_auth: Union[ServerConfig, AuthManager],
) -> tuple[AuthManager, ServerConfig]:
    """
    Get the correct auth_manager and server_config objects.
    
    This function handles the case where the parameters might be swapped.
    
    Args:
        auth_manager_or_config: Either an AuthManager or a ServerConfig.
        server_config_or_auth: Either a ServerConfig or an AuthManager.
        
    Returns:
        tuple[AuthManager, ServerConfig]: The correct auth_manager and server_config.
        
    Raises:
        ValueError: If the parameters are not of the expected types.
    """
    # Check if the parameters are in the correct order
    if isinstance(auth_manager_or_config, AuthManager) and isinstance(server_config_or_auth, ServerConfig):
        return auth_manager_or_config, server_config_or_auth
    
    # Check if the parameters are swapped
    if isinstance(auth_manager_or_config, ServerConfig) and isinstance(server_config_or_auth, AuthManager):
        return server_config_or_auth, auth_manager_or_config
    
    # If we get here, at least one of the parameters is not of the expected type
    if hasattr(auth_manager_or_config, "get_headers"):
        auth_manager = auth_manager_or_config
    elif hasattr(server_config_or_auth, "get_headers"):
        auth_manager = server_config_or_auth
    else:
        raise ValueError("Cannot find get_headers method in either auth_manager or server_config")
    
    if hasattr(auth_manager_or_config, "instance_url"):
        server_config = auth_manager_or_config
    elif hasattr(server_config_or_auth, "instance_url"):
        server_config = server_config_or_auth
    else:
        raise ValueError("Cannot find instance_url attribute in either auth_manager or server_config")
    
    return auth_manager, server_config


def list_workflows(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    List workflows from ServiceNow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for listing workflows
        
    Returns:
        Dictionary containing the list of workflows
    """
    params = _unwrap_params(params, ListWorkflowsParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    # Convert parameters to ServiceNow query format
    query_params = {
        "sysparm_limit": params.get("limit", 10),
        "sysparm_offset": params.get("offset", 0),
    }
    
    # Build query string
    query_parts = []
    
    if params.get("active") is not None:
        query_parts.append(f"active={str(params['active']).lower()}")
    
    if params.get("name"):
        query_parts.append(f"nameLIKE{params['name']}")
    
    if params.get("query"):
        query_parts.append(params["query"])
    
    if query_parts:
        query_params["sysparm_query"] = "^".join(query_parts)
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow"
        
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        result = response.json()
        return {
            "workflows": result.get("result", []),
            "count": len(result.get("result", [])),
            "total": int(response.headers.get("X-Total-Count", 0)),
        }
    except requests.RequestException as e:
        logger.error(f"Error listing workflows: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error listing workflows: {e}")
        return {"error": str(e)}


def get_workflow_details(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Get detailed information about a specific workflow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for getting workflow details
        
    Returns:
        Dictionary containing the workflow details
    """
    params = _unwrap_params(params, GetWorkflowDetailsParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        return {
            "workflow": result.get("result", {}),
        }
    except requests.RequestException as e:
        logger.error(f"Error getting workflow details: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error getting workflow details: {e}")
        return {"error": str(e)}


def list_workflow_versions(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    List versions of a specific workflow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for listing workflow versions
        
    Returns:
        Dict[str, Any]: List of workflow versions
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, ListWorkflowVersionsParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    # Convert parameters to ServiceNow query format
    query_params = {
        "sysparm_query": f"workflow={workflow_id}",
        "sysparm_limit": params.get("limit", 10),
        "sysparm_offset": params.get("offset", 0),
    }
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow_version"
        
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        result = response.json()
        return {
            "versions": result.get("result", []),
            "count": len(result.get("result", [])),
            "total": int(response.headers.get("X-Total-Count", 0)),
            "workflow_id": workflow_id,
        }
    except requests.RequestException as e:
        logger.error(f"Error listing workflow versions: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error listing workflow versions: {e}")
        return {"error": str(e)}


def get_workflow_activities(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Get activities for a specific workflow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for getting workflow activities
        
    Returns:
        Dict[str, Any]: List of workflow activities
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, GetWorkflowActivitiesParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    version_id = params.get("version")
    
    # If no version specified, get the latest published version
    if not version_id:
        try:
            headers = auth_manager.get_headers()
            version_url = f"{server_config.instance_url}/api/now/table/wf_workflow_version"
            version_params = {
                "sysparm_query": f"workflow={workflow_id}^published=true",
                "sysparm_limit": 1,
                "sysparm_orderby": "version DESC",
            }
            
            version_response = requests.get(version_url, headers=headers, params=version_params)
            version_response.raise_for_status()
            
            version_result = version_response.json()
            versions = version_result.get("result", [])
            
            if not versions:
                return {
                    "error": f"No published versions found for workflow {workflow_id}",
                    "workflow_id": workflow_id,
                }
            
            version_id = versions[0]["sys_id"]
        except requests.RequestException as e:
            logger.error(f"Error getting workflow version: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting workflow version: {e}")
            return {"error": str(e)}
    
    # Get activities for the version
    try:
        headers = auth_manager.get_headers()
        activities_url = f"{server_config.instance_url}/api/now/table/wf_activity"
        activities_params = {
            "sysparm_query": f"workflow_version={version_id}",
            "sysparm_orderby": "order",
        }
        
        activities_response = requests.get(activities_url, headers=headers, params=activities_params)
        activities_response.raise_for_status()
        
        activities_result = activities_response.json()
        return {
            "activities": activities_result.get("result", []),
            "count": len(activities_result.get("result", [])),
            "workflow_id": workflow_id,
            "version_id": version_id,
        }
    except requests.RequestException as e:
        logger.error(f"Error getting workflow activities: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error getting workflow activities: {e}")
        return {"error": str(e)}


def create_workflow(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new workflow in ServiceNow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for creating a workflow
        
    Returns:
        Dict[str, Any]: Created workflow details
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, CreateWorkflowParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    # Validate required parameters
    if not params.get("name"):
        return {"error": "Workflow name is required"}
    
    # Prepare data for the API request
    data = {
        "name": params["name"],
    }
    
    if params.get("description"):
        data["description"] = params["description"]
    
    if params.get("table"):
        data["table"] = params["table"]
    
    if params.get("active") is not None:
        data["active"] = str(params["active"]).lower()
    
    if params.get("attributes"):
        # Add any additional attributes
        data.update(params["attributes"])
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow"
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "workflow": result.get("result", {}),
            "message": "Workflow created successfully",
        }
    except requests.RequestException as e:
        logger.error(f"Error creating workflow: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error creating workflow: {e}")
        return {"error": str(e)}


def update_workflow(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing workflow in ServiceNow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for updating a workflow
        
    Returns:
        Dict[str, Any]: Updated workflow details
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, UpdateWorkflowParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    # Prepare data for the API request
    data = {}
    
    if params.get("name"):
        data["name"] = params["name"]
    
    if params.get("description") is not None:
        data["description"] = params["description"]
    
    if params.get("table"):
        data["table"] = params["table"]
    
    if params.get("active") is not None:
        data["active"] = str(params["active"]).lower()
    
    if params.get("attributes"):
        # Add any additional attributes
        data.update(params["attributes"])
    
    if not data:
        return {"error": "No update parameters provided"}
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}"
        
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "workflow": result.get("result", {}),
            "message": "Workflow updated successfully",
        }
    except requests.RequestException as e:
        logger.error(f"Error updating workflow: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error updating workflow: {e}")
        return {"error": str(e)}


def activate_workflow(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Activate a workflow in ServiceNow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for activating a workflow
        
    Returns:
        Dict[str, Any]: Activated workflow details
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, ActivateWorkflowParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    # Prepare data for the API request
    data = {
        "active": "true",
    }
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}"
        
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "workflow": result.get("result", {}),
            "message": "Workflow activated successfully",
        }
    except requests.RequestException as e:
        logger.error(f"Error activating workflow: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error activating workflow: {e}")
        return {"error": str(e)}


def deactivate_workflow(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deactivate a workflow in ServiceNow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for deactivating a workflow
        
    Returns:
        Dict[str, Any]: Deactivated workflow details
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, DeactivateWorkflowParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    # Prepare data for the API request
    data = {
        "active": "false",
    }
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}"
        
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "workflow": result.get("result", {}),
            "message": "Workflow deactivated successfully",
        }
    except requests.RequestException as e:
        logger.error(f"Error deactivating workflow: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error deactivating workflow: {e}")
        return {"error": str(e)}


def add_workflow_activity(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Add a new activity to a workflow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for adding a workflow activity
        
    Returns:
        Dict[str, Any]: Added workflow activity details
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, AddWorkflowActivityParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    # Validate required parameters
    workflow_version_id = params.get("workflow_version_id")
    if not workflow_version_id:
        return {"error": "Workflow version ID is required"}
    
    activity_name = params.get("name")
    if not activity_name:
        return {"error": "Activity name is required"}
    
    # Prepare data for the API request
    data = {
        "workflow_version": workflow_version_id,
        "name": activity_name,
    }
    
    if params.get("description"):
        data["description"] = params["description"]
    
    if params.get("activity_type"):
        data["activity_type"] = params["activity_type"]
    
    if params.get("attributes"):
        # Add any additional attributes
        data.update(params["attributes"])
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_activity"
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "activity": result.get("result", {}),
            "message": "Workflow activity added successfully",
        }
    except requests.RequestException as e:
        logger.error(f"Error adding workflow activity: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error adding workflow activity: {e}")
        return {"error": str(e)}


def update_workflow_activity(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing activity in a workflow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for updating a workflow activity
        
    Returns:
        Dict[str, Any]: Updated workflow activity details
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, UpdateWorkflowActivityParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    activity_id = params.get("activity_id")
    if not activity_id:
        return {"error": "Activity ID is required"}
    
    # Prepare data for the API request
    data = {}
    
    if params.get("name"):
        data["name"] = params["name"]
    
    if params.get("description") is not None:
        data["description"] = params["description"]
    
    if params.get("attributes"):
        # Add any additional attributes
        data.update(params["attributes"])
    
    if not data:
        return {"error": "No update parameters provided"}
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_activity/{activity_id}"
        
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "activity": result.get("result", {}),
            "message": "Activity updated successfully",
        }
    except requests.RequestException as e:
        logger.error(f"Error updating workflow activity: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error updating workflow activity: {e}")
        return {"error": str(e)}


def delete_workflow_activity(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Delete an activity from a workflow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for deleting a workflow activity
        
    Returns:
        Dict[str, Any]: Result of the deletion operation
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, DeleteWorkflowActivityParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    activity_id = params.get("activity_id")
    if not activity_id:
        return {"error": "Activity ID is required"}
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_activity/{activity_id}"
        
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        return {
            "message": "Activity deleted successfully",
            "activity_id": activity_id,
        }
    except requests.RequestException as e:
        logger.error(f"Error deleting workflow activity: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error deleting workflow activity: {e}")
        return {"error": str(e)}


def reorder_workflow_activities(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Reorder activities in a workflow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for reordering workflow activities
        
    Returns:
        Dict[str, Any]: Result of the reordering operation
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, ReorderWorkflowActivitiesParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    activity_ids = params.get("activity_ids")
    if not activity_ids:
        return {"error": "Activity IDs are required"}
    
    # Make the API requests to update the order of each activity
    try:
        headers = auth_manager.get_headers()
        results = []
        
        for i, activity_id in enumerate(activity_ids):
            # Calculate the new order value (100, 200, 300, etc.)
            new_order = (i + 1) * 100
            
            url = f"{server_config.instance_url}/api/now/table/wf_activity/{activity_id}"
            data = {"order": new_order}
            
            try:
                response = requests.patch(url, headers=headers, json=data)
                response.raise_for_status()
                
                results.append({
                    "activity_id": activity_id,
                    "new_order": new_order,
                    "success": True,
                })
            except requests.RequestException as e:
                logger.error(f"Error updating activity order: {e}")
                results.append({
                    "activity_id": activity_id,
                    "error": str(e),
                    "success": False,
                })
        
        return {
            "message": "Activities reordered",
            "workflow_id": workflow_id,
            "results": results,
        }
    except Exception as e:
        logger.error(f"Unexpected error reordering workflow activities: {e}")
        return {"error": str(e)}


def delete_workflow(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Delete a workflow from ServiceNow.
    
    Args:
        auth_manager: Authentication manager
        server_config: Server configuration
        params: Parameters for deleting a workflow
        
    Returns:
        Dict[str, Any]: Result of the deletion operation
    """
    # Unwrap parameters if needed
    params = _unwrap_params(params, DeleteWorkflowParams)
    
    # Get the correct auth_manager and server_config
    try:
        auth_manager, server_config = _get_auth_and_config(auth_manager, server_config)
    except ValueError as e:
        logger.error(f"Error getting auth and config: {e}")
        return {"error": str(e)}
    
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        return {"error": "Workflow ID is required"}
    
    # Make the API request
    try:
        headers = auth_manager.get_headers()
        url = f"{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}"
        
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        return {
            "message": f"Workflow {workflow_id} deleted successfully",
            "workflow_id": workflow_id,
        }
    except requests.RequestException as e:
        logger.error(f"Error deleting workflow: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error deleting workflow: {e}")
        return {"error": str(e)} 