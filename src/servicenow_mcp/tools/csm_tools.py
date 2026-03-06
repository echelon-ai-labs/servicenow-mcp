"""
Higher-level Customer Service Management tools for the ServiceNow MCP server.

Provides tools for querying CSM business entities: accounts, locations,
products, and integrations — plus case correlation tools that search cases
by these entities.

Reference data tools (list_accounts, list_locations, list_products) query
structured ServiceNow tables directly. Case correlation tools currently use
text-search workarounds on the task table; when CSM table access is granted,
the internals swap without changing the API surface.
"""

import logging
from typing import Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.case_tools import LIST_FIELDS, extract_case
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

MAX_LIMIT = 200


# ---------------------------------------------------------------------------
# Shared helper: search cases via task table
# ---------------------------------------------------------------------------

def _search_cases_by_query(
    config: ServerConfig,
    auth_manager: AuthManager,
    query_str: str,
    limit: int,
    offset: int,
) -> dict:
    """Query the task table for CSM cases matching *query_str*.

    Prepends ``sys_class_name=sn_customerservice_case`` to the query, caps
    the limit, and normalises results via ``extract_case()``.
    """
    api_url = f"{config.api_url}/table/task"
    limit = min(limit, MAX_LIMIT)

    full_query = f"sys_class_name=sn_customerservice_case^{query_str}"

    query_params = {
        "sysparm_query": full_query,
        "sysparm_limit": limit,
        "sysparm_offset": offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_fields": LIST_FIELDS,
    }

    response = requests.get(
        api_url,
        params=query_params,
        headers=auth_manager.get_headers(),
        timeout=config.timeout,
    )
    response.raise_for_status()

    data = response.json()
    return [extract_case(c) for c in data.get("result", [])]


# ---------------------------------------------------------------------------
# Param models — reference data
# ---------------------------------------------------------------------------

class ListAccountsParams(BaseModel):
    """Parameters for listing customer accounts."""
    name_filter: Optional[str] = Field(None, description="Filter accounts by name (LIKE search)")
    limit: int = Field(50, description="Maximum number of accounts to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")


class ListLocationsParams(BaseModel):
    """Parameters for listing locations."""
    account: Optional[str] = Field(None, description="Filter by company/account name")
    name_filter: Optional[str] = Field(None, description="Filter locations by name (LIKE search)")
    limit: int = Field(50, description="Maximum number of locations to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")


class ListProductsParams(BaseModel):
    """Parameters for listing sold products."""
    account: Optional[str] = Field(None, description="Filter by account name")
    product_name: Optional[str] = Field(None, description="Filter by product name")
    limit: int = Field(50, description="Maximum number of products to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")


# ---------------------------------------------------------------------------
# Param models — case correlation
# ---------------------------------------------------------------------------

