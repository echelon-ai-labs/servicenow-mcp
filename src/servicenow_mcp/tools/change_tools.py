"""
Change management tools for the ServiceNow MCP server.

This module provides tools for managing change requests in ServiceNow.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

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


class CreateChangeRequestParams(BaseModel):
    """Parameters for creating a change request."""

    short_description: str = Field(..., description="Short description of the change request")
    description: Optional[str] = Field(None, description="Detailed description of the change request")
    type: str = Field(..., description="Type of change (normal, standard, emergency)")
    risk: Optional[str] = Field(None, description="Risk level of the change")
    impact: Optional[str] = Field(None, description="Impact of the change")
    category: Optional[str] = Field(None, description="Category of the change")
    requested_by: Optional[str] = Field(None, description="User who requested the change")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the change")
    start_date: Optional[str] = Field(None, description="Planned start date (YYYY-MM-DD HH:MM:SS)")
    end_date: Optional[str] = Field(None, description="Planned end date (YYYY-MM-DD HH:MM:SS)")


class UpdateChangeRequestParams(BaseModel):
    """Parameters for updating a change request."""

    change_id: str = Field(..., description="Change request ID or sys_id")
    short_description: Optional[str] = Field(None, description="Short description of the change request")
    description: Optional[str] = Field(None, description="Detailed description of the change request")
    state: Optional[str] = Field(None, description="State of the change request")
    risk: Optional[str] = Field(None, description="Risk level of the change")
    impact: Optional[str] = Field(None, description="Impact of the change")
    category: Optional[str] = Field(None, description="Category of the change")
    assignment_group: Optional[str] = Field(None, description="Group assigned to the change")
    start_date: Optional[str] = Field(None, description="Planned start date (YYYY-MM-DD HH:MM:SS)")
    end_date: Optional[str] = Field(None, description="Planned end date (YYYY-MM-DD HH:MM:SS)")
    work_notes: Optional[str] = Field(None, description="Work notes to add to the change request")


class ListChangeRequestsParams(BaseModel):
    """Parameters for listing change requests."""

    limit: Optional[int] = Field(10, description="Maximum number of records to return")
    offset: Optional[int] = Field(0, description="Offset to start from")
    state: Optional[str] = Field(None, description="Filter by state")
    type: Optional[str] = Field(None, description="Filter by type (normal, standard, emergency)")
    category: Optional[str] = Field(None, description="Filter by category")
    assignment_group: Optional[str] = Field(None, description="Filter by assignment group")
    timeframe: Optional[str] = Field(None, description="Filter by timeframe (upcoming, in-progress, completed)")
    query: Optional[str] = Field(None, description="Additional query string")


class GetChangeRequestDetailsParams(BaseModel):
    """Parameters for getting change request details."""

    change_id: str = Field(..., description="Change request ID or sys_id")


class AddChangeTaskParams(BaseModel):
    """Parameters for adding a task to a change request."""

    change_id: str = Field(..., description="Change request ID or sys_id")
    short_description: str = Field(..., description="Short description of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    assigned_to: Optional[str] = Field(None, description="User assigned to the task")
    planned_start_date: Optional[str] = Field(None, description="Planned start date (YYYY-MM-DD HH:MM:SS)")
    planned_end_date: Optional[str] = Field(None, description="Planned end date (YYYY-MM-DD HH:MM:SS)")


class SubmitChangeForApprovalParams(BaseModel):
    """Parameters for submitting a change request for approval."""

    change_id: str = Field(..., description="Change request ID or sys_id")
    approval_comments: Optional[str] = Field(None, description="Comments for the approval request")


class ApproveChangeParams(BaseModel):
    """Parameters for approving a change request."""

    change_id: str = Field(..., description="Change request ID or sys_id")
    approver_id: Optional[str] = Field(None, description="ID of the approver")
    approval_comments: Optional[str] = Field(None, description="Comments for the approval")


class RejectChangeParams(BaseModel):
    """Parameters for rejecting a change request."""

    change_id: str = Field(..., description="Change request ID or sys_id")
    approver_id: Optional[str] = Field(None, description="ID of the approver")
    rejection_reason: str = Field(..., description="Reason for rejection")


def create_change_request(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new change request in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for creating the change request.

    Returns:
        The created change request.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        CreateChangeRequestParams, 
        required_fields=["short_description", "type"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "short_description": validated_params.short_description,
        "type": validated_params.type,
    }
    
    # Add optional fields if provided
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.risk:
        data["risk"] = validated_params.risk
    if validated_params.impact:
        data["impact"] = validated_params.impact
    if validated_params.category:
        data["category"] = validated_params.category
    if validated_params.requested_by:
        data["requested_by"] = validated_params.requested_by
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.start_date:
        data["start_date"] = validated_params.start_date
    if validated_params.end_date:
        data["end_date"] = validated_params.end_date
    
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
    url = f"{instance_url}/api/now/table/change_request"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Change request created successfully",
            "change_request": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating change request: {e}")
        return {
            "success": False,
            "message": f"Error creating change request: {str(e)}",
        }


def update_change_request(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing change request in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for updating the change request.

    Returns:
        The updated change request.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        UpdateChangeRequestParams, 
        required_fields=["change_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {}
    
    # Add fields if provided
    if validated_params.short_description:
        data["short_description"] = validated_params.short_description
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.state:
        data["state"] = validated_params.state
    if validated_params.risk:
        data["risk"] = validated_params.risk
    if validated_params.impact:
        data["impact"] = validated_params.impact
    if validated_params.category:
        data["category"] = validated_params.category
    if validated_params.assignment_group:
        data["assignment_group"] = validated_params.assignment_group
    if validated_params.start_date:
        data["start_date"] = validated_params.start_date
    if validated_params.end_date:
        data["end_date"] = validated_params.end_date
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
    url = f"{instance_url}/api/now/table/change_request/{validated_params.change_id}"
    
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Change request updated successfully",
            "change_request": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating change request: {e}")
        return {
            "success": False,
            "message": f"Error updating change request: {str(e)}",
        }


def list_change_requests(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    List change requests from ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for listing change requests.

    Returns:
        A list of change requests.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        ListChangeRequestsParams
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Build the query
    query_parts = []
    
    if validated_params.state:
        query_parts.append(f"state={validated_params.state}")
    if validated_params.type:
        query_parts.append(f"type={validated_params.type}")
    if validated_params.category:
        query_parts.append(f"category={validated_params.category}")
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
    url = f"{instance_url}/api/now/table/change_request"
    
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
        change_requests = result.get("result", [])
        count = len(change_requests)
        
        return {
            "success": True,
            "change_requests": change_requests,
            "count": count,
            "total": count,  # Use count as total if total is not provided
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing change requests: {e}")
        return {
            "success": False,
            "message": f"Error listing change requests: {str(e)}",
        }


def get_change_request_details(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Get details of a change request from ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for getting change request details.

    Returns:
        The change request details.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        GetChangeRequestDetailsParams,
        required_fields=["change_id"]
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
    url = f"{instance_url}/api/now/table/change_request/{validated_params.change_id}"
    
    params = {
        "sysparm_display_value": "true",
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        result = response.json()
        
        # Get tasks associated with this change request
        tasks_url = f"{instance_url}/api/now/table/change_task"
        tasks_params = {
            "sysparm_query": f"change_request={validated_params.change_id}",
            "sysparm_display_value": "true",
        }
        
        tasks_response = requests.get(tasks_url, headers=headers, params=tasks_params)
        tasks_response.raise_for_status()
        
        tasks_result = tasks_response.json()
        
        return {
            "success": True,
            "change_request": result["result"],
            "tasks": tasks_result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting change request details: {e}")
        return {
            "success": False,
            "message": f"Error getting change request details: {str(e)}",
        }


def add_change_task(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Add a task to a change request in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for adding a change task.

    Returns:
        The created change task.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        AddChangeTaskParams,
        required_fields=["change_id", "short_description"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "change_request": validated_params.change_id,
        "short_description": validated_params.short_description,
    }
    
    # Add optional fields if provided
    if validated_params.description:
        data["description"] = validated_params.description
    if validated_params.assigned_to:
        data["assigned_to"] = validated_params.assigned_to
    if validated_params.planned_start_date:
        data["planned_start_date"] = validated_params.planned_start_date
    if validated_params.planned_end_date:
        data["planned_end_date"] = validated_params.planned_end_date
    
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
    url = f"{instance_url}/api/now/table/change_task"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "message": "Change task added successfully",
            "change_task": result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding change task: {e}")
        return {
            "success": False,
            "message": f"Error adding change task: {str(e)}",
        }


def submit_change_for_approval(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Submit a change request for approval in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for submitting a change request for approval.

    Returns:
        The result of the submission.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        SubmitChangeForApprovalParams,
        required_fields=["change_id"]
    )
    
    if not result["success"]:
        return result
    
    validated_params = result["params"]
    
    # Prepare the request data
    data = {
        "state": "assess",  # Set state to "assess" to submit for approval
    }
    
    # Add approval comments if provided
    if validated_params.approval_comments:
        data["work_notes"] = validated_params.approval_comments
    
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
    url = f"{instance_url}/api/now/table/change_request/{validated_params.change_id}"
    
    try:
        response = requests.patch(url, json=data, headers=headers)
        response.raise_for_status()
        
        # Now, create an approval request
        approval_url = f"{instance_url}/api/now/table/sysapproval_approver"
        approval_data = {
            "document_id": validated_params.change_id,
            "source_table": "change_request",
            "state": "requested",
        }
        
        approval_response = requests.post(approval_url, json=approval_data, headers=headers)
        approval_response.raise_for_status()
        
        approval_result = approval_response.json()
        
        return {
            "success": True,
            "message": "Change request submitted for approval successfully",
            "approval": approval_result["result"],
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting change for approval: {e}")
        return {
            "success": False,
            "message": f"Error submitting change for approval: {str(e)}",
        }


def approve_change(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Approve a change request in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for approving a change request.

    Returns:
        The result of the approval.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        ApproveChangeParams,
        required_fields=["change_id"]
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
    
    # First, find the approval record
    approval_query_url = f"{instance_url}/api/now/table/sysapproval_approver"
    
    query_params = {
        "sysparm_query": f"document_id={validated_params.change_id}",
        "sysparm_limit": 1,
    }
    
    try:
        approval_response = requests.get(approval_query_url, headers=headers, params=query_params)
        approval_response.raise_for_status()
        
        approval_result = approval_response.json()
        
        if not approval_result.get("result") or len(approval_result["result"]) == 0:
            return {
                "success": False,
                "message": "No approval record found for this change request",
            }
        
        approval_id = approval_result["result"][0]["sys_id"]
        
        # Now, update the approval record to approved
        approval_update_url = f"{instance_url}/api/now/table/sysapproval_approver/{approval_id}"
        headers["Content-Type"] = "application/json"
        
        approval_data = {
            "state": "approved",
        }
        
        if validated_params.approval_comments:
            approval_data["comments"] = validated_params.approval_comments
        
        approval_update_response = requests.patch(approval_update_url, json=approval_data, headers=headers)
        approval_update_response.raise_for_status()
        
        # Finally, update the change request state to "implement"
        change_url = f"{instance_url}/api/now/table/change_request/{validated_params.change_id}"
        
        change_data = {
            "state": "implement",  # This may vary depending on ServiceNow configuration
        }
        
        change_response = requests.patch(change_url, json=change_data, headers=headers)
        change_response.raise_for_status()
        
        return {
            "success": True,
            "message": "Change request approved successfully",
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error approving change: {e}")
        return {
            "success": False,
            "message": f"Error approving change: {str(e)}",
        }


def reject_change(
    auth_manager: AuthManager,
    server_config: ServerConfig,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Reject a change request in ServiceNow.

    Args:
        auth_manager: The authentication manager.
        server_config: The server configuration.
        params: The parameters for rejecting a change request.

    Returns:
        The result of the rejection.
    """
    # Unwrap and validate parameters
    result = _unwrap_and_validate_params(
        params, 
        RejectChangeParams,
        required_fields=["change_id", "rejection_reason"]
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
    
    # First, find the approval record
    approval_query_url = f"{instance_url}/api/now/table/sysapproval_approver"
    
    query_params = {
        "sysparm_query": f"document_id={validated_params.change_id}",
        "sysparm_limit": 1,
    }
    
    try:
        approval_response = requests.get(approval_query_url, headers=headers, params=query_params)
        approval_response.raise_for_status()
        
        approval_result = approval_response.json()
        
        if not approval_result.get("result") or len(approval_result["result"]) == 0:
            return {
                "success": False,
                "message": "No approval record found for this change request",
            }
        
        approval_id = approval_result["result"][0]["sys_id"]
        
        # Now, update the approval record to rejected
        approval_update_url = f"{instance_url}/api/now/table/sysapproval_approver/{approval_id}"
        headers["Content-Type"] = "application/json"
        
        approval_data = {
            "state": "rejected",
            "comments": validated_params.rejection_reason,
        }
        
        approval_update_response = requests.patch(approval_update_url, json=approval_data, headers=headers)
        approval_update_response.raise_for_status()
        
        # Finally, update the change request state to "canceled"
        change_url = f"{instance_url}/api/now/table/change_request/{validated_params.change_id}"
        
        change_data = {
            "state": "canceled",  # This may vary depending on ServiceNow configuration
            "work_notes": f"Change request rejected: {validated_params.rejection_reason}",
        }
        
        change_response = requests.patch(change_url, json=change_data, headers=headers)
        change_response.raise_for_status()
        
        return {
            "success": True,
            "message": "Change request rejected successfully",
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error rejecting change: {e}")
        return {
            "success": False,
            "message": f"Error rejecting change: {str(e)}",
        } 