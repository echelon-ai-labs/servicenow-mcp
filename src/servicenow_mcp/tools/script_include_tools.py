"""
Script Include tools for the ServiceNow MCP server.

This module provides tools for managing script includes in ServiceNow.
"""

import logging
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ListScriptIncludesParams(BaseModel):
    """Parameters for listing script includes."""
    
    limit: int = Field(10, description="Maximum number of script includes to return")
    offset: int = Field(0, description="Offset for pagination")
    active: Optional[bool] = Field(None, description="Filter by active status")
    client_callable: Optional[bool] = Field(None, description="Filter by client callable status")
    query: Optional[str] = Field(None, description="Search query for script includes")


class GetScriptIncludeParams(BaseModel):
    """Parameters for getting a script include."""
    
    script_include_id: str = Field(..., description="Script include ID or name")


class CreateScriptIncludeParams(BaseModel):
    """Parameters for creating a script include."""
    
    name: str = Field(..., description="Name of the script include")
    script: str = Field(..., description="Script content")
    description: Optional[str] = Field(None, description="Description of the script include")
    api_name: Optional[str] = Field(None, description="API name of the script include")
    client_callable: bool = Field(False, description="Whether the script include is client callable")
    active: bool = Field(True, description="Whether the script include is active")
    access: str = Field("package_private", description="Access level of the script include")


class UpdateScriptIncludeParams(BaseModel):
    """Parameters for updating a script include."""
    
    script_include_id: str = Field(..., description="Script include ID or name")
    script: Optional[str] = Field(None, description="Script content")
    description: Optional[str] = Field(None, description="Description of the script include")
    api_name: Optional[str] = Field(None, description="API name of the script include")
    client_callable: Optional[bool] = Field(None, description="Whether the script include is client callable")
    active: Optional[bool] = Field(None, description="Whether the script include is active")
    access: Optional[str] = Field(None, description="Access level of the script include")


class DeleteScriptIncludeParams(BaseModel):
    """Parameters for deleting a script include."""
    
    script_include_id: str = Field(..., description="Script include ID or name")


