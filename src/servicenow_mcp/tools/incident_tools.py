"""
Incident tools for the ServiceNow MCP server.

This module provides tools for managing incidents in ServiceNow.
"""

import logging
from typing import List, Optional, Tuple

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class CreateIncidentParams(BaseModel):
    """Parameters for creating an incident."""

    short_description: str = Field(..., description="Short description of the incident")
    description: Optional[str] = Field(None, description="Detailed description of the incident")
    caller_id: Optional[str] = Field(
        None, description="User who reported the incident (sys_id, username, name, or email)"
    )
    channel: Optional[str] = Field(
        None,
        description="Channel / contact type, e.g. email, phone, chat, self-service, walk-in, "
        "virtual_agent",
    )
    category: Optional[str] = Field(None, description="Category of the incident")
    subcategory: Optional[str] = Field(None, description="Subcategory of the incident")
    priority: Optional[str] = Field(
        None, description="Priority (usually auto-calculated from impact + urgency)"
    )
    impact: Optional[str] = Field(None, description="Impact of the incident (1 High, 2 Medium, 3 Low)")
    urgency: Optional[str] = Field(None, description="Urgency of the incident (1 High, 2 Medium, 3 Low)")
    assigned_to: Optional[str] = Field(
        None, description="User assigned to the incident (sys_id, username, name, or email)"
    )
    assignment_group: Optional[str] = Field(
        None, description="Group assigned to the incident (sys_id or group name)"
    )


class UpdateIncidentParams(BaseModel):
    """Parameters for updating an incident."""

    incident_id: str = Field(..., description="Incident number or sys_id")
    short_description: Optional[str] = Field(None, description="Short description of the incident")
    description: Optional[str] = Field(None, description="Detailed description of the incident")
    state: Optional[str] = Field(
        None, description="State code: 1 New, 2 In Progress, 3 On Hold, 6 Resolved, 7 Closed, 8 Canceled"
    )
    channel: Optional[str] = Field(
        None, description="Channel / contact type, e.g. email, phone, chat, self-service, walk-in"
    )
    category: Optional[str] = Field(None, description="Category of the incident")
    subcategory: Optional[str] = Field(None, description="Subcategory of the incident")
    priority: Optional[str] = Field(
        None, description="Priority (usually auto-calculated from impact + urgency)"
    )
    impact: Optional[str] = Field(None, description="Impact of the incident (1 High, 2 Medium, 3 Low)")
    urgency: Optional[str] = Field(None, description="Urgency of the incident (1 High, 2 Medium, 3 Low)")
    assigned_to: Optional[str] = Field(
        None, description="User assigned to the incident (sys_id, username, name, or email)"
    )
    assignment_group: Optional[str] = Field(
        None, description="Group assigned to the incident (sys_id or group name)"
    )
    work_notes: Optional[str] = Field(None, description="Work notes to add to the incident")
    close_notes: Optional[str] = Field(None, description="Close notes to add to the incident")
    close_code: Optional[str] = Field(None, description="Close code for the incident")


class AddCommentParams(BaseModel):
    """Parameters for adding a comment to an incident."""

    incident_id: str = Field(..., description="Incident ID or sys_id")
    comment: str = Field(..., description="Comment to add to the incident")
    is_work_note: bool = Field(False, description="Whether the comment is a work note")


class ResolveIncidentParams(BaseModel):
    """Parameters for resolving an incident."""

    incident_id: str = Field(..., description="Incident ID or sys_id")
    resolution_code: str = Field(..., description="Resolution code for the incident")
    resolution_notes: str = Field(..., description="Resolution notes for the incident")


