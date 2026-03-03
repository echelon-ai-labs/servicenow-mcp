"""
CMDB tools for the ServiceNow MCP server.

This module provides tools for managing Configuration Items (CIs) and relationships
in ServiceNow's Configuration Management Database (CMDB).
"""

import logging
from typing import Optional, Dict, Any, List

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ListCIsParams(BaseModel):
    """Parameters for listing configuration items."""
    
    table: str = Field("cmdb_ci", description="CMDB table name (e.g., cmdb_ci, cmdb_ci_server, cmdb_ci_computer)")
    limit: int = Field(10, description="Maximum number of CIs to return")
    offset: int = Field(0, description="Offset for pagination")
    operational_status: Optional[str] = Field(None, description="Filter by operational status")
    name: Optional[str] = Field(None, description="Filter by CI name (contains)")
    query: Optional[str] = Field(None, description="ServiceNow encoded query string")


class GetCIParams(BaseModel):
    """Parameters for getting a specific CI."""
    
    ci_id: str = Field(..., description="CI sys_id or name")
    table: str = Field("cmdb_ci", description="CMDB table name")


class CreateCIParams(BaseModel):
    """Parameters for creating a configuration item."""
    
    table: str = Field("cmdb_ci", description="CMDB table name (e.g., cmdb_ci_server, cmdb_ci_computer)")
    name: str = Field(..., description="Name of the CI")
    short_description: Optional[str] = Field(None, description="Short description")
    operational_status: Optional[str] = Field(None, description="Operational status (1=Operational, 2=Non-Operational, etc.)")
    manufacturer: Optional[str] = Field(None, description="Manufacturer sys_id or name")
    model_id: Optional[str] = Field(None, description="Model sys_id")
    serial_number: Optional[str] = Field(None, description="Serial number")
    asset_tag: Optional[str] = Field(None, description="Asset tag")
    ip_address: Optional[str] = Field(None, description="IP address")
    location: Optional[str] = Field(None, description="Location sys_id or name")
    assigned_to: Optional[str] = Field(None, description="Assigned to user sys_id or name")
    managed_by: Optional[str] = Field(None, description="Managed by user sys_id or name")
    owned_by: Optional[str] = Field(None, description="Owned by user sys_id or name")
    support_group: Optional[str] = Field(None, description="Support group sys_id or name")
    additional_fields: Optional[Dict[str, Any]] = Field(None, description="Additional fields as key-value pairs")


class UpdateCIParams(BaseModel):
    """Parameters for updating a configuration item."""
    
    ci_id: str = Field(..., description="CI sys_id")
    table: str = Field("cmdb_ci", description="CMDB table name")
    name: Optional[str] = Field(None, description="Name of the CI")
    short_description: Optional[str] = Field(None, description="Short description")
    operational_status: Optional[str] = Field(None, description="Operational status")
    manufacturer: Optional[str] = Field(None, description="Manufacturer sys_id or name")
    model_id: Optional[str] = Field(None, description="Model sys_id")
    serial_number: Optional[str] = Field(None, description="Serial number")
    asset_tag: Optional[str] = Field(None, description="Asset tag")
    ip_address: Optional[str] = Field(None, description="IP address")
    location: Optional[str] = Field(None, description="Location sys_id or name")
    assigned_to: Optional[str] = Field(None, description="Assigned to user sys_id or name")
    managed_by: Optional[str] = Field(None, description="Managed by user sys_id or name")
    owned_by: Optional[str] = Field(None, description="Owned by user sys_id or name")
    support_group: Optional[str] = Field(None, description="Support group sys_id or name")
    additional_fields: Optional[Dict[str, Any]] = Field(None, description="Additional fields as key-value pairs")


class DeleteCIParams(BaseModel):
    """Parameters for deleting a configuration item."""
    
    ci_id: str = Field(..., description="CI sys_id")
    table: str = Field("cmdb_ci", description="CMDB table name")


class ListCIRelationshipsParams(BaseModel):
    """Parameters for listing CI relationships."""
    
    ci_id: str = Field(..., description="CI sys_id")
    direction: str = Field("all", description="Relationship direction: 'parent', 'child', or 'all'")
    limit: int = Field(50, description="Maximum number of relationships to return")


