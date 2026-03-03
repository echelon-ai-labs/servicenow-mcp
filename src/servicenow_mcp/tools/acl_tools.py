"""
Access Control List (ACL) and Security tools for the ServiceNow MCP server.

This module provides tools for managing Access Control Lists, Security Attributes,
and related security configurations in ServiceNow.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ListACLsParams(BaseModel):
    """Parameters for listing Access Control Lists."""
    
    limit: int = Field(10, description="Maximum number of ACLs to return")
    offset: int = Field(0, description="Offset for pagination")
    table_name: Optional[str] = Field(None, description="Filter by table name")
    operation: Optional[str] = Field(None, description="Filter by operation (read, write, create, delete)")
    active: Optional[bool] = Field(None, description="Filter by active status")
    query: Optional[str] = Field(None, description="Search query for ACLs")


class GetACLParams(BaseModel):
    """Parameters for getting a specific Access Control List."""
    
    acl_id: str = Field(..., description="ACL sys_id")


class CreateACLParams(BaseModel):
    """Parameters for creating a new Access Control List."""
    
    name: str = Field(..., description="Name of the ACL")
    type: str = Field(..., description="Type of ACL (record, field, etc.)")
    operation: str = Field(..., description="Operation (read, write, create, delete)")
    description: Optional[str] = Field(None, description="Description of the ACL")
    script: Optional[str] = Field(None, description="Script to evaluate access")
    active: bool = Field(True, description="Whether the ACL is active")
    admin_overrides: bool = Field(False, description="Whether admin role overrides this ACL")


class UpdateACLParams(BaseModel):
    """Parameters for updating an Access Control List."""
    
    acl_id: str = Field(..., description="ACL sys_id")
    name: Optional[str] = Field(None, description="Name of the ACL")
    description: Optional[str] = Field(None, description="Description of the ACL")
    script: Optional[str] = Field(None, description="Script to evaluate access")
    active: Optional[bool] = Field(None, description="Whether the ACL is active")
    admin_overrides: Optional[bool] = Field(None, description="Whether admin role overrides this ACL")


class DeleteACLParams(BaseModel):
    """Parameters for deleting an Access Control List."""
    
    acl_id: str = Field(..., description="ACL sys_id")


class ListRolesParams(BaseModel):
    """Parameters for listing roles."""
    
    limit: int = Field(10, description="Maximum number of roles to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for roles")
    active: Optional[bool] = Field(None, description="Filter by active status")


class GetRoleParams(BaseModel):
    """Parameters for getting a specific role."""
    
    role_id: str = Field(..., description="Role sys_id or name")


class CreateRoleParams(BaseModel):
    """Parameters for creating a new role."""
    
    name: str = Field(..., description="Name of the role")
    description: Optional[str] = Field(None, description="Description of the role")
    requires_subscription: Optional[str] = Field(None, description="Subscription requirement")
    elevated_privilege: bool = Field(False, description="Whether this is an elevated privilege role")


class UpdateRoleParams(BaseModel):
    """Parameters for updating a role."""
    
    role_id: str = Field(..., description="Role sys_id")
    name: Optional[str] = Field(None, description="Name of the role")
    description: Optional[str] = Field(None, description="Description of the role")
    requires_subscription: Optional[str] = Field(None, description="Subscription requirement")
    elevated_privilege: Optional[bool] = Field(None, description="Whether this is an elevated privilege role")


class AssignRoleToACLParams(BaseModel):
    """Parameters for assigning a role to an ACL."""
    
    acl_id: str = Field(..., description="ACL sys_id")
    role_id: str = Field(..., description="Role sys_id")


class RemoveRoleFromACLParams(BaseModel):
    """Parameters for removing a role from an ACL."""
    
    acl_id: str = Field(..., description="ACL sys_id")
    role_id: str = Field(..., description="Role sys_id")


class ListSecurityAttributesParams(BaseModel):
    """Parameters for listing security attributes."""
    
    limit: int = Field(10, description="Maximum number of security attributes to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for security attributes")


class CreateSecurityAttributeParams(BaseModel):
    """Parameters for creating a security attribute."""
    
    name: str = Field(..., description="Name of the security attribute")
    description: Optional[str] = Field(None, description="Description of the security attribute")
    type: str = Field("string", description="Type of the security attribute")


class ACLResponse(BaseModel):
    """Response from ACL operations."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


