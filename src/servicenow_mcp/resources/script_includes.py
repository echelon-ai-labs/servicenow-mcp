"""
Script Include resources for the ServiceNow MCP server.

This module provides resources for accessing script include data from ServiceNow.
"""

import logging
from typing import List, Optional, Dict, Any
import requests
import json

from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ScriptIncludeModel(BaseModel):
    """Model representing a ServiceNow script include."""
    
    sys_id: str = Field(..., description="Unique identifier for the script include")
    name: str = Field(..., description="Name of the script include")
    script: str = Field(..., description="Script content")
    description: Optional[str] = Field(None, description="Description of the script include")
    api_name: Optional[str] = Field(None, description="API name of the script include")
    client_callable: bool = Field(..., description="Whether the script include is client callable")
    active: bool = Field(..., description="Whether the script include is active")
    access: str = Field(..., description="Access level of the script include")
    created_on: str = Field(..., description="Date and time when the script include was created")
    updated_on: str = Field(..., description="Date and time when the script include was last updated")
    created_by: Optional[str] = Field(None, description="User who created the script include")
    updated_by: Optional[str] = Field(None, description="User who last updated the script include")


class ScriptIncludeListParams(BaseModel):
    """Parameters for listing script includes."""
    
    limit: int = Field(10, description="Maximum number of script includes to return")
    offset: int = Field(0, description="Offset for pagination")
    active: Optional[bool] = Field(None, description="Filter by active status")
    client_callable: Optional[bool] = Field(None, description="Filter by client callable status")
    query: Optional[str] = Field(None, description="Search query for script includes")


class ScriptIncludeResource:
    """Resource for accessing ServiceNow script includes."""
    
    def __init__(self, config: ServerConfig, auth_manager: AuthManager):
        """Initialize the script include resource.
        
        Args:
            config: The server configuration.
            auth_manager: The authentication manager.
        """
        self.config = config
        self.auth_manager = auth_manager
        
    async def list_script_includes(self, params: ScriptIncludeListParams) -> str:
        """List script includes from ServiceNow.
        
        Args:
            params: The parameters for the request.
            
        Returns:
            A JSON string containing the list of script includes.
        """
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
            
        # Make the API request
        url = f"{self.config.instance_url}/api/now/table/sys_script_include"
        
        try:
            headers = self.auth_manager.get_headers()
            response = requests.get(url, params=query_params, headers=headers)
            response.raise_for_status()
            
            # Parse the response to extract script includes
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
                
            result = {
                "success": True,
                "message": f"Found {len(script_includes)} script includes",
                "script_includes": script_includes,
                "total": len(script_includes),
                "limit": params.limit,
                "offset": params.offset,
            }
            
            return json.dumps(result)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing script includes: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error listing script includes: {str(e)}",
                "script_includes": [],
                "total": 0,
                "limit": params.limit,
                "offset": params.offset,
            })
            
    async def get_script_include(self, script_include_id: str) -> str:
        """Get a specific script include from ServiceNow.
        
        Args:
            script_include_id: The ID or name of the script include.
            
        Returns:
            A JSON string containing the script include data.
        """
        # Build query parameters
        query_params = {
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
            "sysparm_fields": "sys_id,name,script,description,api_name,client_callable,active,access,sys_created_on,sys_updated_on,sys_created_by,sys_updated_by"
        }
        
        # Determine if we're querying by sys_id or name
        if script_include_id.startswith("sys_id:"):
            sys_id = script_include_id.replace("sys_id:", "")
            url = f"{self.config.instance_url}/api/now/table/sys_script_include/{sys_id}"
        else:
            # Query by name
            url = f"{self.config.instance_url}/api/now/table/sys_script_include"
            query_params["sysparm_query"] = f"name={script_include_id}"
            
        # Make the API request
        try:
            headers = self.auth_manager.get_headers()
            response = requests.get(url, params=query_params, headers=headers)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            if "result" not in data:
                return json.dumps({
                    "success": False,
                    "message": f"Script include not found: {script_include_id}",
                })
                
            # Handle both single result and list of results
            result = data["result"]
            if isinstance(result, list):
                if not result:
                    return json.dumps({
                        "success": False,
                        "message": f"Script include not found: {script_include_id}",
                    })
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
            
            return json.dumps({
                "success": True,
                "message": f"Found script include: {item.get('name')}",
                "script_include": script_include,
            })
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting script include: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error getting script include: {str(e)}",
            }) 