class GetCasesByAccountParams(BaseModel):
    """Parameters for getting cases by customer account."""
    account_name: str = Field(..., description="Account name to search for")
    limit: int = Field(50, description="Maximum number of cases to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by case state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    created_after: Optional[str] = Field(None, description="Filter cases created after this date (YYYY-MM-DD)")


class GetCasesByLocationParams(BaseModel):
    """Parameters for getting cases by location."""
    location_name: str = Field(..., description="Location name to search for")
    limit: int = Field(50, description="Maximum number of cases to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by case state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    created_after: Optional[str] = Field(None, description="Filter cases created after this date (YYYY-MM-DD)")


class GetCasesByProductParams(BaseModel):
    """Parameters for getting cases by product type."""
    product_name: str = Field(..., description="Product name to search for")
    limit: int = Field(50, description="Maximum number of cases to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by case state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    created_after: Optional[str] = Field(None, description="Filter cases created after this date (YYYY-MM-DD)")


class GetCasesByIntegrationParams(BaseModel):
    """Parameters for getting cases by integration/vendor."""
    integration_name: str = Field(..., description="Integration or vendor name to search for")
    limit: int = Field(50, description="Maximum number of cases to return (max 200)")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by case state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    created_after: Optional[str] = Field(None, description="Filter cases created after this date (YYYY-MM-DD)")


class GetCaseHistoryParams(BaseModel):
    """Parameters for getting full case history (comments + work notes)."""
    case_number: str = Field(..., description="The case number (e.g. 'CS0008423')")


# ---------------------------------------------------------------------------
# Reference data tools
# ---------------------------------------------------------------------------

def list_accounts(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListAccountsParams,
) -> dict:
    """List customer accounts from the customer_account table.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Query parameters.

    Returns:
        Dictionary with list of accounts.
    """
    api_url = f"{config.api_url}/table/customer_account"
    limit = min(params.limit, MAX_LIMIT)

    filters = []
    if params.name_filter:
        filters.append(f"nameLIKE{params.name_filter}")

    query_params = {
        "sysparm_limit": limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_fields": "sys_id,name,account_code,city,state,country",
    }
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
        accounts = data.get("result", [])

        return {
            "success": True,
            "message": f"Found {len(accounts)} accounts",
            "accounts": accounts,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list accounts: {e}")
        return {
            "success": False,
            "message": f"Failed to list accounts: {str(e)}",
            "accounts": [],
        }


def list_locations(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListLocationsParams,
) -> dict:
    """List locations from the cmn_location table.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Query parameters.

    Returns:
        Dictionary with list of locations.
    """
    api_url = f"{config.api_url}/table/cmn_location"
    limit = min(params.limit, MAX_LIMIT)

    filters = []
    if params.account:
        filters.append(f"companyLIKE{params.account}")
    if params.name_filter:
        filters.append(f"nameLIKE{params.name_filter}")

    query_params = {
        "sysparm_limit": limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_fields": "sys_id,name,company,city,state,country",
    }
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
        locations = data.get("result", [])

        return {
            "success": True,
            "message": f"Found {len(locations)} locations",
            "locations": locations,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list locations: {e}")
        return {
            "success": False,
            "message": f"Failed to list locations: {str(e)}",
            "locations": [],
        }


def list_products(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListProductsParams,
) -> dict:
    """List sold products from the sn_install_base_sold_product table.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Query parameters.

    Returns:
        Dictionary with list of products.
    """
    api_url = f"{config.api_url}/table/sn_install_base_sold_product"
    limit = min(params.limit, MAX_LIMIT)

    filters = []
    if params.account:
        filters.append(f"accountLIKE{params.account}")
    if params.product_name:
        filters.append(f"nameLIKE{params.product_name}")

    query_params = {
        "sysparm_limit": limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_fields": "sys_id,name,account,product_model",
    }
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
        products = data.get("result", [])

        return {
            "success": True,
            "message": f"Found {len(products)} products",
            "products": products,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list products: {e}")
        return {
            "success": False,
            "message": f"Failed to list products: {str(e)}",
            "products": [],
        }


# ---------------------------------------------------------------------------
# Case correlation tools
# ---------------------------------------------------------------------------

def get_cases_by_account(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCasesByAccountParams,
) -> dict:
    """Get cases for a customer account.

    Validates the account exists in ``customer_account``, then searches cases
    via short_description LIKE on the task table.

    Future: swap to ``account={sys_id}`` on ``sn_customerservice_case``.
    """
    # Step 1: validate account exists
    acct_url = f"{config.api_url}/table/customer_account"
    try:
        acct_resp = requests.get(
            acct_url,
            params={
                "sysparm_query": f"nameLIKE{params.account_name}",
                "sysparm_limit": 1,
                "sysparm_fields": "sys_id,name",
            },
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        acct_resp.raise_for_status()
        acct_data = acct_resp.json().get("result", [])
        if not acct_data:
            return {
                "success": False,
                "message": f"Account not found: {params.account_name}",
                "cases": [],
            }
    except requests.RequestException as e:
        logger.error(f"Failed to look up account: {e}")
        return {
            "success": False,
            "message": f"Failed to look up account: {str(e)}",
            "cases": [],
        }

    # Step 2: search cases — text workaround
    # Future: query_str = f"account={acct_data[0]['sys_id']}"
    query_parts = [f"short_descriptionLIKE{params.account_name}"]
    if params.state:
        query_parts.append(f"state={params.state}")
    if params.priority:
        query_parts.append(f"priority={params.priority}")
    if params.created_after:
        query_parts.append(f"sys_created_on>={params.created_after}")

    query_str = "^".join(query_parts)

    try:
        cases = _search_cases_by_query(config, auth_manager, query_str, params.limit, params.offset)
        return {
            "success": True,
            "message": f"Found {len(cases)} cases for account '{params.account_name}'",
            "cases": cases,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to search cases by account: {e}")
        return {
            "success": False,
            "message": f"Failed to search cases by account: {str(e)}",
            "cases": [],
        }


def get_cases_by_location(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCasesByLocationParams,
) -> dict:
    """Get cases for a specific venue/location.

    Searches cases via short_description LIKE on the task table.

    Future: swap to ``location={sys_id}`` on ``sn_customerservice_case``.
    """
    query_parts = [f"short_descriptionLIKE{params.location_name}"]
    if params.state:
        query_parts.append(f"state={params.state}")
    if params.priority:
        query_parts.append(f"priority={params.priority}")
    if params.created_after:
        query_parts.append(f"sys_created_on>={params.created_after}")

    query_str = "^".join(query_parts)

    try:
        cases = _search_cases_by_query(config, auth_manager, query_str, params.limit, params.offset)
        return {
            "success": True,
            "message": f"Found {len(cases)} cases for location '{params.location_name}'",
            "cases": cases,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to search cases by location: {e}")
        return {
            "success": False,
            "message": f"Failed to search cases by location: {str(e)}",
            "cases": [],
        }


def get_cases_by_product(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCasesByProductParams,
) -> dict:
    """Get cases involving a specific product type.

    Searches short_description and description via LIKE on the task table.

    Future: swap to ``sold_product.name={product_name}`` on
    ``sn_customerservice_case``.
    """
    query_parts = [
        f"short_descriptionLIKE{params.product_name}^ORdescriptionLIKE{params.product_name}"
    ]
    if params.state:
        query_parts.append(f"state={params.state}")
    if params.priority:
        query_parts.append(f"priority={params.priority}")
    if params.created_after:
        query_parts.append(f"sys_created_on>={params.created_after}")

    query_str = "^".join(query_parts)

    try:
        cases = _search_cases_by_query(config, auth_manager, query_str, params.limit, params.offset)
        return {
            "success": True,
            "message": f"Found {len(cases)} cases for product '{params.product_name}'",
            "cases": cases,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to search cases by product: {e}")
        return {
            "success": False,
            "message": f"Failed to search cases by product: {str(e)}",
            "cases": [],
        }


def get_cases_by_integration(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCasesByIntegrationParams,
) -> dict:
    """Get cases involving a specific integration/vendor.

    Searches short_description and description via LIKE on the task table.

    Future: swap to a structured integration field on
    ``sn_customerservice_case`` when available.
    """
    query_parts = [
        f"short_descriptionLIKE{params.integration_name}^ORdescriptionLIKE{params.integration_name}"
    ]
    if params.state:
        query_parts.append(f"state={params.state}")
    if params.priority:
        query_parts.append(f"priority={params.priority}")
    if params.created_after:
        query_parts.append(f"sys_created_on>={params.created_after}")

    query_str = "^".join(query_parts)

    try:
        cases = _search_cases_by_query(config, auth_manager, query_str, params.limit, params.offset)
        return {
            "success": True,
            "message": f"Found {len(cases)} cases for integration '{params.integration_name}'",
            "cases": cases,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to search cases by integration: {e}")
        return {
            "success": False,
            "message": f"Failed to search cases by integration: {str(e)}",
            "cases": [],
        }


# ---------------------------------------------------------------------------
# Case detail tool
# ---------------------------------------------------------------------------

HISTORY_FIELDS = ",".join([
    "sys_id",
    "number",
    "short_description",
    "description",
    "state",
    "priority",
    "assigned_to",
    "company",
    "assignment_group",
    "comments",
    "work_notes",
    "close_notes",
    "opened_at",
    "closed_at",
    "resolved_at",
])


def get_case_history(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCaseHistoryParams,
) -> dict:
    """Get full comment and work note timeline for a case.

    Queries the task table requesting comments, work_notes, close_notes and
    key timestamps.
    """
    api_url = f"{config.api_url}/table/task"

    query_params = {
        "sysparm_query": f"sys_class_name=sn_customerservice_case^number={params.case_number}",
        "sysparm_limit": 1,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_fields": HISTORY_FIELDS,
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

        case = result[0]
        # Normalize assigned_to if it's a dict
        assigned_to = case.get("assigned_to")
        if isinstance(assigned_to, dict):
            case["assigned_to"] = assigned_to.get("display_value")

        return {
            "success": True,
            "message": f"Case {params.case_number} history retrieved",
            "case": case,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to get case history: {e}")
        return {
            "success": False,
            "message": f"Failed to get case history: {str(e)}",
        }
