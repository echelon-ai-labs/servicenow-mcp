"""
Tools that require a real user session (SESSION auth).

They call internal ServiceNow UI endpoints or rely on user context
(for example, javascript:gs.getUserID()) that only works with cookies +
X-UserToken from a valid SSO session.
"""
import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import AuthType, ServerConfig

logger = logging.getLogger(__name__)


def _ensure_session_auth(auth_manager: AuthManager) -> Optional[str]:
    """Return error message if auth is not SESSION; otherwise None."""
    if auth_manager.config.type != AuthType.SESSION:
        return (
            "This tool requires SERVICENOW_AUTH_TYPE=session "
            "(browser SSO session authentication)."
        )
    return None


# ── Params ───────────────────────────────────────────────────────────────────

class UiGlobalSearchParams(BaseModel):
    query: str = Field(..., description="Global search term in ServiceNow")
    limit: int = Field(10, description="Maximum number of results per category")


class UiMyAssignedTasksParams(BaseModel):
    table: str = Field("task", description="Base table (task, incident, sc_req_item, change_request)")
    state_filter: Optional[str] = Field(
        None, description="Additional encoded query filter (e.g., 'active=true')"
    )
    limit: int = Field(20, description="Maximum number of tasks")


class UiMyGroupsParams(BaseModel):
    pass


class UiUserPresenceParams(BaseModel):
    user_ids: Optional[list[str]] = Field(
        None, description="sys_ids of users to check presence for (None = only current user)"
    )


class UiCurrentUserParams(BaseModel):
    pass


# ── Tools ────────────────────────────────────────────────────────────────────

def ui_global_search(
    config: ServerConfig, auth_manager: AuthManager, params: UiGlobalSearchParams
) -> str:
    """ServiceNow global search (same as top navigation search)."""
    err = _ensure_session_auth(auth_manager)
    if err:
        return json.dumps({"error": err})

    url = f"{config.instance_url}/api/now/sg/global_search"
    response = auth_manager.make_request(
        "GET",
        url,
        params={"sysparm_search": params.query, "sysparm_limit": params.limit},
        timeout=config.timeout,
    )
    if response.status_code != 200:
        return json.dumps({"error": f"HTTP {response.status_code}", "body": response.text[:500]})
    return json.dumps(response.json())


def ui_my_assigned_tasks(
    config: ServerConfig, auth_manager: AuthManager, params: UiMyAssignedTasksParams
) -> str:
    """Tasks assigned to the logged-in user (uses gs.getUserID() via dynamic query)."""
    err = _ensure_session_auth(auth_manager)
    if err:
        return json.dumps({"error": err})

    user_id = auth_manager._get_session_data().get("user_id")
    if not user_id:
        return json.dumps({"error": "user_id not available in current session"})

    query = f"assigned_to={user_id}^ORDERBYDESCsys_updated_on"
    if params.state_filter:
        query = f"{query}^{params.state_filter}"

    url = f"{config.instance_url}/api/now/table/{params.table}"
    response = auth_manager.make_request(
        "GET",
        url,
        params={
            "sysparm_query": query,
            "sysparm_limit": params.limit,
            "sysparm_display_value": "true",
            "sysparm_fields": "number,sys_id,short_description,state,priority,sys_updated_on",
        },
        timeout=config.timeout,
    )
    if response.status_code != 200:
        return json.dumps({"error": f"HTTP {response.status_code}", "body": response.text[:500]})
    return json.dumps(response.json().get("result", []))


def ui_my_groups(
    config: ServerConfig, auth_manager: AuthManager, params: UiMyGroupsParams
) -> str:
    """List groups where the logged-in user is a member."""
    err = _ensure_session_auth(auth_manager)
    if err:
        return json.dumps({"error": err})

    user_id = auth_manager._get_session_data().get("user_id")
    if not user_id:
        return json.dumps({"error": "user_id not available in current session"})

    url = f"{config.instance_url}/api/now/table/sys_user_grmember"
    response = auth_manager.make_request(
        "GET",
        url,
        params={
            "sysparm_query": f"user={user_id}",
            "sysparm_limit": 100,
            "sysparm_display_value": "true",
            "sysparm_fields": "group.name,group.sys_id,group.description",
        },
        timeout=config.timeout,
    )
    if response.status_code != 200:
        return json.dumps({"error": f"HTTP {response.status_code}", "body": response.text[:500]})
    return json.dumps(response.json().get("result", []))


def ui_user_presence(
    config: ServerConfig, auth_manager: AuthManager, params: UiUserPresenceParams
) -> str:
    """User presence status (online/offline) via internal UI endpoint."""
    err = _ensure_session_auth(auth_manager)
    if err:
        return json.dumps({"error": err})

    user_ids = params.user_ids
    if not user_ids:
        me = auth_manager._get_session_data().get("user_id")
        user_ids = [me] if me else []

    url = f"{config.instance_url}/api/now/ui/presence"
    response = auth_manager.make_request(
        "POST",
        url,
        json={"users": user_ids},
        timeout=config.timeout,
    )
    if response.status_code != 200:
        return json.dumps({"error": f"HTTP {response.status_code}", "body": response.text[:500]})
    return response.text


def ui_current_user(
    config: ServerConfig, auth_manager: AuthManager, params: UiCurrentUserParams
) -> str:
    """Return current logged-in user info (sys_id, name, email, roles)."""
    err = _ensure_session_auth(auth_manager)
    if err:
        return json.dumps({"error": err})

    user_id = auth_manager._get_session_data().get("user_id")
    if not user_id:
        return json.dumps({"error": "user_id not available in current session"})

    url = f"{config.instance_url}/api/now/table/sys_user/{user_id}"
    response = auth_manager.make_request(
        "GET",
        url,
        params={
            "sysparm_display_value": "true",
            "sysparm_fields": "user_name,name,email,sys_id,active,title,department",
        },
        timeout=config.timeout,
    )
    if response.status_code != 200:
        return json.dumps({"error": f"HTTP {response.status_code}", "body": response.text[:500]})
    return json.dumps(response.json().get("result", {}))
