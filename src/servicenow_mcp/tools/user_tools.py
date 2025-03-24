"""
User management tools for the ServiceNow MCP server.

This module provides tools for managing users and groups in ServiceNow.
"""

import logging
from typing import List, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class CreateUserParams(BaseModel):
    """Parameters for creating a user."""

    user_name: str = Field(..., description="Username for the user")
    first_name: str = Field(..., description="First name of the user")
    last_name: str = Field(..., description="Last name of the user")
    email: str = Field(..., description="Email address of the user")
    title: Optional[str] = Field(None, description="Job title of the user")
    department: Optional[str] = Field(None, description="Department the user belongs to")
    manager: Optional[str] = Field(None, description="Manager of the user (sys_id or username)")
    roles: Optional[List[str]] = Field(None, description="Roles to assign to the user")
    phone: Optional[str] = Field(None, description="Phone number of the user")
    mobile_phone: Optional[str] = Field(None, description="Mobile phone number of the user")
    location: Optional[str] = Field(None, description="Location of the user")
    password: Optional[str] = Field(None, description="Password for the user account")
    active: Optional[bool] = Field(True, description="Whether the user account is active")


class UpdateUserParams(BaseModel):
    """Parameters for updating a user."""

    user_id: str = Field(..., description="User ID or sys_id to update")
    user_name: Optional[str] = Field(None, description="Username for the user")
    first_name: Optional[str] = Field(None, description="First name of the user")
    last_name: Optional[str] = Field(None, description="Last name of the user")
    email: Optional[str] = Field(None, description="Email address of the user")
    title: Optional[str] = Field(None, description="Job title of the user")
    department: Optional[str] = Field(None, description="Department the user belongs to")
    manager: Optional[str] = Field(None, description="Manager of the user (sys_id or username)")
    roles: Optional[List[str]] = Field(None, description="Roles to assign to the user")
    phone: Optional[str] = Field(None, description="Phone number of the user")
    mobile_phone: Optional[str] = Field(None, description="Mobile phone number of the user")
    location: Optional[str] = Field(None, description="Location of the user")
    password: Optional[str] = Field(None, description="Password for the user account")
    active: Optional[bool] = Field(None, description="Whether the user account is active")


class GetUserParams(BaseModel):
    """Parameters for getting a user."""

    user_id: Optional[str] = Field(None, description="User ID or sys_id")
    user_name: Optional[str] = Field(None, description="Username of the user")
    email: Optional[str] = Field(None, description="Email address of the user")


class ListUsersParams(BaseModel):
    """Parameters for listing users."""
    
    limit: int = Field(10, description="Maximum number of users to return")
    offset: int = Field(0, description="Offset for pagination")
    active: Optional[bool] = Field(None, description="Filter by active status")
    department: Optional[str] = Field(None, description="Filter by department")
    query: Optional[str] = Field(None, description="Search query for users")


