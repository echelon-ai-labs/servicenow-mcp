"""
Changeset tools for the ServiceNow MCP server.

This module provides tools for managing changesets in ServiceNow.
"""

import logging
from typing import Any, Dict, Optional, Union

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


class ListChangesetsParams(BaseModel):
    """Parameters for listing changesets."""

    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    state: Optional[str] = Field(None, description="Filter by state")
    application: Optional[str] = Field(None, description="Filter by application")
    developer: Optional[str] = Field(None, description="Filter by developer")
    timeframe: Optional[str] = Field(None, description="Filter by timeframe (recent, last_week, last_month)")
    query: Optional[str] = Field(None, description="Additional query string")


class GetChangesetDetailsParams(BaseModel):
    """Parameters for getting changeset details."""

    changeset_id: str = Field(..., description="Changeset ID or sys_id")


class CreateChangesetParams(BaseModel):
    """Parameters for creating a changeset."""

    name: str = Field(..., description="Name of the changeset")
    description: Optional[str] = Field(None, description="Description of the changeset")
    application: str = Field(..., description="Application the changeset belongs to")
    developer: Optional[str] = Field(None, description="Developer responsible for the changeset")


class UpdateChangesetParams(BaseModel):
    """Parameters for updating a changeset."""

    changeset_id: str = Field(..., description="Changeset ID or sys_id")
    name: Optional[str] = Field(None, description="Name of the changeset")
    description: Optional[str] = Field(None, description="Description of the changeset")
    state: Optional[str] = Field(None, description="State of the changeset")
    developer: Optional[str] = Field(None, description="Developer responsible for the changeset")


class CommitChangesetParams(BaseModel):
    """Parameters for committing a changeset."""

    changeset_id: str = Field(..., description="Changeset ID or sys_id")
    commit_message: Optional[str] = Field(None, description="Commit message")


class PublishChangesetParams(BaseModel):
    """Parameters for publishing a changeset."""

    changeset_id: str = Field(..., description="Changeset ID or sys_id")
    publish_notes: Optional[str] = Field(None, description="Notes for publishing")


class AddFileToChangesetParams(BaseModel):
    """Parameters for adding a file to a changeset."""

    changeset_id: str = Field(..., description="Changeset ID or sys_id")
    file_path: str = Field(..., description="Path of the file to add")
    file_content: str = Field(..., description="Content of the file")