class ListIncidentsParams(BaseModel):
    """Parameters for listing incidents."""
    
    limit: int = Field(10, description="Maximum number of incidents to return")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by incident state")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")
    category: Optional[str] = Field(None, description="Filter by category")
    urgency: Optional[str] = Field(None, description="Filter by urgency (1 High, 2 Medium, 3 Low)")
    severity: Optional[str] = Field(None, description="Filter by severity (1 High, 2 Medium, 3 Low)")
    impact: Optional[str] = Field(None, description="Filter by impact (1 High, 2 Medium, 3 Low)")
    priority: Optional[str] = Field(None, description="Filter by priority (1 Critical .. 5 Planning)")
    query: Optional[str] = Field(
        None, description="Free-text keyword search across short description and description"
    )
    created_after: Optional[str] = Field(
        None,
        description="Only incidents created on/after this date. Accepts 'YYYY-MM-DD' "
        "(start of day) or 'YYYY-MM-DD HH:MM:SS'. Combine with created_before for a range.",
    )
    created_before: Optional[str] = Field(
        None,
        description="Only incidents created on/before this date. Accepts 'YYYY-MM-DD' "
        "(end of day) or 'YYYY-MM-DD HH:MM:SS'.",
    )
    updated_after: Optional[str] = Field(
        None,
        description="Only incidents whose last update/response was on/after this date "
        "('YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS').",
    )
    updated_before: Optional[str] = Field(
        None,
        description="Only incidents whose last update/response was on/before this date "
        "('YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS').",
    )


class GetIncidentByNumberParams(BaseModel):
    """Parameters for fetching an incident by its number."""

    incident_number: str = Field(..., description="The number of the incident to fetch")


class GetIncidentParams(BaseModel):
    """Parameters for fetching a single incident by number or sys_id."""

    incident_id: str = Field(..., description="Incident number (e.g. INC0010001) or sys_id")


class DeleteIncidentParams(BaseModel):
    """Parameters for deleting an incident."""

    incident_id: str = Field(..., description="Incident number (e.g. INC0010001) or sys_id")


class CloseIncidentParams(BaseModel):
    """Parameters for closing an incident."""

    incident_id: str = Field(..., description="Incident number (e.g. INC0010001) or sys_id")
    close_code: str = Field(
        ...,
        description="Resolution/close code — must be one of the instance's configured choices "
        "(e.g. 'Solution provided')",
    )
    close_notes: str = Field(..., description="Close notes describing the resolution")


class ReopenIncidentParams(BaseModel):
    """Parameters for reopening a resolved/closed incident."""

    incident_id: str = Field(..., description="Incident number (e.g. INC0010001) or sys_id")
    reopen_notes: Optional[str] = Field(
        None, description="Work note explaining why the incident is being reopened"
    )


