"""
Customer Service Case tools for the ServiceNow MCP server.

This module provides read-only tools for querying Customer Service Cases
(sn_customerservice_case) in ServiceNow. All queries go through the `task`
table filtered by sys_class_name because direct access to the
sn_customerservice_case table returns 401.
"""

import logging
from typing import Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

# Fields to return in list/search operations (performance with 17K+ records)
LIST_FIELDS = ",".join([
    "sys_id",
    "number",
    "short_description",
    "state",
    "priority",
    "category",
    "subcategory",
    "assigned_to",
    "contact_type",
    "sys_created_on",
    "sys_updated_on",
])

MAX_LIMIT = 200


class ListCasesParams(BaseModel):
    """Parameters for listing customer service cases."""

    limit: int = Field(50, description="Maximum number of cases to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by case state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    category: Optional[str] = Field(None, description="Filter by category")
    subcategory: Optional[str] = Field(None, description="Filter by subcategory")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")
    contact_type: Optional[str] = Field(None, description="Filter by contact type (e.g. phone, email, web)")
    created_after: Optional[str] = Field(None, description="Filter cases created after this date (YYYY-MM-DD)")
    created_before: Optional[str] = Field(None, description="Filter cases created before this date (YYYY-MM-DD)")
    query: Optional[str] = Field(None, description="Additional encoded query string")
    order_by: Optional[str] = Field(None, description="Field to order results by (prefix with - for descending)")


class GetCaseByNumberParams(BaseModel):
    """Parameters for fetching a case by its CS number."""

    case_number: str = Field(..., description="The case number (e.g. CS0017600)")


class SearchCasesParams(BaseModel):
    """Parameters for full-text searching cases."""

    search_text: str = Field(..., description="Text to search for in short_description and description")
    limit: int = Field(50, description="Maximum number of cases to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by case state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    created_after: Optional[str] = Field(None, description="Filter cases created after this date (YYYY-MM-DD)")


def extract_case(case_data: dict) -> dict:
    """Normalize a case record from the API response.

    Handles the assigned_to field which can be either a string or a dict
    with a display_value key.
    """
    assigned_to = case_data.get("assigned_to")
    if isinstance(assigned_to, dict):
        assigned_to = assigned_to.get("display_value")

    return {
        "sys_id": case_data.get("sys_id"),
        "number": case_data.get("number"),
        "short_description": case_data.get("short_description"),
        "description": case_data.get("description"),
        "state": case_data.get("state"),
        "priority": case_data.get("priority"),
        "category": case_data.get("category"),
        "subcategory": case_data.get("subcategory"),
        "assigned_to": assigned_to,
        "contact_type": case_data.get("contact_type"),
        "created_on": case_data.get("sys_created_on"),
        "updated_on": case_data.get("sys_updated_on"),
    }


def list_cases(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCasesParams,
) -> dict:
    """
    List customer service cases from ServiceNow.

    Queries the task table filtered by sys_class_name=sn_customerservice_case.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing cases.

    Returns:
        Dictionary with list of cases.
    """
    api_url = f"{config.api_url}/table/task"

    limit = min(params.limit, MAX_LIMIT)

    # Build query - always filter by sys_class_name
    filters = ["sys_class_name=sn_customerservice_case"]

    if params.state:
        filters.append(f"state={params.state}")
    if params.priority:
        filters.append(f"priority={params.priority}")
    if params.category:
        filters.append(f"category={params.category}")
    if params.subcategory:
        filters.append(f"subcategory={params.subcategory}")
    if params.assigned_to:
        filters.append(f"assigned_to={params.assigned_to}")
    if params.contact_type:
        filters.append(f"contact_type={params.contact_type}")
    if params.created_after:
        filters.append(f"sys_created_on>={params.created_after}")
    if params.created_before:
        filters.append(f"sys_created_on<={params.created_before}")
    if params.query:
        filters.append(params.query)

    query_string = "^".join(filters)
    if params.order_by:
        if params.order_by.startswith("-"):
            query_string += f"^ORDERBY DESC{params.order_by[1:]}"
        else:
            query_string += f"^ORDERBY{params.order_by}"

    query_params = {
        "sysparm_query": query_string,
        "sysparm_limit": limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_fields": LIST_FIELDS,
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
        cases = [extract_case(c) for c in data.get("result", [])]

        return {
            "success": True,
            "message": f"Found {len(cases)} cases",
            "cases": cases,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list cases: {e}")
        return {
            "success": False,
            "message": f"Failed to list cases: {str(e)}",
            "cases": [],
        }


def get_case_by_number(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCaseByNumberParams,
) -> dict:
    """
    Fetch a single customer service case by its CS number.

    Queries the task table filtered by sys_class_name and number.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters with the case number.

    Returns:
        Dictionary with the case details.
    """
    api_url = f"{config.api_url}/table/task"

    query_params = {
        "sysparm_query": f"sys_class_name=sn_customerservice_case^number={params.case_number}",
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
        result = data.get("result", [])

        if not result:
            return {
                "success": False,
                "message": f"Case not found: {params.case_number}",
            }

        case = extract_case(result[0])

        return {
            "success": True,
            "message": f"Case {params.case_number} found",
            "case": case,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to fetch case: {e}")
        return {
            "success": False,
            "message": f"Failed to fetch case: {str(e)}",
        }


def search_cases(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: SearchCasesParams,
) -> dict:
    """
    Full-text search across customer service case short_description and description.

    Queries the task table filtered by sys_class_name with LIKE operators.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for searching cases.

    Returns:
        Dictionary with matching cases.
    """
    api_url = f"{config.api_url}/table/task"

    limit = min(params.limit, MAX_LIMIT)

    # Build query - sys_class_name filter + text search
    filters = [
        "sys_class_name=sn_customerservice_case",
        f"short_descriptionLIKE{params.search_text}^ORdescriptionLIKE{params.search_text}",
    ]

    if params.state:
        filters.append(f"state={params.state}")
    if params.priority:
        filters.append(f"priority={params.priority}")
    if params.created_after:
        filters.append(f"sys_created_on>={params.created_after}")

    query_params = {
        "sysparm_query": "^".join(filters),
        "sysparm_limit": limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_fields": LIST_FIELDS,
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
        cases = [extract_case(c) for c in data.get("result", [])]

        return {
            "success": True,
            "message": f"Found {len(cases)} cases matching '{params.search_text}'",
            "cases": cases,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to search cases: {e}")
        return {
            "success": False,
            "message": f"Failed to search cases: {str(e)}",
            "cases": [],
        }
