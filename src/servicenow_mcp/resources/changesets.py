"""
Changeset resources for the ServiceNow MCP server.

This module provides resources for accessing changesets in ServiceNow.
"""

import logging
from typing import Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from mcp.server.fastmcp.resources import Resource
from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ChangesetListParams(BaseModel):
    """Parameters for listing changesets."""

    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    state: Optional[str] = Field(None, description="Filter by state")
    application: Optional[str] = Field(None, description="Filter by application")
    developer: Optional[str] = Field(None, description="Filter by developer")


class ChangesetResource:
    """Resource for accessing changesets in ServiceNow."""

    def __init__(self, config: ServerConfig, auth_manager: AuthManager):
        """
        Initialize the changeset resource.

        Args:
            config: The server configuration.
            auth_manager: The authentication manager.
        """
        self.config = config
        self.auth_manager = auth_manager

    async def list_changesets(self, params: ChangesetListParams) -> str:
        """
        List changesets from ServiceNow.

        Args:
            params: The parameters for listing changesets.

        Returns:
            A JSON string containing the list of changesets.
        """
        # Build query parameters
        query_params = {
            "sysparm_limit": params.limit,
            "sysparm_offset": params.offset,
        }
        
        # Build sysparm_query
        query_parts = []
        
        if params.state:
            query_parts.append(f"state={params.state}")
        
        if params.application:
            query_parts.append(f"application={params.application}")
        
        if params.developer:
            query_parts.append(f"developer={params.developer}")
        
        if query_parts:
            query_params["sysparm_query"] = "^".join(query_parts)
        
        # Make the API request
        url = f"{self.config.instance_url}/api/now/table/sys_update_set"
        
        try:
            headers = self.auth_manager.get_headers()
            response = requests.get(url, params=query_params, headers=headers)
            response.raise_for_status()
            
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing changesets: {e}")
            return f'{{"error": "Error listing changesets: {str(e)}"}}'

    async def get_changeset(self, changeset_id: str) -> str:
        """
        Get a specific changeset from ServiceNow.

        Args:
            changeset_id: The ID of the changeset to get.

        Returns:
            A JSON string containing the changeset details.
        """
        # Make the API request
        url = f"{self.config.instance_url}/api/now/table/sys_update_set/{changeset_id}"
        
        try:
            headers = self.auth_manager.get_headers()
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Get the changeset details
            changeset_result = response.json()
            
            # Get the changes in this changeset
            changes_url = f"{self.config.instance_url}/api/now/table/sys_update_xml"
            changes_params = {
                "sysparm_query": f"update_set={changeset_id}",
            }
            
            changes_response = requests.get(changes_url, params=changes_params, headers=headers)
            changes_response.raise_for_status()
            
            changes_result = changes_response.json()
            
            # Combine the results
            result = {
                "changeset": changeset_result.get("result", {}),
                "changes": changes_result.get("result", []),
                "change_count": len(changes_result.get("result", [])),
            }
            
            import json
            return json.dumps(result)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting changeset: {e}")
            return f'{{"error": "Error getting changeset: {str(e)}"}}' 