def list_changesets(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Union[Dict[str, Any], ListChangesetsParams],
) -> Dict[str, Any]:
    """
    List changesets from ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for listing changesets. Can be a dictionary or a ListChangesetsParams object.

    Returns:
        A list of changesets.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(params, ListChangesetsParams)
    
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
    
    # Build query parameters
    query_params = {
        "sysparm_limit": validated_params.limit,
        "sysparm_offset": validated_params.offset,
    }
    
    # Build sysparm_query
    query_parts = []
    
    if validated_params.state:
        query_parts.append(f"state={validated_params.state}")
    
    if validated_params.application:
        query_parts.append(f"application={validated_params.application}")
    
    if validated_params.developer:
        query_parts.append(f"developer={validated_params.developer}")
    
    if validated_params.timeframe:
        if validated_params.timeframe == "recent":
            query_parts.append("sys_created_onONLast 7 days@javascript:gs.beginningOfLast7Days()@javascript:gs.endOfToday()")
        elif validated_params.timeframe == "last_week":
            query_parts.append("sys_created_onONLast week@javascript:gs.beginningOfLastWeek()@javascript:gs.endOfLastWeek()")
        elif validated_params.timeframe == "last_month":
            query_parts.append("sys_created_onONLast month@javascript:gs.beginningOfLastMonth()@javascript:gs.endOfLastMonth()")
    
    if validated_params.query:
        query_parts.append(validated_params.query)
    
    if query_parts:
        query_params["sysparm_query"] = "^".join(query_parts)
    
    # Make the API request
    url = f"{instance_url}/api/now/table/sys_update_set"
    
    try:
        response = requests.get(url, params=query_params, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "changesets": result.get("result", []),
            "count": len(result.get("result", [])),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing changesets: {e}")
        return {
            "success": False,
            "message": f"Error listing changesets: {str(e)}",
        }


def get_changeset_details(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Union[Dict[str, Any], GetChangesetDetailsParams],
) -> Dict[str, Any]:
    """
    Get detailed information about a specific changeset.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for getting changeset details. Can be a dictionary or a GetChangesetDetailsParams object.

    Returns:
        Detailed information about the changeset.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        GetChangesetDetailsParams, 
        required_fields=["changeset_id"]
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
    url = f"{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        # Get the changeset details
        changeset = result.get("result", {})
        
        # Get the changes in this changeset
        changes_url = f"{instance_url}/api/now/table/sys_update_xml"
        changes_params = {
            "sysparm_query": f"update_set={validated_params.changeset_id}",
        }
        
        changes_response = requests.get(changes_url, params=changes_params, headers=headers)
        changes_response.raise_for_status()
        
        changes_result = changes_response.json()
        changes = changes_result.get("result", [])
        
        return {
            "success": True,
            "changeset": changeset,
            "changes": changes,
            "change_count": len(changes),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting changeset details: {e}")
        return {
            "success": False,
            "message": f"Error getting changeset details: {str(e)}",
        }


def create_changeset(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Union[Dict[str, Any], CreateChangesetParams],
) -> Dict[str, Any]:
    """
    Create a new changeset in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for creating a changeset. Can be a dictionary or a CreateChangesetParams object.

    Returns:
        The created changeset.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        CreateChangesetParams, 
        required_fields=["name", "application"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "name": validated_params.name,
        "application": validated_params.application,
    }
    
    # Add optional fields if provided
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.developer:
        data["developer"] = validated_params.developer
    
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
    url = f"{instance_url}/api/now/table/sys_update_set"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Changeset created successfully",
            "changeset": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating changeset: {e}")
        return {
            "success": False,
            "message": f"Error creating changeset: {str(e)}",
        }


def update_changeset(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Union[Dict[str, Any], UpdateChangesetParams],
) -> Dict[str, Any]:
    """
    Update an existing changeset in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for updating a changeset. Can be a dictionary or a UpdateChangesetParams object.

    Returns:
        The updated changeset.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        UpdateChangesetParams, 
        required_fields=["changeset_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {}
    
    # Add optional fields if provided
    if validated_params.name:
        data["name"] = validated_params.name
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.developer:
        data["developer"] = validated_params.developer
    
    # If no fields to update, return error
    if not data:
        return {
            "success": False,
            "message": "No fields to update",
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
    url = f"{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}"
    
    try:
        response = requests.patch(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Changeset updated successfully",
            "changeset": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating changeset: {e}")
        return {
            "success": False,
            "message": f"Error updating changeset: {str(e)}",
        }


def commit_changeset(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Union[Dict[str, Any], CommitChangesetParams],
) -> Dict[str, Any]:
    """
    Commit a changeset in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for committing a changeset. Can be a dictionary or a CommitChangesetParams object.

    Returns:
        The committed changeset.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        CommitChangesetParams, 
        required_fields=["changeset_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "state": "complete",
    }
    
    # Add commit message if provided
    if validated_params.commit_message:
        data["description"] = validated_params.commit_message
    
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
    url = f"{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}"
    
    try:
        response = requests.patch(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Changeset committed successfully",
            "changeset": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error committing changeset: {e}")
        return {
            "success": False,
            "message": f"Error committing changeset: {str(e)}",
        }


def publish_changeset(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Union[Dict[str, Any], PublishChangesetParams],
) -> Dict[str, Any]:
    """
    Publish a changeset in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for publishing a changeset. Can be a dictionary or a PublishChangesetParams object.

    Returns:
        The published changeset.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        PublishChangesetParams, 
        required_fields=["changeset_id"]
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
    
    # Add Content-Type header
    headers["Content-Type"] = "application/json"
    
    # Prepare the request data for the publish action
    data = {
        "state": "published",
    }
    
    # Add publish notes if provided
    if validated_params.publish_notes:
        data["description"] = validated_params.publish_notes
    
    # Make the API request
    url = f"{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}"
    
    try:
        response = requests.patch(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Changeset published successfully",
            "changeset": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error publishing changeset: {e}")
        return {
            "success": False,
            "message": f"Error publishing changeset: {str(e)}",
        }


def add_file_to_changeset(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Union[Dict[str, Any], AddFileToChangesetParams],
) -> Dict[str, Any]:
    """
    Add a file to a changeset in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for adding a file to a changeset. Can be a dictionary or a AddFileToChangesetParams object.

    Returns:
        The result of the add file operation.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        AddFileToChangesetParams, 
        required_fields=["changeset_id", "file_path", "file_content"]
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
    
    # Add Content-Type header
    headers["Content-Type"] = "application/json"
    
    # Prepare the request data for adding a file
    data = {
        "update_set": validated_params.changeset_id,
        "name": validated_params.file_path,
        "payload": validated_params.file_content,
        "type": "file",
    }
    
    # Make the API request
    url = f"{instance_url}/api/now/table/sys_update_xml"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "File added to changeset successfully",
            "file": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding file to changeset: {e}")
        return {
            "success": False,
            "message": f"Error adding file to changeset: {str(e)}",
        } 