class ScriptIncludeResponse(BaseModel):
    """Response from script include operations."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    script_include_id: Optional[str] = Field(None, description="ID of the affected script include")
    script_include_name: Optional[str] = Field(None, description="Name of the affected script include")


def list_script_includes(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListScriptIncludesParams,
) -> Dict[str, Any]:
    """List script includes from ServiceNow.
    
    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for the request.
        
    Returns:
        A dictionary containing the list of script includes.
    """
    try:
        # Build the URL
        url = f"{config.instance_url}/api/now/table/sys_script_include"
        
        # Build query parameters
        query_params = {
            "sysparm_limit": params.limit,
            "sysparm_offset": params.offset,
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
            "sysparm_fields": "sys_id,name,script,description,api_name,client_callable,active,access,sys_created_on,sys_updated_on,sys_created_by,sys_updated_by"
        }
        
        # Add filters if provided
        query_parts = []
        
        if params.active is not None:
            query_parts.append(f"active={str(params.active).lower()}")
            
        if params.client_callable is not None:
            query_parts.append(f"client_callable={str(params.client_callable).lower()}")
            
        if params.query:
            query_parts.append(f"nameLIKE{params.query}")
            
        if query_parts:
            query_params["sysparm_query"] = "^".join(query_parts)
            
        # Make the request
        headers = auth_manager.get_headers()
        
        response = requests.get(
            url,
            params=query_params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        script_includes = []
        
        for item in data.get("result", []):
            script_include = {
                "sys_id": item.get("sys_id"),
                "name": item.get("name"),
                "description": item.get("description"),
                "api_name": item.get("api_name"),
                "client_callable": item.get("client_callable") == "true",
                "active": item.get("active") == "true",
                "access": item.get("access"),
                "created_on": item.get("sys_created_on"),
                "updated_on": item.get("sys_updated_on"),
                "created_by": item.get("sys_created_by", {}).get("display_value"),
                "updated_by": item.get("sys_updated_by", {}).get("display_value"),
            }
            script_includes.append(script_include)
            
        return {
            "success": True,
            "message": f"Found {len(script_includes)} script includes",
            "script_includes": script_includes,
            "total": len(script_includes),
            "limit": params.limit,
            "offset": params.offset,
        }
        
    except Exception as e:
        logger.error(f"Error listing script includes: {e}")
        return {
            "success": False,
            "message": f"Error listing script includes: {str(e)}",
            "script_includes": [],
            "total": 0,
            "limit": params.limit,
            "offset": params.offset,
        }


def get_script_include(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetScriptIncludeParams,
) -> Dict[str, Any]:
    """Get a specific script include from ServiceNow.
    
    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for the request.
        
    Returns:
        A dictionary containing the script include data.
    """
    try:
        # Build query parameters
        query_params = {
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
            "sysparm_fields": "sys_id,name,script,description,api_name,client_callable,active,access,sys_created_on,sys_updated_on,sys_created_by,sys_updated_by"
        }
        
        # Determine if we're querying by sys_id or name
        if params.script_include_id.startswith("sys_id:"):
            sys_id = params.script_include_id.replace("sys_id:", "")
            url = f"{config.instance_url}/api/now/table/sys_script_include/{sys_id}"
        else:
            # Query by name
            url = f"{config.instance_url}/api/now/table/sys_script_include"
            query_params["sysparm_query"] = f"name={params.script_include_id}"
            
        # Make the request
        headers = auth_manager.get_headers()
        
        response = requests.get(
            url,
            params=query_params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        if "result" not in data:
            return {
                "success": False,
                "message": f"Script include not found: {params.script_include_id}",
            }
            
        # Handle both single result and list of results
        result = data["result"]
        if isinstance(result, list):
            if not result:
                return {
                    "success": False,
                    "message": f"Script include not found: {params.script_include_id}",
                }
            item = result[0]
        else:
            item = result
            
        script_include = {
            "sys_id": item.get("sys_id"),
            "name": item.get("name"),
            "script": item.get("script"),
            "description": item.get("description"),
            "api_name": item.get("api_name"),
            "client_callable": item.get("client_callable") == "true",
            "active": item.get("active") == "true",
            "access": item.get("access"),
            "created_on": item.get("sys_created_on"),
            "updated_on": item.get("sys_updated_on"),
            "created_by": item.get("sys_created_by", {}).get("display_value"),
            "updated_by": item.get("sys_updated_by", {}).get("display_value"),
        }
        
        return {
            "success": True,
            "message": f"Found script include: {item.get('name')}",
            "script_include": script_include,
        }
        
    except Exception as e:
        logger.error(f"Error getting script include: {e}")
        return {
            "success": False,
            "message": f"Error getting script include: {str(e)}",
        }


def create_script_include(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateScriptIncludeParams,
) -> ScriptIncludeResponse:
    """Create a new script include in ServiceNow.
    
    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for the request.
        
    Returns:
        A response indicating the result of the operation.
    """
    # Build the URL
    url = f"{config.instance_url}/api/now/table/sys_script_include"
    
    # Build the request body
    body = {
        "name": params.name,
        "script": params.script,
        "active": str(params.active).lower(),
        "client_callable": str(params.client_callable).lower(),
        "access": params.access,
    }
    
    if params.description:
        body["description"] = params.description
        
    if params.api_name:
        body["api_name"] = params.api_name
        
    # Make the request
    headers = auth_manager.get_headers()
    
    try:
        response = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        if "result" not in data:
            return ScriptIncludeResponse(
                success=False,
                message="Failed to create script include",
            )
            
        result = data["result"]
        
        return ScriptIncludeResponse(
            success=True,
            message=f"Created script include: {result.get('name')}",
            script_include_id=result.get("sys_id"),
            script_include_name=result.get("name"),
        )
        
    except Exception as e:
        logger.error(f"Error creating script include: {e}")
        return ScriptIncludeResponse(
            success=False,
            message=f"Error creating script include: {str(e)}",
        )


def update_script_include(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateScriptIncludeParams,
) -> ScriptIncludeResponse:
    """Update an existing script include in ServiceNow.
    
    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for the request.
        
    Returns:
        A response indicating the result of the operation.
    """
    # First, get the script include to update
    get_params = GetScriptIncludeParams(script_include_id=params.script_include_id)
    get_result = get_script_include(config, auth_manager, get_params)
    
    if not get_result["success"]:
        return ScriptIncludeResponse(
            success=False,
            message=get_result["message"],
        )
        
    script_include = get_result["script_include"]
    sys_id = script_include["sys_id"]
    
    # Build the URL
    url = f"{config.instance_url}/api/now/table/sys_script_include/{sys_id}"
    
    # Build the request body
    body = {}
    
    if params.script is not None:
        body["script"] = params.script
        
    if params.description is not None:
        body["description"] = params.description
        
    if params.api_name is not None:
        body["api_name"] = params.api_name
        
    if params.client_callable is not None:
        body["client_callable"] = str(params.client_callable).lower()
        
    if params.active is not None:
        body["active"] = str(params.active).lower()
        
    if params.access is not None:
        body["access"] = params.access
        
    # If no fields to update, return success
    if not body:
        return ScriptIncludeResponse(
            success=True,
            message=f"No changes to update for script include: {script_include['name']}",
            script_include_id=sys_id,
            script_include_name=script_include["name"],
        )
        
    # Make the request
    headers = auth_manager.get_headers()
    
    try:
        response = requests.patch(
            url,
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        if "result" not in data:
            return ScriptIncludeResponse(
                success=False,
                message=f"Failed to update script include: {script_include['name']}",
            )
            
        result = data["result"]
        
        return ScriptIncludeResponse(
            success=True,
            message=f"Updated script include: {result.get('name')}",
            script_include_id=result.get("sys_id"),
            script_include_name=result.get("name"),
        )
        
    except Exception as e:
        logger.error(f"Error updating script include: {e}")
        return ScriptIncludeResponse(
            success=False,
            message=f"Error updating script include: {str(e)}",
        )


def delete_script_include(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: DeleteScriptIncludeParams,
) -> ScriptIncludeResponse:
    """Delete a script include from ServiceNow.
    
    Args:
        config: The server configuration.
        auth_manager: The authentication manager.
        params: The parameters for the request.
        
    Returns:
        A response indicating the result of the operation.
    """
    # First, get the script include to delete
    get_params = GetScriptIncludeParams(script_include_id=params.script_include_id)
    get_result = get_script_include(config, auth_manager, get_params)
    
    if not get_result["success"]:
        return ScriptIncludeResponse(
            success=False,
            message=get_result["message"],
        )
        
    script_include = get_result["script_include"]
    sys_id = script_include["sys_id"]
    name = script_include["name"]
    
    # Build the URL
    url = f"{config.instance_url}/api/now/table/sys_script_include/{sys_id}"
    
    # Make the request
    headers = auth_manager.get_headers()
    
    try:
        response = requests.delete(
            url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        return ScriptIncludeResponse(
            success=True,
            message=f"Deleted script include: {name}",
            script_include_id=sys_id,
            script_include_name=name,
        )
        
    except Exception as e:
        logger.error(f"Error deleting script include: {e}")
        return ScriptIncludeResponse(
            success=False,
            message=f"Error deleting script include: {str(e)}",
        ) 