class CreateGroupParams(BaseModel):
    """Parameters for creating a group."""

    name: str = Field(..., description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    manager: Optional[str] = Field(None, description="Manager of the group (sys_id or username)")
    parent: Optional[str] = Field(None, description="Parent group (sys_id or name)")
    type: Optional[str] = Field(None, description="Type of the group")
    email: Optional[str] = Field(None, description="Email address for the group")
    members: Optional[List[str]] = Field(None, description="List of user sys_ids or usernames to add as members")
    active: Optional[bool] = Field(True, description="Whether the group is active")


class UpdateGroupParams(BaseModel):
    """Parameters for updating a group."""

    group_id: str = Field(..., description="Group ID or sys_id to update")
    name: Optional[str] = Field(None, description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    manager: Optional[str] = Field(None, description="Manager of the group (sys_id or username)")
    parent: Optional[str] = Field(None, description="Parent group (sys_id or name)")
    type: Optional[str] = Field(None, description="Type of the group")
    email: Optional[str] = Field(None, description="Email address for the group")
    active: Optional[bool] = Field(None, description="Whether the group is active")


class AddGroupMembersParams(BaseModel):
    """Parameters for adding members to a group."""

    group_id: str = Field(..., description="Group ID or sys_id")
    members: List[str] = Field(..., description="List of user sys_ids or usernames to add as members")


class RemoveGroupMembersParams(BaseModel):
    """Parameters for removing members from a group."""

    group_id: str = Field(..., description="Group ID or sys_id")
    members: List[str] = Field(..., description="List of user sys_ids or usernames to remove as members")


class UserResponse(BaseModel):
    """Response from user operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    user_id: Optional[str] = Field(None, description="ID of the affected user")
    user_name: Optional[str] = Field(None, description="Username of the affected user")


class GroupResponse(BaseModel):
    """Response from group operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    group_id: Optional[str] = Field(None, description="ID of the affected group")
    group_name: Optional[str] = Field(None, description="Name of the affected group")


def create_user(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateUserParams,
) -> UserResponse:
    """
    Create a new user in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the user.

    Returns:
        Response with the created user details.
    """
    api_url = f"{config.api_url}/table/sys_user"

    # Build request data
    data = {
        "user_name": params.user_name,
        "first_name": params.first_name,
        "last_name": params.last_name,
        "email": params.email,
        "active": str(params.active).lower(),
    }

    if params.title:
        data["title"] = params.title
    if params.department:
        data["department"] = params.department
    if params.manager:
        data["manager"] = params.manager
    if params.phone:
        data["phone"] = params.phone
    if params.mobile_phone:
        data["mobile_phone"] = params.mobile_phone
    if params.location:
        data["location"] = params.location
    if params.password:
        data["user_password"] = params.password

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

        # Handle role assignments if provided
        if params.roles and result.get("sys_id"):
            assign_roles_to_user(config, auth_manager, result.get("sys_id"), params.roles)

        return UserResponse(
            success=True,
            message="User created successfully",
            user_id=result.get("sys_id"),
            user_name=result.get("user_name"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to create user: {e}")
        return UserResponse(
            success=False,
            message=f"Failed to create user: {str(e)}",
        )


def update_user(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateUserParams,
) -> UserResponse:
    """
    Update an existing user in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the user.

    Returns:
        Response with the updated user details.
    """
    api_url = f"{config.api_url}/table/sys_user/{params.user_id}"

    # Build request data
    data = {}
    if params.user_name:
        data["user_name"] = params.user_name
    if params.first_name:
        data["first_name"] = params.first_name
    if params.last_name:
        data["last_name"] = params.last_name
    if params.email:
        data["email"] = params.email
    if params.title:
        data["title"] = params.title
    if params.department:
        data["department"] = params.department
    if params.manager:
        data["manager"] = params.manager
    if params.phone:
        data["phone"] = params.phone
    if params.mobile_phone:
        data["mobile_phone"] = params.mobile_phone
    if params.location:
        data["location"] = params.location
    if params.password:
        data["user_password"] = params.password
    if params.active is not None:
        data["active"] = str(params.active).lower()

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        # Handle role assignments if provided
        if params.roles:
            assign_roles_to_user(config, auth_manager, params.user_id, params.roles)

        return UserResponse(
            success=True,
            message="User updated successfully",
            user_id=result.get("sys_id"),
            user_name=result.get("user_name"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to update user: {e}")
        return UserResponse(
            success=False,
            message=f"Failed to update user: {str(e)}",
        )


def get_user(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetUserParams,
) -> dict:
    """
    Get a user from ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for getting the user.

    Returns:
        Dictionary containing user details.
    """
    api_url = f"{config.api_url}/table/sys_user"
    query_params = {}

    # Build query parameters
    if params.user_id:
        query_params["sysparm_query"] = f"sys_id={params.user_id}"
    elif params.user_name:
        query_params["sysparm_query"] = f"user_name={params.user_name}"
    elif params.email:
        query_params["sysparm_query"] = f"email={params.email}"
    else:
        return {"success": False, "message": "At least one search parameter is required"}

    query_params["sysparm_limit"] = "1"
    query_params["sysparm_display_value"] = "true"

    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", [])
        if not result:
            return {"success": False, "message": "User not found"}

        return {"success": True, "message": "User found", "user": result[0]}

    except requests.RequestException as e:
        logger.error(f"Failed to get user: {e}")
        return {"success": False, "message": f"Failed to get user: {str(e)}"}


def list_users(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListUsersParams,
) -> dict:
    """
    List users from ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing users.

    Returns:
        Dictionary containing list of users.
    """
    api_url = f"{config.api_url}/table/sys_user"
    query_params = {
        "sysparm_limit": str(params.limit),
        "sysparm_offset": str(params.offset),
        "sysparm_display_value": "true",
    }

    # Build query
    query_parts = []
    if params.active is not None:
        query_parts.append(f"active={str(params.active).lower()}")
    if params.department:
        query_parts.append(f"department={params.department}")
    if params.query:
        query_parts.append(f"^nameLIKE{params.query}^ORuser_nameLIKE{params.query}^ORemailLIKE{params.query}")

    if query_parts:
        query_params["sysparm_query"] = "^".join(query_parts)

    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", [])
        
        return {
            "success": True,
            "message": f"Found {len(result)} users",
            "users": result,
            "count": len(result),
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list users: {e}")
        return {"success": False, "message": f"Failed to list users: {str(e)}"}


def assign_roles_to_user(
    config: ServerConfig,
    auth_manager: AuthManager,
    user_id: str,
    roles: List[str],
) -> bool:
    """
    Assign roles to a user in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        user_id: User ID or sys_id.
        roles: List of roles to assign.

    Returns:
        Boolean indicating success.
    """
    # For each role, create a user_role record
    api_url = f"{config.api_url}/table/sys_user_role"
    
    success = True
    for role in roles:
        # First check if the role exists
        role_id = get_role_id(config, auth_manager, role)
        if not role_id:
            logger.warning(f"Role '{role}' not found, skipping assignment")
            continue

        # Check if the user already has this role
        if check_user_has_role(config, auth_manager, user_id, role_id):
            logger.info(f"User already has role '{role}', skipping assignment")
            continue

        # Create the user role assignment
        data = {
            "user": user_id,
            "role": role_id,
        }

        try:
            response = requests.post(
                api_url,
                json=data,
                headers=auth_manager.get_headers(),
                timeout=config.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to assign role '{role}' to user: {e}")
            success = False

    return success


def get_role_id(
    config: ServerConfig,
    auth_manager: AuthManager,
    role_name: str,
) -> Optional[str]:
    """
    Get the sys_id of a role by its name.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        role_name: Name of the role.

    Returns:
        sys_id of the role if found, None otherwise.
    """
    api_url = f"{config.api_url}/table/sys_user_role"
    query_params = {
        "sysparm_query": f"name={role_name}",
        "sysparm_limit": "1",
    }

    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", [])
        if not result:
            return None

        return result[0].get("sys_id")

    except requests.RequestException as e:
        logger.error(f"Failed to get role ID: {e}")
        return None


def check_user_has_role(
    config: ServerConfig,
    auth_manager: AuthManager,
    user_id: str,
    role_id: str,
) -> bool:
    """
    Check if a user has a specific role.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        user_id: User ID or sys_id.
        role_id: Role ID or sys_id.

    Returns:
        Boolean indicating whether the user has the role.
    """
    api_url = f"{config.api_url}/table/sys_user_has_role"
    query_params = {
        "sysparm_query": f"user={user_id}^role={role_id}",
        "sysparm_limit": "1",
    }

    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", [])
        return len(result) > 0

    except requests.RequestException as e:
        logger.error(f"Failed to check if user has role: {e}")
        return False


def create_group(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateGroupParams,
) -> GroupResponse:
    """
    Create a new group in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the group.

    Returns:
        Response with the created group details.
    """
    api_url = f"{config.api_url}/table/sys_user_group"

    # Build request data
    data = {
        "name": params.name,
        "active": str(params.active).lower(),
    }

    if params.description:
        data["description"] = params.description
    if params.manager:
        data["manager"] = params.manager
    if params.parent:
        data["parent"] = params.parent
    if params.type:
        data["type"] = params.type
    if params.email:
        data["email"] = params.email

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
        group_id = result.get("sys_id")

        # Add members if provided
        if params.members and group_id:
            add_group_members(
                config, 
                auth_manager, 
                AddGroupMembersParams(group_id=group_id, members=params.members)
            )

        return GroupResponse(
            success=True,
            message="Group created successfully",
            group_id=group_id,
            group_name=result.get("name"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to create group: {e}")
        return GroupResponse(
            success=False,
            message=f"Failed to create group: {str(e)}",
        )


def update_group(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateGroupParams,
) -> GroupResponse:
    """
    Update an existing group in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the group.

    Returns:
        Response with the updated group details.
    """
    api_url = f"{config.api_url}/table/sys_user_group/{params.group_id}"

    # Build request data
    data = {}
    if params.name:
        data["name"] = params.name
    if params.description:
        data["description"] = params.description
    if params.manager:
        data["manager"] = params.manager
    if params.parent:
        data["parent"] = params.parent
    if params.type:
        data["type"] = params.type
    if params.email:
        data["email"] = params.email
    if params.active is not None:
        data["active"] = str(params.active).lower()

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return GroupResponse(
            success=True,
            message="Group updated successfully",
            group_id=result.get("sys_id"),
            group_name=result.get("name"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to update group: {e}")
        return GroupResponse(
            success=False,
            message=f"Failed to update group: {str(e)}",
        )


def add_group_members(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: AddGroupMembersParams,
) -> GroupResponse:
    """
    Add members to a group in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for adding members to the group.

    Returns:
        Response with the result of the operation.
    """
    api_url = f"{config.api_url}/table/sys_user_grmember"
    
    success = True
    failed_members = []
    
    for member in params.members:
        # Get user ID if username is provided
        user_id = member
        if not member.startswith("sys_id:"):
            user = get_user(
                config, 
                auth_manager, 
                GetUserParams(user_name=member)
            )
            if not user.get("success"):
                user = get_user(
                    config, 
                    auth_manager, 
                    GetUserParams(email=member)
                )
            
            if user.get("success"):
                user_id = user.get("user", {}).get("sys_id")
            else:
                success = False
                failed_members.append(member)
                continue
                
        # Create group membership
        data = {
            "group": params.group_id,
            "user": user_id,
        }

        try:
            response = requests.post(
                api_url,
                json=data,
                headers=auth_manager.get_headers(),
                timeout=config.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to add member '{member}' to group: {e}")
            success = False
            failed_members.append(member)

    if failed_members:
        message = f"Some members could not be added to the group: {', '.join(failed_members)}"
    else:
        message = "All members added to the group successfully"

    return GroupResponse(
        success=success,
        message=message,
        group_id=params.group_id,
    )


def remove_group_members(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: RemoveGroupMembersParams,
) -> GroupResponse:
    """
    Remove members from a group in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for removing members from the group.

    Returns:
        Response with the result of the operation.
    """
    success = True
    failed_members = []
    
    for member in params.members:
        # Get user ID if username is provided
        user_id = member
        if not member.startswith("sys_id:"):
            user = get_user(
                config, 
                auth_manager, 
                GetUserParams(user_name=member)
            )
            if not user.get("success"):
                user = get_user(
                    config, 
                    auth_manager, 
                    GetUserParams(email=member)
                )
            
            if user.get("success"):
                user_id = user.get("user", {}).get("sys_id")
            else:
                success = False
                failed_members.append(member)
                continue
                
        # Find and delete the group membership
        api_url = f"{config.api_url}/table/sys_user_grmember"
        query_params = {
            "sysparm_query": f"group={params.group_id}^user={user_id}",
            "sysparm_limit": "1",
        }

        try:
            # First find the membership record
            response = requests.get(
                api_url,
                params=query_params,
                headers=auth_manager.get_headers(),
                timeout=config.timeout,
            )
            response.raise_for_status()
            
            result = response.json().get("result", [])
            if not result:
                success = False
                failed_members.append(member)
                continue
                
            # Then delete the membership record
            membership_id = result[0].get("sys_id")
            delete_url = f"{api_url}/{membership_id}"
            
            response = requests.delete(
                delete_url,
                headers=auth_manager.get_headers(),
                timeout=config.timeout,
            )
            response.raise_for_status()
            
        except requests.RequestException as e:
            logger.error(f"Failed to remove member '{member}' from group: {e}")
            success = False
            failed_members.append(member)

    if failed_members:
        message = f"Some members could not be removed from the group: {', '.join(failed_members)}"
    else:
        message = "All members removed from the group successfully"

    return GroupResponse(
        success=success,
        message=message,
        group_id=params.group_id,
    ) 