class IncidentResponse(BaseModel):
    """Response from incident operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    incident_id: Optional[str] = Field(None, description="ID of the affected incident")
    incident_number: Optional[str] = Field(None, description="Number of the affected incident")


def _error_detail(exc: requests.RequestException) -> str:
    """Extract a useful message from a ServiceNow error response, if present.

    ServiceNow returns errors as ``{"error": {"message": ..., "detail": ...}}``.
    The default ``str(exception)`` only shows the HTTP status (e.g. "403 Client
    Error: Forbidden"), hiding the real reason — for example
    "Data Policy Exception: The following fields are mandatory: Resolution code".
    Surfacing that detail is what makes failed incident operations debuggable.
    """
    resp = getattr(exc, "response", None)
    if resp is None:
        return str(exc)
    detail = ""
    try:
        err = resp.json().get("error", {})
        detail = " - ".join(str(p).strip() for p in (err.get("message"), err.get("detail")) if p)
    except ValueError:
        detail = (resp.text or "").strip()[:300]

    message = f"HTTP {resp.status_code}"
    if detail:
        message += f": {detail}"
    # Auth problems otherwise look identical to every other failure; nudge the user.
    if resp.status_code == 401 or (resp.status_code == 403 and not detail):
        message += (
            " (verify SERVICENOW_USERNAME/SERVICENOW_PASSWORD and that the account "
            "has the required role and ACLs on this record)"
        )
    return message


def _field(value):
    """Extract ``(raw_value, display_value)`` from a Table API field.

    With ``sysparm_display_value=all`` every field is returned as
    ``{"value": ..., "display_value": ...}``. For flat responses (mocks, or
    ``display_value`` false/true) both elements are the same scalar.
    """
    if isinstance(value, dict):
        return value.get("value"), value.get("display_value")
    return value, value


def _format_incident(incident_data: dict) -> dict:
    """Build the incident dict returned by the read tools.

    Coded fields (``state``, ``priority``) are returned as their raw codes — the
    values that ``update_incident``/filters expect — with the human-readable
    label alongside as ``*_display``.
    """
    state_value, state_display = _field(incident_data.get("state"))
    priority_value, priority_display = _field(incident_data.get("priority"))
    _, assigned_to = _field(incident_data.get("assigned_to"))

    return {
        "sys_id": _field(incident_data.get("sys_id"))[0],
        "number": _field(incident_data.get("number"))[0],
        "short_description": _field(incident_data.get("short_description"))[0],
        "description": _field(incident_data.get("description"))[0],
        "state": state_value,
        "state_display": state_display,
        "priority": priority_value,
        "priority_display": priority_display,
        "assigned_to": assigned_to,
        "category": _field(incident_data.get("category"))[0],
        "subcategory": _field(incident_data.get("subcategory"))[0],
        "created_on": _field(incident_data.get("sys_created_on"))[0],
        "updated_on": _field(incident_data.get("sys_updated_on"))[0],
    }


def _resolve_incident_sys_id(
    config: ServerConfig,
    auth_manager: AuthManager,
    incident_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve an incident number or sys_id to a sys_id.

    Returns a ``(sys_id, error_message)`` tuple where exactly one element is set.
    A 32-char hex string is treated as a sys_id; anything else is looked up by
    ``number=``.
    """
    if len(incident_id) == 32 and all(c in "0123456789abcdef" for c in incident_id):
        return incident_id, None

    try:
        response = requests.get(
            f"{config.api_url}/table/incident",
            params={"sysparm_query": f"number={incident_id}", "sysparm_limit": 1},
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to find incident: {e}")
        return None, f"Failed to find incident: {_error_detail(e)}"

    result = response.json().get("result", [])
    if not result:
        return None, f"Incident not found: {incident_id}"
    return result[0].get("sys_id"), None


def _resolve_reference(
    config: ServerConfig,
    auth_manager: AuthManager,
    table: str,
    value: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a reference-field value to a sys_id.

    Accepts a 32-char sys_id (returned as-is) or a human-friendly value: for
    ``sys_user`` it matches name / user_name / email; for ``sys_user_group`` it
    matches the group name. Returns ``(sys_id, error_message)``.
    """
    if len(value) == 32 and all(c in "0123456789abcdef" for c in value):
        return value, None

    if table == "sys_user":
        query = f"name={value}^ORuser_name={value}^ORemail={value}"
        label = "user"
    else:
        query = f"name={value}"
        label = "group"

    try:
        response = requests.get(
            f"{config.api_url}/table/{table}",
            params={"sysparm_query": query, "sysparm_limit": 1, "sysparm_fields": "sys_id"},
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to resolve {label} '{value}': {e}")
        return None, f"Failed to resolve {label} '{value}': {_error_detail(e)}"

    result = response.json().get("result", [])
    if not result:
        return None, f"No {label} found matching '{value}'"
    return result[0].get("sys_id"), None


def _date_bound(value: str, end_of_day: bool) -> str:
    """Normalize a date filter value for a sysparm_query datetime comparison.

    A date-only value ('YYYY-MM-DD') is expanded to the start (00:00:00) or end
    (23:59:59) of that day so '<=' / '>=' cover the whole day; a full datetime is
    used as-is.
    """
    v = (value or "").strip()
    if len(v) == 10:  # YYYY-MM-DD
        v += " 23:59:59" if end_of_day else " 00:00:00"
    return v


def create_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateIncidentParams,
) -> IncidentResponse:
    """
    Create a new incident in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the incident.

    Returns:
        Response with the created incident details.
    """
    api_url = f"{config.api_url}/table/incident"

    # Build request data
    data = {
        "short_description": params.short_description,
    }

    if params.description:
        data["description"] = params.description
    if params.caller_id:
        sys_id, err = _resolve_reference(config, auth_manager, "sys_user", params.caller_id)
        if err:
            return IncidentResponse(success=False, message=err)
        data["caller_id"] = sys_id
    if params.channel:
        data["contact_type"] = params.channel
    if params.category:
        data["category"] = params.category
    if params.subcategory:
        data["subcategory"] = params.subcategory
    if params.priority:
        data["priority"] = params.priority
    if params.impact:
        data["impact"] = params.impact
    if params.urgency:
        data["urgency"] = params.urgency
    if params.assigned_to:
        sys_id, err = _resolve_reference(config, auth_manager, "sys_user", params.assigned_to)
        if err:
            return IncidentResponse(success=False, message=err)
        data["assigned_to"] = sys_id
    if params.assignment_group:
        sys_id, err = _resolve_reference(config, auth_manager, "sys_user_group", params.assignment_group)
        if err:
            return IncidentResponse(success=False, message=err)
        data["assignment_group"] = sys_id

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

        return IncidentResponse(
            success=True,
            message="Incident created successfully",
            incident_id=result.get("sys_id"),
            incident_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to create incident: {e}")
        return IncidentResponse(
            success=False,
            message=f"Failed to create incident: {_error_detail(e)}",
        )


def update_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateIncidentParams,
) -> IncidentResponse:
    """
    Update an existing incident in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the incident.

    Returns:
        Response with the updated incident details.
    """
    # Resolve incident number/sys_id to a sys_id
    sys_id, error = _resolve_incident_sys_id(config, auth_manager, params.incident_id)
    if error:
        return IncidentResponse(success=False, message=error)
    api_url = f"{config.api_url}/table/incident/{sys_id}"

    # Build request data
    data = {}

    if params.short_description:
        data["short_description"] = params.short_description
    if params.description:
        data["description"] = params.description
    if params.state:
        data["state"] = params.state
    if params.channel:
        data["contact_type"] = params.channel
    if params.category:
        data["category"] = params.category
    if params.subcategory:
        data["subcategory"] = params.subcategory
    if params.priority:
        data["priority"] = params.priority
    if params.impact:
        data["impact"] = params.impact
    if params.urgency:
        data["urgency"] = params.urgency
    if params.assigned_to:
        ref_id, err = _resolve_reference(config, auth_manager, "sys_user", params.assigned_to)
        if err:
            return IncidentResponse(success=False, message=err)
        data["assigned_to"] = ref_id
    if params.assignment_group:
        ref_id, err = _resolve_reference(config, auth_manager, "sys_user_group", params.assignment_group)
        if err:
            return IncidentResponse(success=False, message=err)
        data["assignment_group"] = ref_id
    if params.work_notes:
        data["work_notes"] = params.work_notes
    if params.close_notes:
        data["close_notes"] = params.close_notes
    if params.close_code:
        data["close_code"] = params.close_code

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

        return IncidentResponse(
            success=True,
            message="Incident updated successfully",
            incident_id=result.get("sys_id"),
            incident_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to update incident: {e}")
        return IncidentResponse(
            success=False,
            message=f"Failed to update incident: {_error_detail(e)}",
        )


def add_comment(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: AddCommentParams,
) -> IncidentResponse:
    """
    Add a comment to an incident in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for adding the comment.

    Returns:
        Response with the result of the operation.
    """
    # Resolve incident number/sys_id to a sys_id
    sys_id, error = _resolve_incident_sys_id(config, auth_manager, params.incident_id)
    if error:
        return IncidentResponse(success=False, message=error)
    api_url = f"{config.api_url}/table/incident/{sys_id}"

    # Build request data
    data = {}

    if params.is_work_note:
        data["work_notes"] = params.comment
    else:
        data["comments"] = params.comment

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

        return IncidentResponse(
            success=True,
            message="Comment added successfully",
            incident_id=result.get("sys_id"),
            incident_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to add comment: {e}")
        return IncidentResponse(
            success=False,
            message=f"Failed to add comment: {_error_detail(e)}",
        )


def resolve_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ResolveIncidentParams,
) -> IncidentResponse:
    """
    Resolve an incident in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for resolving the incident.

    Returns:
        Response with the result of the operation.
    """
    # Resolve incident number/sys_id to a sys_id
    sys_id, error = _resolve_incident_sys_id(config, auth_manager, params.incident_id)
    if error:
        return IncidentResponse(success=False, message=error)
    api_url = f"{config.api_url}/table/incident/{sys_id}"

    # Build request data.
    # NOTE: do NOT send resolved_at — ServiceNow sets resolved_at/resolved_by
    # automatically when state moves to Resolved. Sending the literal "now" is
    # not a valid datetime and is silently dropped by the Table API.
    # close_code must be one of the instance's configured "Resolution code"
    # choices (e.g. "Solution provided"); an invalid value is dropped, which
    # then trips the mandatory-field Data Policy and returns HTTP 403.
    data = {
        "state": "6",  # Resolved
        "close_code": params.resolution_code,
        "close_notes": params.resolution_notes,
    }

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

        return IncidentResponse(
            success=True,
            message="Incident resolved successfully",
            incident_id=result.get("sys_id"),
            incident_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to resolve incident: {e}")
        return IncidentResponse(
            success=False,
            message=f"Failed to resolve incident: {_error_detail(e)}",
        )


def list_incidents(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListIncidentsParams,
) -> dict:
    """
    List incidents from ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing incidents.

    Returns:
        Dictionary with list of incidents.
    """
    api_url = f"{config.api_url}/table/incident"

    # Build query parameters.
    # display_value=all returns both raw codes and display labels for every
    # field, so callers get the code (for round-tripping into update/filters)
    # and the human-readable label together.
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "all",
        "sysparm_exclude_reference_link": "true",
    }

    # Add filters. The free-text OR goes first: ServiceNow groups `^OR` with the
    # immediately preceding term, so "shortLIKEq^ORdescLIKEq^state=X^..." parses as
    # "(short OR desc) AND state=X AND ...". Putting it last would scope the other
    # filters only to the first OR branch.
    filters = []
    if params.query:
        filters.append(f"short_descriptionLIKE{params.query}^ORdescriptionLIKE{params.query}")
    if params.state:
        filters.append(f"state={params.state}")
    if params.assigned_to:
        filters.append(f"assigned_to={params.assigned_to}")
    if params.category:
        filters.append(f"category={params.category}")
    if params.urgency:
        filters.append(f"urgency={params.urgency}")
    if params.severity:
        filters.append(f"severity={params.severity}")
    if params.impact:
        filters.append(f"impact={params.impact}")
    if params.priority:
        filters.append(f"priority={params.priority}")
    # Creation-date filters (single date, or a range with both bounds)
    if params.created_after:
        filters.append(f"sys_created_on>={_date_bound(params.created_after, end_of_day=False)}")
    if params.created_before:
        filters.append(f"sys_created_on<={_date_bound(params.created_before, end_of_day=True)}")
    # Last-response (last updated) filters
    if params.updated_after:
        filters.append(f"sys_updated_on>={_date_bound(params.updated_after, end_of_day=False)}")
    if params.updated_before:
        filters.append(f"sys_updated_on<={_date_bound(params.updated_before, end_of_day=True)}")

    # Return newest incidents first so recently-created ones are not paged out.
    query = "^".join(filters)
    query = f"{query}^ORDERBYDESCsys_created_on" if query else "ORDERBYDESCsys_created_on"
    query_params["sysparm_query"] = query
    
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
        incidents = [_format_incident(item) for item in data.get("result", [])]

        return {
            "success": True,
            "message": f"Found {len(incidents)} incidents",
            "incidents": incidents
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to list incidents: {e}")
        return {
            "success": False,
            "message": f"Failed to list incidents: {_error_detail(e)}",
            "incidents": []
        }


def get_incident_by_number(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetIncidentByNumberParams,
) -> dict:
    """
    Fetch a single incident from ServiceNow by its number.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for fetching the incident.

    Returns:
        Dictionary with the incident details.
    """
    api_url = f"{config.api_url}/table/incident"

    # Build query parameters
    query_params = {
        "sysparm_query": f"number={params.incident_number}",
        "sysparm_limit": 1,
        "sysparm_display_value": "all",
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
        result = data.get("result", [])

        if not result:
            return {
                "success": False,
                "message": f"Incident not found: {params.incident_number}",
            }

        return {
            "success": True,
            "message": f"Incident {params.incident_number} found",
            "incident": _format_incident(result[0]),
        }

    except requests.RequestException as e:
        logger.error(f"Failed to fetch incident: {e}")
        return {
            "success": False,
            "message": f"Failed to fetch incident: {_error_detail(e)}",
        }


def get_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetIncidentParams,
) -> dict:
    """
    Fetch a single incident from ServiceNow by its number OR sys_id.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters identifying the incident (number or sys_id).

    Returns:
        Dictionary with the incident details.
    """
    sys_id, error = _resolve_incident_sys_id(config, auth_manager, params.incident_id)
    if error:
        return {"success": False, "message": error}

    try:
        response = requests.get(
            f"{config.api_url}/table/incident/{sys_id}",
            params={
                "sysparm_display_value": "all",
                "sysparm_exclude_reference_link": "true",
            },
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

    except requests.RequestException as e:
        logger.error(f"Failed to fetch incident: {e}")
        return {
            "success": False,
            "message": f"Failed to fetch incident: {_error_detail(e)}",
        }

    incident_data = response.json().get("result", {})
    if not incident_data:
        return {"success": False, "message": f"Incident not found: {params.incident_id}"}

    incident = _format_incident(incident_data)
    return {
        "success": True,
        "message": f"Incident {incident.get('number')} found",
        "incident": incident,
    }


def delete_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: DeleteIncidentParams,
) -> IncidentResponse:
    """
    Delete an incident in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters identifying the incident (number or sys_id).

    Returns:
        Response with the result of the operation.
    """
    sys_id, error = _resolve_incident_sys_id(config, auth_manager, params.incident_id)
    if error:
        return IncidentResponse(success=False, message=error)

    try:
        response = requests.delete(
            f"{config.api_url}/table/incident/{sys_id}",
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

    except requests.RequestException as e:
        logger.error(f"Failed to delete incident: {e}")
        return IncidentResponse(
            success=False,
            message=f"Failed to delete incident: {_error_detail(e)}",
        )

    # A successful DELETE returns HTTP 204 with no body.
    return IncidentResponse(
        success=True,
        message="Incident deleted successfully",
        incident_id=sys_id,
    )


def close_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CloseIncidentParams,
) -> IncidentResponse:
    """
    Close an incident in ServiceNow (state = Closed).

    Like resolving, closing is gated by a Data Policy that makes the resolution
    code and close notes mandatory, so both are required parameters.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for closing the incident.

    Returns:
        Response with the result of the operation.
    """
    sys_id, error = _resolve_incident_sys_id(config, auth_manager, params.incident_id)
    if error:
        return IncidentResponse(success=False, message=error)
    api_url = f"{config.api_url}/table/incident/{sys_id}"

    data = {
        "state": "7",  # Closed
        "close_code": params.close_code,
        "close_notes": params.close_notes,
    }

    try:
        response = requests.put(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})
        return IncidentResponse(
            success=True,
            message="Incident closed successfully",
            incident_id=result.get("sys_id"),
            incident_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to close incident: {e}")
        return IncidentResponse(
            success=False,
            message=f"Failed to close incident: {_error_detail(e)}",
        )


def reopen_incident(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ReopenIncidentParams,
) -> IncidentResponse:
    """
    Reopen a resolved or closed incident (state = In Progress).

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for reopening the incident.

    Returns:
        Response with the result of the operation.
    """
    sys_id, error = _resolve_incident_sys_id(config, auth_manager, params.incident_id)
    if error:
        return IncidentResponse(success=False, message=error)
    api_url = f"{config.api_url}/table/incident/{sys_id}"

    data = {"state": "2"}  # In Progress
    if params.reopen_notes:
        data["work_notes"] = params.reopen_notes

    try:
        response = requests.put(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})
        return IncidentResponse(
            success=True,
            message="Incident reopened successfully",
            incident_id=result.get("sys_id"),
            incident_number=result.get("number"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to reopen incident: {e}")
        return IncidentResponse(
            success=False,
            message=f"Failed to reopen incident: {_error_detail(e)}",
        )