def list_acls(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListACLsParams,
) -> Dict[str, Any]:
    """
    List Access Control Lists from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing ACLs

    Returns:
        Dictionary containing ACLs and metadata
    """
    logger.info("Listing Access Control Lists")
    
    api_url = f"{config.api_url}/table/sys_security_acl"
    
    # Build query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Add filters
    filters = []
    if params.table_name:
        filters.append(f"name.name={params.table_name}")
    if params.operation:
        filters.append(f"operation={params.operation}")
    if params.active is not None:
        filters.append(f"active={str(params.active).lower()}")
    if params.query:
        filters.append(f"nameLIKE{params.query}^ORdescriptionLIKE{params.query}")
    
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
        acls = []
        
        for acl_data in data.get("result", []):
            acl = {
                "sys_id": acl_data.get("sys_id"),
                "name": acl_data.get("name"),
                "type": acl_data.get("type"),
                "operation": acl_data.get("operation"),
                "description": acl_data.get("description"),
                "active": acl_data.get("active"),
                "admin_overrides": acl_data.get("admin_overrides"),
                "script": acl_data.get("script", ""),
                "created_on": acl_data.get("sys_created_on"),
                "updated_on": acl_data.get("sys_updated_on"),
            }
            acls.append(acl)
        
        return {
            "success": True,
            "message": f"Found {len(acls)} ACLs",
            "acls": acls,
            "total": len(acls),
            "limit": params.limit,
            "offset": params.offset,
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to list ACLs: {e}")
        return {
            "success": False,
            "message": f"Failed to list ACLs: {str(e)}",
            "acls": [],
            "total": 0,
        }


def get_acl(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetACLParams,
) -> ACLResponse:
    """
    Get a specific Access Control List from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for getting ACL

    Returns:
        Response containing the ACL details
    """
    logger.info(f"Getting ACL: {params.acl_id}")
    
    api_url = f"{config.api_url}/table/sys_security_acl/{params.acl_id}"
    
    query_params = {
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        acl_data = data.get("result", {})
        
        if not acl_data:
            return ACLResponse(
                success=False,
                message=f"ACL not found: {params.acl_id}",
                data=None,
            )
        
        acl = {
            "sys_id": acl_data.get("sys_id"),
            "name": acl_data.get("name"),
            "type": acl_data.get("type"),
            "operation": acl_data.get("operation"),
            "description": acl_data.get("description"),
            "active": acl_data.get("active"),
            "admin_overrides": acl_data.get("admin_overrides"),
            "script": acl_data.get("script", ""),
            "created_on": acl_data.get("sys_created_on"),
            "updated_on": acl_data.get("sys_updated_on"),
        }
        
        return ACLResponse(
            success=True,
            message=f"Retrieved ACL: {acl_data.get('name', '')}",
            data=acl,
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to get ACL: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to get ACL: {str(e)}",
            data=None,
        )


def create_acl(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateACLParams,
) -> ACLResponse:
    """
    Create a new Access Control List in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating ACL

    Returns:
        Response containing the created ACL details
    """
    logger.info(f"Creating ACL: {params.name}")
    
    api_url = f"{config.api_url}/table/sys_security_acl"
    
    # Build request data
    data = {
        "name": params.name,
        "type": params.type,
        "operation": params.operation,
        "active": str(params.active).lower(),
        "admin_overrides": str(params.admin_overrides).lower(),
    }
    
    if params.description:
        data["description"] = params.description
    if params.script:
        data["script"] = params.script
    
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", {})
        
        return ACLResponse(
            success=True,
            message=f"ACL created successfully: {params.name}",
            data={
                "sys_id": result.get("sys_id"),
                "name": result.get("name"),
                "type": result.get("type"),
                "operation": result.get("operation"),
            },
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to create ACL: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to create ACL: {str(e)}",
            data=None,
        )


def update_acl(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateACLParams,
) -> ACLResponse:
    """
    Update an existing Access Control List in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating ACL

    Returns:
        Response containing the updated ACL details
    """
    logger.info(f"Updating ACL: {params.acl_id}")
    
    api_url = f"{config.api_url}/table/sys_security_acl/{params.acl_id}"
    
    # Build request data with only provided parameters
    data = {}
    if params.name is not None:
        data["name"] = params.name
    if params.description is not None:
        data["description"] = params.description
    if params.script is not None:
        data["script"] = params.script
    if params.active is not None:
        data["active"] = str(params.active).lower()
    if params.admin_overrides is not None:
        data["admin_overrides"] = str(params.admin_overrides).lower()
    
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", {})
        
        return ACLResponse(
            success=True,
            message=f"ACL updated successfully: {params.acl_id}",
            data={
                "sys_id": result.get("sys_id"),
                "name": result.get("name"),
                "type": result.get("type"),
                "operation": result.get("operation"),
            },
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to update ACL: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to update ACL: {str(e)}",
            data=None,
        )


def delete_acl(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: DeleteACLParams,
) -> ACLResponse:
    """
    Delete an Access Control List in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for deleting ACL

    Returns:
        Response containing the result of the operation
    """
    logger.info(f"Deleting ACL: {params.acl_id}")
    
    api_url = f"{config.api_url}/table/sys_security_acl/{params.acl_id}"
    
    try:
        response = requests.delete(
            api_url,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        return ACLResponse(
            success=True,
            message=f"ACL deleted successfully: {params.acl_id}",
            data={"sys_id": params.acl_id},
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to delete ACL: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to delete ACL: {str(e)}",
            data=None,
        )


def list_roles(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListRolesParams,
) -> Dict[str, Any]:
    """
    List roles from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing roles

    Returns:
        Dictionary containing roles and metadata
    """
    logger.info("Listing roles")
    
    api_url = f"{config.api_url}/table/sys_user_role"
    
    # Build query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Add filters
    filters = []
    if params.active is not None:
        filters.append(f"active={str(params.active).lower()}")
    if params.query:
        filters.append(f"nameLIKE{params.query}^ORdescriptionLIKE{params.query}")
    
    if filters:
        query_params["sysparm_query"] = "^".join(filters)
    
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        roles = []
        
        for role_data in data.get("result", []):
            role = {
                "sys_id": role_data.get("sys_id"),
                "name": role_data.get("name"),
                "description": role_data.get("description"),
                "elevated_privilege": role_data.get("elevated_privilege"),
                "requires_subscription": role_data.get("requires_subscription"),
                "created_on": role_data.get("sys_created_on"),
            }
            roles.append(role)
        
        return {
            "success": True,
            "message": f"Found {len(roles)} roles",
            "roles": roles,
            "total": len(roles),
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to list roles: {e}")
        return {
            "success": False,
            "message": f"Failed to list roles: {str(e)}",
            "roles": [],
            "total": 0,
        }


def get_role(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetRoleParams,
) -> ACLResponse:
    """
    Get a specific role from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for getting role

    Returns:
        Response containing the role details
    """
    logger.info(f"Getting role: {params.role_id}")
    
    # Check if role_id is a sys_id or name
    if len(params.role_id) == 32:
        # Likely a sys_id
        api_url = f"{config.api_url}/table/sys_user_role/{params.role_id}"
        query_params = {
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        }
    else:
        # Likely a name
        api_url = f"{config.api_url}/table/sys_user_role"
        query_params = {
            "sysparm_query": f"name={params.role_id}",
            "sysparm_limit": 1,
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        }
    
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Handle both direct fetch and query results
        if "result" in data:
            if isinstance(data["result"], list):
                if not data["result"]:
                    return ACLResponse(
                        success=False,
                        message=f"Role not found: {params.role_id}",
                        data=None,
                    )
                role_data = data["result"][0]
            else:
                role_data = data["result"]
        else:
            return ACLResponse(
                success=False,
                message=f"Role not found: {params.role_id}",
                data=None,
            )
        
        role = {
            "sys_id": role_data.get("sys_id"),
            "name": role_data.get("name"),
            "description": role_data.get("description"),
            "elevated_privilege": role_data.get("elevated_privilege"),
            "requires_subscription": role_data.get("requires_subscription"),
        }
        
        return ACLResponse(
            success=True,
            message=f"Retrieved role: {role_data.get('name', '')}",
            data=role,
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to get role: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to get role: {str(e)}",
            data=None,
        )


def create_role(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateRoleParams,
) -> ACLResponse:
    """
    Create a new role in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating role

    Returns:
        Response containing the created role details
    """
    logger.info(f"Creating role: {params.name}")
    
    api_url = f"{config.api_url}/table/sys_user_role"
    
    data = {
        "name": params.name,
        "elevated_privilege": str(params.elevated_privilege).lower(),
    }
    
    if params.description:
        data["description"] = params.description
    if params.requires_subscription:
        data["requires_subscription"] = params.requires_subscription
    
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", {})
        
        return ACLResponse(
            success=True,
            message=f"Role created successfully: {params.name}",
            data={
                "sys_id": result.get("sys_id"),
                "name": result.get("name"),
                "description": result.get("description"),
            },
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to create role: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to create role: {str(e)}",
            data=None,
        )


def update_role(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateRoleParams,
) -> ACLResponse:
    """
    Update an existing role in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating role

    Returns:
        Response containing the updated role details
    """
    logger.info(f"Updating role: {params.role_id}")
    
    api_url = f"{config.api_url}/table/sys_user_role/{params.role_id}"
    
    data = {}
    if params.name is not None:
        data["name"] = params.name
    if params.description is not None:
        data["description"] = params.description
    if params.requires_subscription is not None:
        data["requires_subscription"] = params.requires_subscription
    if params.elevated_privilege is not None:
        data["elevated_privilege"] = str(params.elevated_privilege).lower()
    
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", {})
        
        return ACLResponse(
            success=True,
            message=f"Role updated successfully: {params.role_id}",
            data={
                "sys_id": result.get("sys_id"),
                "name": result.get("name"),
                "description": result.get("description"),
            },
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to update role: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to update role: {str(e)}",
            data=None,
        )


def list_security_attributes(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListSecurityAttributesParams,
) -> Dict[str, Any]:
    """
    List security attributes from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing security attributes

    Returns:
        Dictionary containing security attributes and metadata
    """
    logger.info("Listing security attributes")
    
    api_url = f"{config.api_url}/table/sys_security_attribute"
    
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    if params.query:
        query_params["sysparm_query"] = f"nameLIKE{params.query}^ORdescriptionLIKE{params.query}"
    
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        attributes = []
        
        for attr_data in data.get("result", []):
            attribute = {
                "sys_id": attr_data.get("sys_id"),
                "name": attr_data.get("name"),
                "description": attr_data.get("description"),
                "type": attr_data.get("type"),
                "created_on": attr_data.get("sys_created_on"),
            }
            attributes.append(attribute)
        
        return {
            "success": True,
            "message": f"Found {len(attributes)} security attributes",
            "attributes": attributes,
            "total": len(attributes),
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to list security attributes: {e}")
        return {
            "success": False,
            "message": f"Failed to list security attributes: {str(e)}",
            "attributes": [],
            "total": 0,
        }


def create_security_attribute(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateSecurityAttributeParams,
) -> ACLResponse:
    """
    Create a security attribute in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating security attribute

    Returns:
        Response containing the created security attribute details
    """
    logger.info(f"Creating security attribute: {params.name}")
    
    api_url = f"{config.api_url}/table/sys_security_attribute"
    
    data = {
        "name": params.name,
        "type": params.type,
    }
    
    if params.description:
        data["description"] = params.description
    
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", {})
        
        return ACLResponse(
            success=True,
            message=f"Security attribute created successfully: {params.name}",
            data={
                "sys_id": result.get("sys_id"),
                "name": result.get("name"),
                "type": result.get("type"),
            },
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to create security attribute: {e}")
        return ACLResponse(
            success=False,
            message=f"Failed to create security attribute: {str(e)}",
            data=None,
        )