class CreateCIRelationshipParams(BaseModel):
    """Parameters for creating a CI relationship."""
    
    parent_id: str = Field(..., description="Parent CI sys_id")
    child_id: str = Field(..., description="Child CI sys_id")
    relationship_type: Optional[str] = Field(None, description="Relationship type sys_id (e.g., 'Depends on::Used by')")


class DeleteCIRelationshipParams(BaseModel):
    """Parameters for deleting a CI relationship."""
    
    relationship_id: str = Field(..., description="Relationship sys_id")


class SearchCIsParams(BaseModel):
    """Parameters for searching CIs."""
    
    search_term: str = Field(..., description="Search term to find in CI name or description")
    table: str = Field("cmdb_ci", description="CMDB table name")
    limit: int = Field(20, description="Maximum number of results to return")


class CMDBResponse(BaseModel):
    """Response from CMDB operations."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data from the operation")


def list_cis(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCIsParams,
) -> dict:
    """
    List configuration items from ServiceNow CMDB.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing CIs.
        
    Returns:
        Dictionary with list of CIs.
    """
    api_url = f"{config.api_url}/table/{params.table}"
    
    # Build query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Build query filters
    filters = []
    if params.operational_status:
        filters.append(f"operational_status={params.operational_status}")
    if params.name:
        filters.append(f"nameLIKE{params.name}")
    if params.query:
        filters.append(params.query)
    
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
        cis = []
        
        for ci_data in data.get("result", []):
            ci = {
                "sys_id": ci_data.get("sys_id"),
                "name": ci_data.get("name"),
                "short_description": ci_data.get("short_description"),
                "operational_status": ci_data.get("operational_status"),
                "manufacturer": ci_data.get("manufacturer"),
                "model_id": ci_data.get("model_id"),
                "serial_number": ci_data.get("serial_number"),
                "asset_tag": ci_data.get("asset_tag"),
                "ip_address": ci_data.get("ip_address"),
                "location": ci_data.get("location"),
                "assigned_to": ci_data.get("assigned_to"),
                "managed_by": ci_data.get("managed_by"),
                "owned_by": ci_data.get("owned_by"),
                "support_group": ci_data.get("support_group"),
                "sys_class_name": ci_data.get("sys_class_name"),
                "sys_created_on": ci_data.get("sys_created_on"),
                "sys_updated_on": ci_data.get("sys_updated_on"),
            }
            cis.append(ci)
        
        return {
            "success": True,
            "message": f"Found {len(cis)} configuration items",
            "cis": cis,
            "count": len(cis)
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to list CIs: {e}")
        return {
            "success": False,
            "message": f"Failed to list CIs: {str(e)}",
            "cis": []
        }


def get_ci(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCIParams,
) -> dict:
    """
    Get a specific configuration item from ServiceNow CMDB.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for getting a CI.
        
    Returns:
        Dictionary with CI details.
    """
    # Check if ci_id is a sys_id or name
    if len(params.ci_id) == 32 and all(c in "0123456789abcdef" for c in params.ci_id):
        api_url = f"{config.api_url}/table/{params.table}/{params.ci_id}"
        query_params = {
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        }
    else:
        # Search by name
        api_url = f"{config.api_url}/table/{params.table}"
        query_params = {
            "sysparm_query": f"name={params.ci_id}",
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
        
        data = response.json()
        
        # Handle both single record and list responses
        if "result" in data:
            if isinstance(data["result"], list):
                if not data["result"]:
                    return {
                        "success": False,
                        "message": f"CI not found: {params.ci_id}",
                    }
                ci_data = data["result"][0]
            else:
                ci_data = data["result"]
        else:
            return {
                "success": False,
                "message": "Invalid response from ServiceNow",
            }
        
        ci = {
            "sys_id": ci_data.get("sys_id"),
            "name": ci_data.get("name"),
            "short_description": ci_data.get("short_description"),
            "operational_status": ci_data.get("operational_status"),
            "manufacturer": ci_data.get("manufacturer"),
            "model_id": ci_data.get("model_id"),
            "serial_number": ci_data.get("serial_number"),
            "asset_tag": ci_data.get("asset_tag"),
            "ip_address": ci_data.get("ip_address"),
            "location": ci_data.get("location"),
            "assigned_to": ci_data.get("assigned_to"),
            "managed_by": ci_data.get("managed_by"),
            "owned_by": ci_data.get("owned_by"),
            "support_group": ci_data.get("support_group"),
            "sys_class_name": ci_data.get("sys_class_name"),
            "sys_created_on": ci_data.get("sys_created_on"),
            "sys_updated_on": ci_data.get("sys_updated_on"),
        }
        
        return {
            "success": True,
            "message": f"CI found: {ci['name']}",
            "ci": ci
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to get CI: {e}")
        return {
            "success": False,
            "message": f"Failed to get CI: {str(e)}",
        }


def create_ci(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateCIParams,
) -> CMDBResponse:
    """
    Create a new configuration item in ServiceNow CMDB.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating a CI.
        
    Returns:
        Response with the created CI details.
    """
    api_url = f"{config.api_url}/table/{params.table}"
    
    # Build request data
    data = {
        "name": params.name,
    }
    
    if params.short_description:
        data["short_description"] = params.short_description
    if params.operational_status:
        data["operational_status"] = params.operational_status
    if params.manufacturer:
        data["manufacturer"] = params.manufacturer
    if params.model_id:
        data["model_id"] = params.model_id
    if params.serial_number:
        data["serial_number"] = params.serial_number
    if params.asset_tag:
        data["asset_tag"] = params.asset_tag
    if params.ip_address:
        data["ip_address"] = params.ip_address
    if params.location:
        data["location"] = params.location
    if params.assigned_to:
        data["assigned_to"] = params.assigned_to
    if params.managed_by:
        data["managed_by"] = params.managed_by
    if params.owned_by:
        data["owned_by"] = params.owned_by
    if params.support_group:
        data["support_group"] = params.support_group
    
    # Add additional fields
    if params.additional_fields:
        data.update(params.additional_fields)
    
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
        
        return CMDBResponse(
            success=True,
            message=f"CI created successfully: {result.get('name')}",
            data={
                "sys_id": result.get("sys_id"),
                "name": result.get("name"),
                "table": params.table
            }
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to create CI: {e}")
        return CMDBResponse(
            success=False,
            message=f"Failed to create CI: {str(e)}",
        )


def update_ci(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateCIParams,
) -> CMDBResponse:
    """
    Update an existing configuration item in ServiceNow CMDB.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating a CI.
        
    Returns:
        Response with the updated CI details.
    """
    api_url = f"{config.api_url}/table/{params.table}/{params.ci_id}"
    
    # Build request data
    data = {}
    
    if params.name:
        data["name"] = params.name
    if params.short_description:
        data["short_description"] = params.short_description
    if params.operational_status:
        data["operational_status"] = params.operational_status
    if params.manufacturer:
        data["manufacturer"] = params.manufacturer
    if params.model_id:
        data["model_id"] = params.model_id
    if params.serial_number:
        data["serial_number"] = params.serial_number
    if params.asset_tag:
        data["asset_tag"] = params.asset_tag
    if params.ip_address:
        data["ip_address"] = params.ip_address
    if params.location:
        data["location"] = params.location
    if params.assigned_to:
        data["assigned_to"] = params.assigned_to
    if params.managed_by:
        data["managed_by"] = params.managed_by
    if params.owned_by:
        data["owned_by"] = params.owned_by
    if params.support_group:
        data["support_group"] = params.support_group
    
    # Add additional fields
    if params.additional_fields:
        data.update(params.additional_fields)
    
    if not data:
        return CMDBResponse(
            success=False,
            message="No fields to update",
        )
    
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
        
        return CMDBResponse(
            success=True,
            message=f"CI updated successfully: {result.get('name')}",
            data={
                "sys_id": result.get("sys_id"),
                "name": result.get("name"),
            }
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to update CI: {e}")
        return CMDBResponse(
            success=False,
            message=f"Failed to update CI: {str(e)}",
        )


def delete_ci(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: DeleteCIParams,
) -> CMDBResponse:
    """
    Delete a configuration item from ServiceNow CMDB.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for deleting a CI.
        
    Returns:
        Response with the deletion result.
    """
    api_url = f"{config.api_url}/table/{params.table}/{params.ci_id}"
    
    # Make request
    try:
        response = requests.delete(
            api_url,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        return CMDBResponse(
            success=True,
            message="CI deleted successfully",
            data={"sys_id": params.ci_id}
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to delete CI: {e}")
        return CMDBResponse(
            success=False,
            message=f"Failed to delete CI: {str(e)}",
        )


def list_ci_relationships(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCIRelationshipsParams,
) -> dict:
    """
    List relationships for a configuration item.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing CI relationships.
        
    Returns:
        Dictionary with list of relationships.
    """
    api_url = f"{config.api_url}/table/cmdb_rel_ci"
    
    # Build query based on direction
    if params.direction == "parent":
        query = f"child={params.ci_id}"
    elif params.direction == "child":
        query = f"parent={params.ci_id}"
    else:  # all
        query = f"parent={params.ci_id}^ORchild={params.ci_id}"
    
    query_params = {
        "sysparm_query": query,
        "sysparm_limit": params.limit,
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
        
        data = response.json()
        relationships = []
        
        for rel_data in data.get("result", []):
            relationship = {
                "sys_id": rel_data.get("sys_id"),
                "parent": rel_data.get("parent"),
                "child": rel_data.get("child"),
                "type": rel_data.get("type"),
                "sys_created_on": rel_data.get("sys_created_on"),
            }
            relationships.append(relationship)
        
        return {
            "success": True,
            "message": f"Found {len(relationships)} relationships",
            "relationships": relationships,
            "count": len(relationships)
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to list CI relationships: {e}")
        return {
            "success": False,
            "message": f"Failed to list CI relationships: {str(e)}",
            "relationships": []
        }


def create_ci_relationship(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateCIRelationshipParams,
) -> CMDBResponse:
    """
    Create a relationship between two configuration items.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating a CI relationship.
        
    Returns:
        Response with the created relationship details.
    """
    api_url = f"{config.api_url}/table/cmdb_rel_ci"
    
    # Build request data
    data = {
        "parent": params.parent_id,
        "child": params.child_id,
    }
    
    if params.relationship_type:
        data["type"] = params.relationship_type
    
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
        
        return CMDBResponse(
            success=True,
            message="CI relationship created successfully",
            data={
                "sys_id": result.get("sys_id"),
                "parent": result.get("parent"),
                "child": result.get("child"),
                "type": result.get("type"),
            }
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to create CI relationship: {e}")
        return CMDBResponse(
            success=False,
            message=f"Failed to create CI relationship: {str(e)}",
        )


def delete_ci_relationship(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: DeleteCIRelationshipParams,
) -> CMDBResponse:
    """
    Delete a relationship between configuration items.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for deleting a CI relationship.
        
    Returns:
        Response with the deletion result.
    """
    api_url = f"{config.api_url}/table/cmdb_rel_ci/{params.relationship_id}"
    
    # Make request
    try:
        response = requests.delete(
            api_url,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        return CMDBResponse(
            success=True,
            message="CI relationship deleted successfully",
            data={"sys_id": params.relationship_id}
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to delete CI relationship: {e}")
        return CMDBResponse(
            success=False,
            message=f"Failed to delete CI relationship: {str(e)}",
        )


def search_cis(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: SearchCIsParams,
) -> dict:
    """
    Search for configuration items by name or description.
    
    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for searching CIs.
        
    Returns:
        Dictionary with search results.
    """
    api_url = f"{config.api_url}/table/{params.table}"
    
    # Build search query
    query = f"nameLIKE{params.search_term}^ORshort_descriptionLIKE{params.search_term}"
    
    query_params = {
        "sysparm_query": query,
        "sysparm_limit": params.limit,
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
        
        data = response.json()
        cis = []
        
        for ci_data in data.get("result", []):
            ci = {
                "sys_id": ci_data.get("sys_id"),
                "name": ci_data.get("name"),
                "short_description": ci_data.get("short_description"),
                "operational_status": ci_data.get("operational_status"),
                "sys_class_name": ci_data.get("sys_class_name"),
            }
            cis.append(ci)
        
        return {
            "success": True,
            "message": f"Found {len(cis)} configuration items matching '{params.search_term}'",
            "cis": cis,
            "count": len(cis)
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to search CIs: {e}")
        return {
            "success": False,
            "message": f"Failed to search CIs: {str(e)}",
            "cis": []
        }
